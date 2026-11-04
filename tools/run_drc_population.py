#!/usr/bin/env python3
"""Frozen development/holdout runner for the independent MeshEcho-DRC core.

The mechanical DRC runner owns the simulator evidence tables.  This module is
the population boundary: it is the only entry point that can open the frozen
development or untouched holdout seed lists, validates the prerequisite before
holdout, and computes seed-paired nominal intervals and predeclared gates.

The module deliberately does not auto-run a cohort at import time.  Tests and
callers must invoke :func:`run_population` explicitly.  Population execution
is disk-backed: one seed/arm ledger is written and released before the next
simulation starts, while the full JSONL evidence remains available for audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

# Allow this frozen entry point to be invoked as `python tools/...py` as well
# as imported by the test suite from the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_drc_experiment as drc


POPULATION_CONTRACT_PATH = (
    ROOT / "docs" / "research" / "meshecho_drc_population_contract_20261006.md"
)
POPULATION_SCHEMA = "meshecho-drc-population-v1"

DEVELOPMENT_SEEDS: Tuple[int, ...] = tuple(range(62001, 62021))
HOLDOUT_SEEDS: Tuple[int, ...] = tuple(range(63001, 63021))
STAGES = ("development", "holdout")
PRIMARY_ARMS: Tuple[str, ...] = tuple(drc.DRC_PROTOCOLS)
# Conventional names used by the other prospective experiment runners.  Keep
# these aliases pointed at the same immutable values so there is no second
# configuration source to drift.
SPLIT_SEEDS = {
    "development": DEVELOPMENT_SEEDS,
    "holdout": HOLDOUT_SEEDS,
}
ARMS = PRIMARY_ARMS

# This is the single primary case from the population contract.  Keep the
# object immutable and reject caller-supplied alternatives in run_population.
PRIMARY_CASE = drc.DrcCase(
    key="drc_primary",
    nodes=50,
    area_m=8250.0,
    duration_s=600.0,
    rate_per_min=4.0,
    traffic="unicast",
    pair_count=4,
    pair_schedule="poisson",
    payload_bytes=32,
    tx_power_dbm=17.0,
    path_loss_exp=2.75,
    shadow_sigma_db=4.0,
    temporal_fading_sigma_db=6.0,
    temporal_fading_interval_s=60.0,
    capture_threshold_db=6.0,
    sf=7,
    bw_hz=125_000,
    cr=1,
    max_hops=6,
    route_ttl_s=600.0,
    flood_base_delay_s=0.45,
    flood_jitter_s=0.65,
    safety_margin_s=0.25,
    fixed_guard_s=15.0,
)
CASE = PRIMARY_CASE
PRIMARY_DEADLINE_S = 30.0
EXPLORATORY_SEEDS = frozenset({61001})

# The simulator's equal-time ordering and the boundary used by the DRC
# controller are recorded in every population manifest.  These strings are
# metadata, not a second implementation of the scheduler.
EVENT_PRIORITY_CONTRACT = (
    "tx_end/rx_processing < protocol_timers/application_events < tx_requests"
)
DEADLINE_SEMANTICS = (
    "source TX start strictly before deadline; accepted physical ACK at exact "
    "deadline is eligible; TX start at/after deadline is not eligible"
)


# Student-t two-sided 95% critical values.  The primary cohort has n=20, but
# keeping the small-df entries makes focused tests and partial diagnostics
# mathematically explicit.  For large n the normal limit is conservative for
# this nominal interval and avoids a scipy runtime dependency.
_T95_BY_DF = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
    40: 2.021,
    60: 2.000,
    120: 1.980,
}


@dataclass(frozen=True)
class PopulationResult:
    """Immutable return value for one explicit population run."""

    stage: str
    bundle: drc.DrcExperiment
    paths: Dict[str, Path]
    manifest: Dict[str, Any]
    paired_summary: List[Dict[str, Any]]
    exposure: Dict[str, Any]
    gates: Dict[str, Any]
    prerequisite_manifest_sha256: Optional[str] = None

    # Older experiment runners return an artifact-path dictionary.  These
    # small mapping conveniences preserve that ergonomic surface while still
    # exposing the audited bundle and gate report to new callers.
    def __getitem__(self, key: str) -> Path:
        return self.paths[key]

    def keys(self):
        return self.paths.keys()

    def items(self):
        return self.paths.items()

    def __iter__(self):
        return iter(self.paths)

    def __len__(self):
        return len(self.paths)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_canonical(item) for item in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return _canonical(value.value)
    if isinstance(value, float):
        return round(value, 12)
    return value


def _truth(value: Any) -> bool:
    """Parse bools from in-memory rows and CSV-reloaded artifact rows."""

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _digest(value: Any) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def population_contract_sha256() -> str:
    return _file_sha256(POPULATION_CONTRACT_PATH)


def population_source_hashes() -> Dict[str, str]:
    """Hash all source files that affect the population boundary."""

    paths = (
        ROOT / "lora_mesh_sim.py",
        ROOT / "meshecho_drc.py",
        Path(drc.__file__).resolve(),
        Path(__file__).resolve(),
        POPULATION_CONTRACT_PATH,
    )
    return {
        str(path.relative_to(ROOT)): _file_sha256(path)
        for path in paths
    }


def input_hashes() -> Dict[str, str]:
    """Compatibility alias matching the existing experiment runners."""

    return population_source_hashes()


def _stage_seeds(stage: str) -> Tuple[int, ...]:
    if stage == "development":
        return DEVELOPMENT_SEEDS
    if stage == "holdout":
        return HOLDOUT_SEEDS
    raise ValueError(f"stage must be development or holdout, got {stage!r}")


def seeds_for_stage(stage: str) -> Tuple[int, ...]:
    """Return the immutable seed cohort for a population stage."""

    return _stage_seeds(stage)


def _validate_frozen_inputs(
    stage: str,
    case: drc.DrcCase,
    protocols: Sequence[str],
    seeds: Sequence[int],
    deadline_s: float,
) -> Tuple[int, ...]:
    expected_seeds = _stage_seeds(stage)
    if case != PRIMARY_CASE:
        raise ValueError("population runner only permits the frozen primary case")
    if tuple(protocols) != PRIMARY_ARMS:
        raise ValueError("population runner only permits the frozen DRC arm order")
    if tuple(seeds) != expected_seeds:
        raise ValueError(f"{stage} seed list is not the frozen cohort")
    if any(seed in EXPLORATORY_SEEDS for seed in seeds):
        raise ValueError("exploratory seed is excluded from confirmatory cohorts")
    if float(deadline_s) != PRIMARY_DEADLINE_S:
        raise ValueError("population runner requires the frozen 30 s deadline")
    return expected_seeds


def stage_bundle(
    bundle: drc.DrcExperiment,
    stage: str,
    *,
    strict: bool = True,
) -> drc.DrcExperiment:
    """Return a bundle with the declared stage stamped on every evidence row.

    Strict mode is the production path.  It refuses a partial matrix or an
    empty physical ledger before any population manifest can be written.  A
    caller doing a narrow unit test of the relabel operation may set
    ``strict=False`` explicitly; :func:`run_population` never does so.
    """

    expected_seeds = _stage_seeds(stage)
    if strict:
        if tuple(bundle.protocols) != PRIMARY_ARMS:
            raise ValueError("population bundle has non-frozen arm order")
        if tuple(bundle.seeds) != expected_seeds:
            raise ValueError("population bundle has non-frozen seed list")
        expected_runs = len(expected_seeds) * len(PRIMARY_ARMS)
        run_keys = {
            (int(row.get("seed", -1)), str(row.get("protocol")))
            for row in bundle.runs
        }
        if len(bundle.runs) != expected_runs or len(run_keys) != expected_runs:
            raise ValueError("population bundle has an incomplete run matrix")
        if not bundle.flows:
            raise ValueError("population bundle has no flow evidence")
        if not bundle.actions:
            raise ValueError("population bundle has no action evidence")
        if not bundle.requests or not bundle.transmissions or not bundle.rx_attempts:
            raise ValueError("population bundle has incomplete physical evidence")
        if any(
            int(row.get("scheduled_unicast_flows", 0)) <= 0
            for row in bundle.runs
        ):
            raise ValueError("population bundle contains a zero-event seed record")
        expected_keys = {
            (seed, arm) for seed in expected_seeds for arm in PRIMARY_ARMS
        }
        if run_keys != expected_keys:
            raise ValueError("population bundle is missing a seed/arm record")

    def stamped(records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        return [dict(record, seed_split=stage) for record in records]

    return replace(
        bundle,
        split=stage,
        runs=stamped(bundle.runs),
        flows=stamped(bundle.flows),
        actions=stamped(bundle.actions),
        requests=stamped(bundle.requests),
        transmissions=stamped(bundle.transmissions),
        rx_attempts=stamped(bundle.rx_attempts),
        acks=stamped(bundle.acks),
    )


def _t95(n: int) -> float:
    if n < 2:
        return 0.0
    df = n - 1
    if df in _T95_BY_DF:
        return _T95_BY_DF[df]
    larger = [value for value in _T95_BY_DF if value > df]
    if not larger:
        return 1.96
    return _T95_BY_DF[min(larger)]


def nominal_ci95(values: Sequence[float]) -> Dict[str, float]:
    """Return a nominal two-sided 95% t interval over seed-level values."""

    numeric = [float(value) for value in values]
    if not numeric:
        raise ValueError("cannot compute a paired interval with no seeds")
    mean = statistics.fmean(numeric)
    if len(numeric) < 2:
        half = 0.0
    else:
        half = _t95(len(numeric)) * statistics.stdev(numeric) / math.sqrt(len(numeric))
    return {
        "n": len(numeric),
        "mean": mean,
        "half_width": half,
        "ci_low": mean - half,
        "ci_high": mean + half,
    }


def _rows_by_key(
    runs: Sequence[Mapping[str, Any]],
    protocols: Sequence[str],
) -> Dict[Tuple[int, str], Mapping[str, Any]]:
    if not protocols or tuple(protocols) != PRIMARY_ARMS:
        raise ValueError("paired summary requires the frozen DRC arm order")
    keyed: Dict[Tuple[int, str], Mapping[str, Any]] = {}
    for row in runs:
        key = (int(row["seed"]), str(row["protocol"]))
        if key in keyed:
            raise ValueError(f"duplicate paired run {key}")
        keyed[key] = row
    seeds = sorted({seed for seed, _arm in keyed})
    expected = {(seed, arm) for seed in seeds for arm in protocols}
    if set(keyed) != expected:
        raise ValueError("paired run matrix is incomplete")
    identity_fields = (
        "case_sha256",
        "scheduled_trace_sha256",
        "topology_sha256",
        "radio_sha256",
        "pair_pool_sha256",
    )
    for seed in seeds:
        rows = [keyed[(seed, arm)] for arm in protocols]
        for field in identity_fields:
            values = {row.get(field) for row in rows}
            # Focused unit fixtures may omit identity columns; real artifacts
            # must contain them and are rejected by the lower-level audit.
            if len(values) > 1:
                raise ValueError(f"paired identity mismatch in {field} for seed {seed}")
    return keyed


def summarize_paired(
    runs_or_bundle: Sequence[Mapping[str, Any]] | drc.DrcExperiment,
    protocols: Optional[Sequence[str]] = None,
    paired: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Compute seed-paired means and nominal intervals from run rows.

    Differences are always candidate (`meshecho-drc`) minus the named control;
    each seed receives equal weight.  Pooled packet ratios are intentionally
    not used.
    """

    if isinstance(runs_or_bundle, drc.DrcExperiment):
        runs = runs_or_bundle.runs
        protocols = tuple(protocols or runs_or_bundle.protocols)
        paired = runs_or_bundle.paired if paired is None else paired
    else:
        runs = list(runs_or_bundle)
        protocols = tuple(protocols or PRIMARY_ARMS)
    keyed = _rows_by_key(runs, protocols)
    seeds = sorted({seed for seed, _arm in keyed})
    candidate = PRIMARY_ARMS[0]
    paired_by_key: Dict[Tuple[int, str], Mapping[str, Any]] = {}
    if paired is not None:
        for row in paired:
            key = (int(row["seed"]), str(row["comparator"]))
            if key in paired_by_key:
                raise ValueError(f"duplicate paired effect {key}")
            if str(row.get("focus")) != candidate:
                raise ValueError("paired effect focus differs from candidate arm")
            paired_by_key[key] = row
        expected_paired_keys = {
            (seed, comparator)
            for seed in seeds
            for comparator in PRIMARY_ARMS[1:]
        }
        if set(paired_by_key) != expected_paired_keys:
            raise ValueError("paired effect matrix is incomplete")
    result: List[Dict[str, Any]] = []
    for comparator in PRIMARY_ARMS[1:]:
        candidate_rows = [keyed[(seed, candidate)] for seed in seeds]
        control_rows = [keyed[(seed, comparator)] for seed in seeds]
        ack_values = [
            float(left["ack_pdr_deadline"])
            - float(right["ack_pdr_deadline"])
            for left, right in zip(candidate_rows, control_rows)
        ]
        delivery_values = [
            float(left["delivery_pdr_deadline"])
            - float(right["delivery_pdr_deadline"])
            for left, right in zip(candidate_rows, control_rows)
        ]
        if paired is not None:
            for seed, expected_ack, expected_delivery in zip(
                seeds, ack_values, delivery_values
            ):
                saved = paired_by_key[(seed, comparator)]
                if not math.isclose(
                    float(saved["ack_pdr_gain"]), expected_ack, abs_tol=1e-12
                ):
                    raise ValueError("paired ACK effect differs from runs")
                if not math.isclose(
                    float(saved["delivery_pdr_gain"]), expected_delivery, abs_tol=1e-12
                ):
                    raise ValueError("paired delivery effect differs from runs")
                for field in ("trace_match", "topology_match", "pair_pool_match"):
                    if saved.get(field) not in (True, "True", "true", 1, "1"):
                        raise ValueError(f"paired identity failed: {field}")
        ack = nominal_ci95(ack_values)
        delivery = nominal_ci95(delivery_values)
        airtime = nominal_ci95(
            [
                float(left["tx_ledger_airtime_s"])
                - float(right["tx_ledger_airtime_s"])
                for left, right in zip(candidate_rows, control_rows)
            ]
        )
        relative_values: List[float] = []
        for left, right in zip(candidate_rows, control_rows):
            control_airtime = float(right["tx_ledger_airtime_s"])
            if control_airtime <= 0.0:
                raise ValueError("paired airtime denominator must be positive")
            relative_values.append(
                (float(left["tx_ledger_airtime_s"]) - control_airtime)
                / control_airtime
            )
        relative_airtime = nominal_ci95(relative_values)
        candidate_airtime = nominal_ci95(
            [float(row["tx_ledger_airtime_s"]) for row in candidate_rows]
        )
        comparator_airtime = nominal_ci95(
            [float(row["tx_ledger_airtime_s"]) for row in control_rows]
        )
        result.append(
            {
                "comparator": comparator,
                "seed_count": len(seeds),
                "seeds": list(seeds),
                "ack_pdr_mean": ack["mean"],
                "ack_pdr_ci_low": ack["ci_low"],
                "ack_pdr_ci_high": ack["ci_high"],
                "ack_pdr_half_width": ack["half_width"],
                "delivery_pdr_mean": delivery["mean"],
                "delivery_pdr_ci_low": delivery["ci_low"],
                "delivery_pdr_ci_high": delivery["ci_high"],
                "delivery_pdr_half_width": delivery["half_width"],
                "airtime_mean": airtime["mean"],
                "airtime_ci_low": airtime["ci_low"],
                "airtime_ci_high": airtime["ci_high"],
                "airtime_half_width": airtime["half_width"],
                "relative_airtime_mean": relative_airtime["mean"],
                "relative_airtime_ci_low": relative_airtime["ci_low"],
                "relative_airtime_ci_high": relative_airtime["ci_high"],
                "candidate_airtime_mean": candidate_airtime["mean"],
                "comparator_airtime_mean": comparator_airtime["mean"],
            }
        )
    return result


# Descriptive alias for callers that use the term in the contract.
paired_statistics = summarize_paired


def _exposure_counts(bundle: drc.DrcExperiment) -> Dict[str, Any]:
    candidate = PRIMARY_ARMS[0]
    decisions = {
        (int(row["seed"]), int(row["flow_id"]))
        for row in bundle.actions
        if str(row.get("protocol")) == candidate
        and row.get("event") == "decision"
        and row.get("action") == "R_RESERVED"
    }
    reserved_starts = {
        (int(row["seed"]), int(row["flow_id"]))
        for row in bundle.requests
        if str(row.get("protocol")) == candidate
        and row.get("status") == "started"
        and row.get("packet_kind") == "DRC_REQUEST"
    }
    r_reserved = len(decisions & reserved_starts)
    recovery_rows = [
        row
        for row in bundle.requests
        if str(row.get("protocol")) == candidate
        and row.get("status") == "started"
        and row.get("packet_kind") == "DRC_RECOVERY_REQUEST"
    ]
    recovery_keys = {
        (int(row["seed"]), int(row["flow_id"]), int(row.get("repair_index") or 0))
        for row in recovery_rows
    }
    # A request is a physical start only when it has a joined TX.  The
    # lower-level runner audit proves the one-to-one request/TX relationship.
    recovery_starts = len(recovery_keys)
    reserve_fallback = sum(
        1
        for row in bundle.actions
        if str(row.get("protocol")) == candidate
        and row.get("event") == "decision"
        and "fallback" in str(row.get("reason", "")).lower()
    )
    accepted = [row for row in bundle.acks if _truth(row.get("accepted"))]
    attempts = {
        (str(row.get("protocol")), int(row["rx_attempt_id"])): row
        for row in bundle.rx_attempts
    }
    invalid_accepted = 0
    for ack in accepted:
        attempt = (
            attempts.get((str(ack.get("protocol")), int(ack["ack_rx_attempt_id"])))
            if ack.get("ack_rx_attempt_id") is not None
            else None
        )
        if (
            attempt is None
            or attempt.get("reason") != "success"
            or not _truth(attempt.get("decoded"))
            or int(attempt.get("tx_id")) != int(ack.get("ack_tx_id"))
        ):
            invalid_accepted += 1
    return {
        "r_reserved_starts": r_reserved,
        "f_recovery_starts": recovery_starts,
        "reserve_fallback_decisions": reserve_fallback,
        "accepted_ack_count": len(accepted),
        "invalid_accepted_ack_provenance": invalid_accepted,
        "reserve_fallback_exposure_inconclusive": reserve_fallback == 0,
    }


def exposure_counts(bundle: drc.DrcExperiment) -> Dict[str, Any]:
    """Public exposure audit used by tests and population reports."""

    return _exposure_counts(bundle)


def _summary_by_comparator(summary: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    return {str(row["comparator"]): row for row in summary}


def evaluate_development_gates(
    bundle: drc.DrcExperiment,
    paired_summary: Optional[Sequence[Mapping[str, Any]]] = None,
    exposure: Optional[Mapping[str, Any]] = None,
    artifact_audit: bool = False,
) -> Dict[str, Any]:
    """Evaluate the frozen joint development gate, failing closed on missing data."""

    summary = list(paired_summary or summarize_paired(bundle))
    by_comparator = _summary_by_comparator(summary)
    controls = set(PRIMARY_ARMS[1:])
    # Callers may pass only the two exposure thresholds (for example a report
    # builder); retain independently derived provenance fields instead of
    # turning omitted evidence into a default pass.
    # A streaming population runner supplies every exposure/provenance field
    # from the current DrcRun before releasing its RX ledger.  In that case,
    # do not reconstruct a whole-RX ``attempts`` index from the JSONL view;
    # doing so would defeat the bounded-memory execution contract.  Keep the
    # historical derivation path for callers that provide only a partial
    # override (and for small in-memory unit fixtures).
    exposure_fields = {
        "r_reserved_starts",
        "f_recovery_starts",
        "reserve_fallback_decisions",
        "accepted_ack_count",
        "invalid_accepted_ack_provenance",
        "reserve_fallback_exposure_inconclusive",
    }
    if exposure is not None and exposure_fields.issubset(exposure):
        exposure_data = dict(exposure)
    else:
        exposure_data = _exposure_counts(bundle)
        if exposure is not None:
            exposure_data.update(dict(exposure))
    required = ("meshecho-drc-all-f", "meshecho-drc-no-rescue")
    ack_bounds = [
        float(by_comparator[name]["ack_pdr_ci_low"])
        for name in required
        if name in by_comparator
    ]
    delivery_bounds = [
        float(by_comparator[name]["delivery_pdr_ci_low"])
        for name in controls
        if name in by_comparator
    ]
    candidate_means = [
        float(by_comparator[name]["candidate_airtime_mean"])
        for name in by_comparator
        if "candidate_airtime_mean" in by_comparator[name]
    ]
    candidate_mean = candidate_means[0] if candidate_means else None
    no_rescue_mean = (
        float(by_comparator["meshecho-drc-no-rescue"]["comparator_airtime_mean"])
        if "meshecho-drc-no-rescue" in by_comparator
        else None
    )
    all_f_mean = (
        float(by_comparator["meshecho-drc-all-f"]["comparator_airtime_mean"])
        if "meshecho-drc-all-f" in by_comparator
        else None
    )
    checks = {
        "ack_pdr_lower_bounds": (
            len(ack_bounds) == len(required) and all(value >= -0.05 for value in ack_bounds)
        ),
        "delivery_pdr_lower_bounds": (
            len(delivery_bounds) == len(controls)
            and all(value >= -0.05 for value in delivery_bounds)
        ),
        "airtime_vs_no_rescue": (
            candidate_mean is not None
            and no_rescue_mean is not None
            and candidate_mean <= 1.10 * no_rescue_mean
        ),
        "airtime_vs_all_f": (
            candidate_mean is not None
            and all_f_mean is not None
            and candidate_mean <= 0.95 * all_f_mean
        ),
        "r_reserved_exposure": int(exposure_data.get("r_reserved_starts", -1)) >= 20,
        "f_recovery_exposure": int(exposure_data.get("f_recovery_starts", -1)) >= 10,
        "accepted_ack_provenance": (
            int(exposure_data.get("invalid_accepted_ack_provenance", 1)) == 0
        ),
        "artifact_audit": bool(artifact_audit),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": {
            "ack_pdr_lower_bound": -0.05,
            "delivery_pdr_lower_bound": -0.05,
            "no_rescue_airtime_max_ratio": 1.10,
            "all_f_airtime_max_ratio": 0.95,
            "r_reserved_starts_min": 20,
            "f_recovery_starts_min": 10,
        },
        "ack_pdr_lower_bounds": {
            name: by_comparator[name]["ack_pdr_ci_low"]
            for name in required
            if name in by_comparator
        },
        "delivery_pdr_lower_bounds": {
            name: by_comparator[name]["delivery_pdr_ci_low"]
            for name in controls
            if name in by_comparator
        },
        "candidate_airtime_mean": candidate_mean,
        "no_rescue_airtime_mean": no_rescue_mean,
        "all_f_airtime_mean": all_f_mean,
        "exposure": exposure_data,
    }


def _read_manifest(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("population manifest cannot be read") from exc
    if not isinstance(value, dict):
        raise ValueError("population manifest must be an object")
    return value


def _validate_population_manifest_shape(
    manifest: Mapping[str, Any], stage: str
) -> None:
    """Check immutable configuration fields shared by both stage audits."""

    expected_seeds = _stage_seeds(stage)
    if manifest.get("population_schema") != POPULATION_SCHEMA:
        raise ValueError("population manifest has wrong schema")
    if manifest.get("population_stage") != stage or manifest.get("seed_split") != stage:
        raise ValueError("population manifest has wrong stage")
    if tuple(int(seed) for seed in manifest.get("seeds", ())) != expected_seeds:
        raise ValueError(f"{stage} manifest seed list is not frozen")
    if tuple(manifest.get("protocols", ())) != PRIMARY_ARMS:
        raise ValueError(f"{stage} manifest arm list is not frozen")
    if tuple(int(seed) for seed in manifest.get("population_seeds", ())) != expected_seeds:
        raise ValueError(f"{stage} population seed list is not frozen")
    if tuple(manifest.get("population_arms", ())) != PRIMARY_ARMS:
        raise ValueError(f"{stage} population arm list is not frozen")
    if set(expected_seeds) & EXPLORATORY_SEEDS:
        raise ValueError("population cohort includes an excluded exploratory seed")
    if manifest.get("case") != asdict(PRIMARY_CASE):
        raise ValueError(f"{stage} manifest case differs from frozen primary case")
    expected_case_hash = _digest(asdict(PRIMARY_CASE))
    if manifest.get("case_sha256") != expected_case_hash:
        raise ValueError(f"{stage} manifest case hash mismatch")
    if manifest.get("population_case_sha256") != expected_case_hash:
        raise ValueError(f"{stage} population case hash mismatch")
    if float(manifest.get("deadline_s", -1.0)) != PRIMARY_DEADLINE_S:
        raise ValueError(f"{stage} manifest deadline differs from frozen deadline")
    if manifest.get("application_trace_schema") != "time+ordinal+src+dst+flow_id":
        raise ValueError(f"{stage} manifest trace schema differs from contract")
    if manifest.get("event_priority_contract") != EVENT_PRIORITY_CONTRACT:
        raise ValueError(f"{stage} event-priority contract differs")
    if manifest.get("deadline_semantics") != DEADLINE_SEMANTICS:
        raise ValueError(f"{stage} deadline semantics differ")


def validate_development_manifest(path: Path) -> Dict[str, Any]:
    """Validate the immutable development prerequisite for opening holdout."""

    manifest_path = Path(path)
    manifest = _read_manifest(manifest_path)
    _validate_population_manifest_shape(manifest, "development")
    if manifest.get("population_contract_sha256") != population_contract_sha256():
        raise ValueError("development population contract hash mismatch")
    if manifest.get("population_source_sha256") != population_source_hashes():
        raise ValueError("development population source hash mismatch")
    if manifest.get("contract_sha256") != population_contract_sha256():
        raise ValueError("development contract alias hash mismatch")
    if manifest.get("source_hashes") != population_source_hashes():
        raise ValueError("development source alias hash mismatch")
    if manifest.get("source_sha256") != drc._source_hashes():
        raise ValueError("development DRC runner source hash mismatch")
    gate = manifest.get("population_gates", {}).get("development")
    ordinary_gate = manifest.get("gates", {}).get("development")
    if gate is not True or ordinary_gate is not True:
        raise ValueError("development gate did not pass; holdout remains closed")
    # The underlying writer/auditor independently checks all artifact hashes,
    # request/TX joins, RX attempts, ACK provenance, and matrix completeness.
    drc.audit_artifacts(manifest_path)
    return {
        "manifest": manifest,
        "manifest_sha256": _file_sha256(manifest_path),
        "path": str(manifest_path),
    }


def audit_population_artifacts(
    manifest_path: Path,
    *,
    expected_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Audit the lower-level DRC artifacts and population metadata."""

    manifest = _read_manifest(Path(manifest_path))
    stage = expected_stage or str(manifest.get("population_stage", ""))
    if stage not in STAGES:
        raise ValueError("population artifact stage is missing")
    _validate_population_manifest_shape(manifest, stage)
    if manifest.get("population_contract_sha256") != population_contract_sha256():
        raise ValueError("population contract hash mismatch")
    if manifest.get("population_source_sha256") != population_source_hashes():
        raise ValueError("population source hash mismatch")
    if manifest.get("contract_sha256") != population_contract_sha256():
        raise ValueError("population contract alias hash mismatch")
    if manifest.get("source_hashes") != population_source_hashes():
        raise ValueError("population source alias hash mismatch")
    drc.audit_artifacts(Path(manifest_path))
    return manifest


def validate_manifest(path: Path, expected_stage: str = "development") -> Dict[str, Any]:
    """Compatibility wrapper for stage prerequisite validation."""

    if expected_stage == "development":
        return validate_development_manifest(Path(path))
    if expected_stage == "holdout":
        return audit_population_artifacts(Path(path), expected_stage="holdout")
    raise ValueError("expected_stage must be development or holdout")


def _update_manifest(
    paths: Mapping[str, Path],
    stage: str,
    bundle: drc.DrcExperiment,
    paired_summary: Sequence[Mapping[str, Any]],
    exposure: Mapping[str, Any],
    gates: Mapping[str, Any],
    prerequisite_manifest_sha256: Optional[str],
) -> Dict[str, Any]:
    manifest_path = Path(paths["manifest"])
    manifest = _read_manifest(manifest_path)
    manifest["population_schema"] = POPULATION_SCHEMA
    manifest["population_stage"] = stage
    manifest["seed_split"] = stage
    manifest["population_contract_sha256"] = population_contract_sha256()
    manifest["population_source_sha256"] = population_source_hashes()
    # Short aliases make the population boundary unambiguous to independent
    # readers while retaining the lower-level runner's ``core_contract`` and
    # ``source_sha256`` fields for its own auditor.
    manifest["contract_sha256"] = manifest["population_contract_sha256"]
    manifest["source_hashes"] = dict(manifest["population_source_sha256"])
    manifest["event_priority_contract"] = EVENT_PRIORITY_CONTRACT
    manifest["deadline_semantics"] = DEADLINE_SEMANTICS
    manifest["population_case_sha256"] = _digest(asdict(bundle.case))
    manifest["population_arms"] = list(bundle.protocols)
    manifest["population_seeds"] = list(bundle.seeds)
    manifest["paired_statistics"] = list(paired_summary)
    manifest["exposure"] = dict(exposure)
    manifest["population_gates"] = {
        "development": bool(gates.get("passed")) if stage == "development" else False,
        "holdout": bool(gates.get("passed")) if stage == "holdout" else False,
        "report": dict(gates),
    }
    ordinary_gates = dict(manifest.get("gates", {}))
    if stage == "development":
        ordinary_gates["development"] = bool(gates.get("passed"))
    if stage == "holdout":
        ordinary_gates["holdout"] = bool(gates.get("passed"))
    manifest["gates"] = ordinary_gates
    manifest["prerequisite_manifest_sha256"] = prerequisite_manifest_sha256
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(_canonical(manifest), handle, sort_keys=True, indent=2)
        handle.write("\n")
    return manifest


class _JsonlEvidenceView:
    """File-backed sequence used by the bounded-memory population result."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return drc._iter_jsonl(self.path)

    def __len__(self) -> int:
        return sum(1 for _ in drc._iter_jsonl(self.path))

    def __getitem__(self, index: int) -> Dict[str, Any]:
        if not isinstance(index, int):
            raise TypeError("JSONL evidence view only supports integer indexing")
        if index < 0:
            index = len(self) + index
        for ordinal, row in enumerate(drc._iter_jsonl(self.path)):
            if ordinal == index:
                return row
        raise IndexError(index)


def _exposure_for_run(result: drc.DrcRun) -> Dict[str, int]:
    """Derive gate exposure/provenance counts before releasing one run."""

    candidate = PRIMARY_ARMS[0]
    if str(result.row.get("protocol")) != candidate:
        return {
            "r_reserved_starts": 0,
            "f_recovery_starts": 0,
            "reserve_fallback_decisions": 0,
            "accepted_ack_count": 0,
            "invalid_accepted_ack_provenance": 0,
        }
    decisions = {
        int(row["flow_id"])
        for row in result.actions
        if row.get("event") == "decision" and row.get("action") == "R_RESERVED"
    }
    reserved_starts = {
        int(row["flow_id"])
        for row in result.requests
        if row.get("status") == "started"
        and row.get("packet_kind") == "DRC_REQUEST"
    }
    recovery_starts = {
        (int(row["flow_id"]), int(row.get("repair_index") or 0))
        for row in result.requests
        if row.get("status") == "started"
        and row.get("packet_kind") == "DRC_RECOVERY_REQUEST"
    }
    reserve_fallback = sum(
        1
        for row in result.actions
        if row.get("event") == "decision"
        and "fallback" in str(row.get("reason", "")).lower()
    )
    attempts = {
        int(row["rx_attempt_id"]): row
        for row in result.rx_attempts
        if row.get("rx_attempt_id") is not None
    }
    accepted = [row for row in result.acks if _truth(row.get("accepted"))]
    invalid = 0
    for ack in accepted:
        attempt = (
            attempts.get(int(ack["ack_rx_attempt_id"]))
            if ack.get("ack_rx_attempt_id") is not None
            else None
        )
        if (
            attempt is None
            or attempt.get("reason") != "success"
            or not _truth(attempt.get("decoded"))
            or int(attempt.get("tx_id")) != int(ack.get("ack_tx_id"))
        ):
            invalid += 1
    return {
        "r_reserved_starts": len(decisions & reserved_starts),
        "f_recovery_starts": len(recovery_starts),
        "reserve_fallback_decisions": reserve_fallback,
        "accepted_ack_count": len(accepted),
        "invalid_accepted_ack_provenance": invalid,
    }


def run_population(
    stage: str,
    out_prefix: Path,
    *,
    development_manifest: Optional[Path] = None,
    case: drc.DrcCase = PRIMARY_CASE,
    protocols: Sequence[str] = PRIMARY_ARMS,
    seeds: Optional[Sequence[int]] = None,
    deadline_s: float = PRIMARY_DEADLINE_S,
) -> PopulationResult:
    """Run exactly one frozen population stage and write audited artifacts."""

    expected_seeds = _stage_seeds(stage)
    selected_seeds = tuple(expected_seeds if seeds is None else seeds)
    _validate_frozen_inputs(stage, case, protocols, selected_seeds, deadline_s)

    prerequisite_sha: Optional[str] = None
    if stage == "holdout":
        if development_manifest is None:
            raise ValueError("holdout requires a validated development manifest")
        prerequisite = validate_development_manifest(Path(development_manifest))
        prerequisite_sha = str(prerequisite["manifest_sha256"])

    # The lower-level runner intentionally exposes only smoke/custom matrix
    # execution.  Consume one result at a time and append its complete JSONL
    # evidence before the next arm starts; retaining a DrcExperiment from
    # ``run_matrix`` here multiplies RX-attempt memory by the whole cohort.
    exposure_totals = {
        "r_reserved_starts": 0,
        "f_recovery_starts": 0,
        "reserve_fallback_decisions": 0,
        "accepted_ack_count": 0,
        "invalid_accepted_ack_provenance": 0,
    }

    def stream_results() -> Iterator[drc.DrcRun]:
        for result in drc.iter_matrix(
            case,
            tuple(protocols),
            selected_seeds,
            deadline_s=deadline_s,
            split="custom",
        ):
            if str(result.row.get("protocol")) == PRIMARY_ARMS[0]:
                counts = _exposure_for_run(result)
                for key, value in counts.items():
                    exposure_totals[key] += int(value)
            yield result

    stream = drc.write_artifacts_stream(
        Path(out_prefix),
        case,
        tuple(protocols),
        selected_seeds,
        deadline_s,
        stage,
        stream_results(),
    )
    paths = stream.paths
    # Existing audit is deliberately invoked before population metadata is
    # added, and again by audit_population_artifacts after metadata is written.
    drc.audit_artifacts(paths["manifest"])
    bundle = drc.DrcExperiment(
        case=case,
        protocols=tuple(protocols),
        seeds=selected_seeds,
        deadline_s=deadline_s,
        split=stage,
        runs=stream.runs,
        flows=_JsonlEvidenceView(paths["flows"]),
        actions=_JsonlEvidenceView(paths["actions"]),
        requests=_JsonlEvidenceView(paths["requests"]),
        transmissions=_JsonlEvidenceView(paths["tx"]),
        rx_attempts=_JsonlEvidenceView(paths["rx_attempts"]),
        acks=_JsonlEvidenceView(paths["acks"]),
        paired=stream.paired,
        source_sha256=stream.source_sha256,
        identities=stream.identities,
    )
    paired = summarize_paired(bundle)
    exposure = {
        **exposure_totals,
        "reserve_fallback_exposure_inconclusive": (
            exposure_totals["reserve_fallback_decisions"] == 0
        ),
    }
    gates = evaluate_development_gates(
        bundle,
        paired_summary=paired,
        exposure=exposure,
        artifact_audit=True,
    )
    manifest = _update_manifest(
        paths,
        stage,
        bundle,
        paired,
        exposure,
        gates,
        prerequisite_sha,
    )
    audit_population_artifacts(paths["manifest"], expected_stage=stage)
    return PopulationResult(
        stage=stage,
        bundle=bundle,
        paths=dict(paths),
        manifest=manifest,
        paired_summary=paired,
        exposure=exposure,
        gates=gates,
        prerequisite_manifest_sha256=prerequisite_sha,
    )


def run_experiment(
    stage: str,
    out_prefix: Path,
    *,
    development_manifest: Optional[Path] = None,
) -> PopulationResult:
    """Compatibility wrapper matching the naming of older experiment tools."""

    return run_population(
        stage,
        out_prefix,
        development_manifest=development_manifest,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path)
    args = parser.parse_args(argv)
    if args.stage == "holdout" and args.development_manifest is None:
        parser.error("--development-manifest is required for holdout")
    return args


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    result = run_population(
        args.stage,
        args.out_prefix,
        development_manifest=args.development_manifest,
    )
    print(result.paths["manifest"])
    print(json.dumps({"stage": result.stage, "gates": result.gates}, sort_keys=True))


if __name__ == "__main__":
    main()
