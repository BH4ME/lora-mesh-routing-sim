#!/usr/bin/env python3
"""Staged passive destination-certified backup exposure screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_sr_experiment as sr
from tools import diagnose_destination_certified_backup as backup
from tools.diagnose_delayed_ack_rx import capture_run, require_stock_parity


_STOCK_RECORDING_SIMULATOR = sr.RecordingSimulator
PROTOCOL = "meshecho-dhr-flood-ack-delay"
SMOKE_SEEDS = (46000,)
EXPLORATORY_SEEDS = tuple(range(46001, 46021))
_RUNNER_AUTHORIZATION = object()
ARTIFACT_KEYS = (
    "summary", "runs", "flows", "actions", "transmissions",
    "flood_decodes", "destination_ack_decodes", "candidate_epochs", "rows",
)
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "tools" / "diagnose_delayed_ack_rx.py",
    ROOT / "tools" / "diagnose_destination_certified_backup.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_destination_certified_backup.py",
    ROOT / "tests" / "test_destination_backup_screen_runner.py",
    ROOT / "tests" / "test_destination_backup_seed_guard.py",
    ROOT / "docs" / "research" / "meshecho_destination_certified_backup_screen.md",
)


def seeds_for_mode(mode: str) -> tuple[int, ...]:
    if mode == "smoke":
        return SMOKE_SEEDS
    if mode == "explore":
        return EXPLORATORY_SEEDS
    raise ValueError(f"unknown backup screen mode: {mode}")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("ascii")).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def _validate_stage(
    mode: str, case: sr.SrCase, deadline_s: float,
    stage_authorization_path: Path | None,
    smoke_manifest_path: Path | None = None,
) -> tuple[dict[str, str], bytes, dict[str, str]]:
    seeds = seeds_for_mode(mode)
    if case != sr.SR_CASES["recurring_fading"] or deadline_s != 30.0:
        raise ValueError("backup screen requires the frozen case and deadline")
    if stage_authorization_path is None:
        raise ValueError(f"{mode} stage authorization is required")
    try:
        authorization_data = Path(stage_authorization_path).read_bytes()
        authorization = json.loads(authorization_data)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{mode} stage authorization cannot be read") from exc
    source_sha256 = _source_hashes()
    predecessors: dict[str, str] = {}
    if mode == "explore" and smoke_manifest_path is not None:
        predecessors["smoke_manifest"] = hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()
    expected = {
        "mode": mode,
        "seeds": list(seeds),
        "protocol": PROTOCOL,
        "case_sha256": _sha256_json(asdict(case)),
        "application_deadline_s": deadline_s,
        "input_sha256": source_sha256,
        "prerequisite_manifest_sha256": predecessors,
    }
    if (authorization != expected
            or not isinstance(authorization.get("seeds"), list)
            or any(type(seed) is not int for seed in authorization["seeds"])):
        raise ValueError(f"{mode} stage authorization differs from frozen inputs")
    if mode == "explore" and smoke_manifest_path is None:
        raise ValueError("exploration requires a verified smoke manifest")
    if mode == "smoke" and smoke_manifest_path is not None:
        raise ValueError("smoke cannot name a predecessor")
    if mode == "explore":
        validate_manifest(
            smoke_manifest_path, expected_mode="smoke",
            expected_source_sha256=source_sha256, strict_replay=True,
        )
        if (hashlib.sha256(Path(smoke_manifest_path).read_bytes()).hexdigest()
                != predecessors["smoke_manifest"]):
            raise RuntimeError("backup screen predecessor changed during replay")
    return source_sha256, authorization_data, predecessors


def _capture_seed(
    seed: int, case: sr.SrCase, deadline_s: float, *,
    stage_authorization_path: Path, smoke_manifest_path: Path | None,
) -> dict[str, Any]:
    """Capture normal physical attempts through the registered seed guard."""

    def authorized_run(
        selected_case: sr.SrCase, protocol: str, selected_seed: int,
        selected_deadline_s: float,
    ) -> sr.SrRun:
        return sr.run_one_sr(
            selected_case, protocol, selected_seed, selected_deadline_s,
            research_authorization=_RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_authorization_path,
            smoke_manifest_path=smoke_manifest_path,
        )

    stock, _ = capture_run(
        case, seed, _STOCK_RECORDING_SIMULATOR, deadline_s,
        runner=authorized_run,
    )
    observed, sim = capture_run(
        case, seed, backup.PassiveBackupSimulator, deadline_s,
        runner=authorized_run,
    )
    parity = require_stock_parity(stock, observed)
    rows = backup.analyze_backup_exposure(sim)
    candidate_epochs = backup.analyze_candidate_epochs(sim)
    replay, replay_sim = capture_run(
        case, seed, backup.PassiveBackupSimulator, deadline_s,
        runner=authorized_run,
    )
    replay_rows = backup.analyze_backup_exposure(replay_sim)
    replay_epochs = backup.analyze_candidate_epochs(replay_sim)
    if (observed != replay
            or sim.flood_decodes != replay_sim.flood_decodes
            or sim.initial_r_decodes != replay_sim.initial_r_decodes
            or sim.destination_ack_decodes != replay_sim.destination_ack_decodes
            or rows != replay_rows or candidate_epochs != replay_epochs):
        raise AssertionError(f"passive backup strict replay differs at seed {seed}")
    for current_sim, evidence in ((sim, observed), (replay_sim, replay)):
        if (hashlib.sha256(repr(current_sim.random.getstate()).encode("ascii")).hexdigest()
                != evidence.random_state_sha256
                or hashlib.sha256(
                    repr(current_sim.channel_random.getstate()).encode("ascii")
                ).hexdigest() != evidence.channel_random_state_sha256):
            raise AssertionError("passive backup analysis consumed RNG")
    result = {
        "seed": seed,
        "parity": parity,
        "strict_replay_exact": True,
        "row": observed.row,
        "flows": observed.flows,
        "actions": observed.actions,
        "transmissions": observed.transmissions,
        "flood_decodes": [asdict(item) for item in sim.flood_decodes],
        "destination_ack_decodes": [
            asdict(item) for item in sim.destination_ack_decodes
        ],
        "candidate_epochs": candidate_epochs,
        "rows": rows,
    }
    result["summary"] = backup.summarize_backup_cohort([result])
    return result


def _summarize_runs(runs: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    summary = backup.summarize_backup_cohort(runs)
    per_seed = [backup.summarize_backup_cohort([run]) for run in runs]
    airtimes = [run["row"]["whole_network_tx_airtime_s"] for run in runs]
    if any(not isinstance(value, (int, float)) or not math.isfinite(value)
           or value <= 0 for value in airtimes):
        raise ValueError("backup screen needs positive complete-network airtime per seed")
    for suffix in ("2_s", "0_5_s"):
        group = summary["by_wait"][suffix]
        parts = [item["by_wait"][suffix] for item in per_seed]
        cost_assessable = all(item["candidate_cost_assessable"] for item in parts)
        ack_assessable = all(
            item.get("source_ack_outcome_unassessable_count") == 0
            and len(run["flows"]) > 0
            for item, run in zip(parts, runs)
        )
        margins = [item["optimistic_cost_substitution_margin_s"] for item in parts]
        group.update({
            "failed_primary_seed_count": sum(
                item["failed_primary_relay_decode_le_120_s"] > 0 for item in parts
            ),
            "proxy_feasible_seed_count": sum(
                item["proxy_prr_ge_0_5_deadline_feasible_count"] > 0
                for item in parts
            ),
            "source_ack_gain_ceiling_equal_seed_mean": sum(
                item["source_ack_headroom_proxy_count"] / len(run["flows"])
                for item, run in zip(parts, runs)
            ) / len(runs) if ack_assessable else None,
            "cost_substitution_fraction_equal_seed_mean": (
                sum(margin / airtime for margin, airtime in zip(margins, airtimes))
                / len(runs) if cost_assessable else None
            ),
            "cost_substitution_fraction_pooled": (
                sum(margins) / sum(airtimes) if cost_assessable else None
            ),
        })
    all_rows = [row for run in runs for row in run["rows"]]
    by_age = {}
    for label, age_limit_s in (
        ("no_age_limit", None), ("le_120_s", 120.0), ("le_60_s", 60.0),
    ):
        selected = [
            row for row in all_rows
            if age_limit_s is None
            or row["backup_age_at_r_enqueue_s"] <= age_limit_s
        ]
        by_age[label] = {}
        for suffix in ("2_s", "0_5_s"):
            failed = [
                row for row in selected
                if row["relay_decoded_current_r"] is True
                and row["destination_decoded_current_r"] is False
            ]
            feasible = [
                row for row in failed
                if row[f"oracle_collision_free_relay_to_dst_prr_{suffix}"] >= 0.5
                and row[f"nominal_source_ack_slack_{suffix}"] >= 0.0
            ]
            by_age[label][suffix] = {
                "nominated_flow_count": len(selected),
                "failed_primary_relay_decode_count": len(failed),
                "proxy_feasible_count": len(feasible),
                "source_ack_headroom_count": sum(
                    row["stock_source_ack_by_deadline"] is False
                    for row in feasible
                ),
                "source_ack_outcome_unassessable_count": sum(
                    row["stock_source_ack_by_deadline"] is None
                    for row in feasible
                ),
                "nominal_cost_substitution_eligible_count": sum(
                    row[f"nominal_cost_substitution_eligible_{suffix}"] is True
                    for row in selected
                ),
            }
    summary["by_age"] = by_age
    primary = summary["by_wait"]["2_s"]
    exposure_passed = (
        primary["failed_primary_relay_decode_le_120_s"] >= 20
        and primary["failed_primary_seed_count"] >= 10
        and primary["proxy_prr_ge_0_5_deadline_feasible_count"] >= 16
    )
    fraction = primary["cost_substitution_fraction_equal_seed_mean"]
    cost_passed = fraction is not None and fraction >= 0.05
    summary.update({
        "primary_timer_s": 2.0,
        "sensitivity_timer_s": 0.5,
        "exposure_gate_passed": exposure_passed if mode == "explore" else None,
        "cost_gate_passed": cost_passed if mode == "explore" else None,
        "necessary_gate_passed": (
            exposure_passed and cost_passed if mode == "explore" else None
        ),
    })
    return summary


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, allow_nan=False))


def _audit_run(run: dict[str, Any], seed: int) -> None:
    row = run["row"]
    parity = run["parity"]
    if (
        type(run.get("seed")) is not int or run["seed"] != seed
        or type(row.get("seed")) is not int or row["seed"] != seed
        or row.get("case") != "recurring_fading"
        or row.get("protocol") != PROTOCOL
        or parity.get("exact") is not True
        or run.get("strict_replay_exact") is not True
        or row.get("scheduled_trace_sha256")
        != parity.get("scheduled_trace_sha256")
        or _sha256_json(row) != parity.get("full_row_sha256")
        or _sha256_json(run["flows"]) != parity.get("flow_trace_sha256")
        or _sha256_json(run["actions"]) != parity.get("action_trace_sha256")
        or _sha256_json(run["transmissions"])
        != parity.get("full_tx_trace_sha256")
        or len(run["flows"]) != row.get("scheduled_unicast_flows")
        or len(run["rows"]) != run["summary"].get("nominated_initial_direct_r")
        or len({item["flow_id"] for item in run["rows"]}) != len(run["rows"])
        or run["summary"] != backup.summarize_backup_cohort([run])
    ):
        raise ValueError(f"backup screen run {seed} parity or cohort differs")


def _artifact_paths(prefix: Path) -> dict[str, Path]:
    prefix = Path(prefix)
    paths = {
        key: prefix.with_name(prefix.name + (
            ".summary.json" if key == "summary" else f".{key}.jsonl"
        )) for key in ARTIFACT_KEYS
    }
    paths["authorization"] = prefix.with_name(prefix.name + ".authorization.json")
    paths["manifest"] = prefix.with_name(prefix.name + ".manifest.json")
    paths["manifest_sha256"] = prefix.with_name(prefix.name + ".manifest.sha256")
    return paths


def _require_paths_available(prefix: Path) -> dict[str, Path]:
    paths = _artifact_paths(prefix)
    if Path(prefix).exists() or any(path.exists() for path in paths.values()):
        raise FileExistsError(f"backup screen output prefix already exists: {prefix}")
    return paths


def write_report(report: dict[str, Any], output_prefix: Path) -> dict[str, Path]:
    """Write full passive evidence, then a content-addressed manifest."""

    prefix = Path(output_prefix)
    paths = _require_paths_available(prefix)
    if _source_hashes() != report["input_sha256"]:
        raise RuntimeError("backup screen inputs changed before artifact writing")
    if len(report["runs"]) != len(report["seeds"]):
        raise ValueError("backup screen run count differs from frozen seeds")
    for run, seed in zip(report["runs"], report["seeds"]):
        _audit_run(run, seed)
    if _summarize_runs(report["runs"], report["mode"]) != report["summary"]:
        raise ValueError("backup screen summary differs from runs")

    def json_line(value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ) + "\n"

    separated = set(ARTIFACT_KEYS) - {"summary", "runs"}
    metadata = {
        key: value for key, value in report.items()
        if key not in {"runs", "_stage_authorization_data"}
    }
    data = {
        "summary": (json.dumps(metadata, sort_keys=True, indent=2,
                               allow_nan=False) + "\n").encode("utf-8"),
        "runs": "".join(json_line({
            key: value for key, value in run.items() if key not in separated
        }) for run in report["runs"]).encode("utf-8"),
    }
    for key in separated:
        data[key] = "".join(json_line({"seed": run["seed"], "item": item})
                             for run in report["runs"] for item in run[key]
                             ).encode("utf-8")
    data["authorization"] = report["_stage_authorization_data"]
    if (hashlib.sha256(data["authorization"]).hexdigest()
            != report["stage_authorization_sha256"]):
        raise ValueError("backup screen authorization changed before writing")
    artifact_keys = ARTIFACT_KEYS + ("authorization",)
    manifest = {
        "mode": report["mode"],
        "protocol": PROTOCOL,
        "seeds": report["seeds"],
        "case_sha256": report["case_sha256"],
        "application_deadline_s": report["application_deadline_s"],
        "drain_until_s": report["drain_until_s"],
        "input_sha256": report["input_sha256"],
        "prerequisite_manifest_sha256": report["prerequisite_manifest_sha256"],
        "stage_authorization_sha256": report["stage_authorization_sha256"],
        "summary": report["summary"],
        "artifacts": {
            key: {
                "file": paths[key].name,
                "sha256": hashlib.sha256(data[key]).hexdigest(),
            } for key in artifact_keys
        },
    }
    manifest_data = (json.dumps(
        manifest, sort_keys=True, indent=2, allow_nan=False,
    ) + "\n").encode("utf-8")
    sidecar = (
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    ).encode("ascii")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for key in artifact_keys:
        with paths[key].open("xb") as output:
            output.write(data[key])
    with paths["manifest"].open("xb") as output:
        output.write(manifest_data)
    with paths["manifest_sha256"].open("xb") as output:
        output.write(sidecar)
    return paths


def validate_manifest(
    manifest_path: Path, *, expected_mode: str,
    expected_source_sha256: dict[str, str],
    smoke_manifest_path: Path | None = None,
    strict_replay: bool = True,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("backup screen manifest needs .manifest.json suffix")
    prefix = manifest_path.with_name(
        manifest_path.name[:-len(".manifest.json")]
    )
    paths = _artifact_paths(prefix)
    manifest_data = manifest_path.read_bytes()
    expected_sidecar = (
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + manifest_path.name + "\n"
    )
    if paths["manifest_sha256"].read_text(encoding="ascii") != expected_sidecar:
        raise ValueError("backup screen manifest SHA-256 sidecar differs")
    manifest = json.loads(manifest_data)
    expected_seeds = seeds_for_mode(expected_mode)
    case = sr.SR_CASES["recurring_fading"]
    if (
        manifest.get("mode") != expected_mode
        or manifest.get("protocol") != PROTOCOL
        or manifest.get("seeds") != list(expected_seeds)
        or any(type(seed) is not int for seed in manifest["seeds"])
        or manifest.get("case_sha256") != _sha256_json(asdict(case))
        or manifest.get("application_deadline_s") != 30.0
        or manifest.get("drain_until_s") != case.duration_s + 30.0
        or manifest.get("input_sha256") != expected_source_sha256
        or _source_hashes() != expected_source_sha256
        or set(manifest.get("artifacts", {}))
        != set(ARTIFACT_KEYS + ("authorization",))
    ):
        raise ValueError("backup screen manifest frozen configuration differs")
    predecessors = manifest.get("prerequisite_manifest_sha256")
    if expected_mode == "smoke" and predecessors != {}:
        raise ValueError("backup screen smoke cannot claim a predecessor")
    if expected_mode == "explore":
        if smoke_manifest_path is None:
            raise ValueError("exploration archive requires its smoke manifest")
        if predecessors != {"smoke_manifest": hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()}:
            raise ValueError("backup screen predecessor manifest hash differs")
        validate_manifest(
            smoke_manifest_path, expected_mode="smoke",
            expected_source_sha256=expected_source_sha256,
            strict_replay=strict_replay,
        )
    data: dict[str, bytes] = {}
    for key, descriptor in manifest["artifacts"].items():
        if descriptor.get("file") != paths[key].name:
            raise ValueError(f"backup screen artifact path differs: {key}")
        data[key] = paths[key].read_bytes()
        if hashlib.sha256(data[key]).hexdigest() != descriptor.get("sha256"):
            raise ValueError(f"backup screen artifact checksum differs: {key}")
    authorization = json.loads(data["authorization"])
    expected_authorization = {
        "mode": expected_mode,
        "seeds": list(expected_seeds),
        "protocol": PROTOCOL,
        "case_sha256": manifest["case_sha256"],
        "application_deadline_s": 30.0,
        "input_sha256": expected_source_sha256,
        "prerequisite_manifest_sha256": predecessors,
    }
    if (
        authorization != expected_authorization
        or hashlib.sha256(data["authorization"]).hexdigest()
        != manifest.get("stage_authorization_sha256")
    ):
        raise ValueError("backup screen archived authorization differs")
    metadata = json.loads(data["summary"])
    expected_metadata = {
        "analysis_type": "passive destination-certified backup exposure",
        "counterfactual_outcomes_observed": False,
        "mode": expected_mode,
        "protocol": PROTOCOL,
        "case": asdict(case),
        "case_sha256": manifest["case_sha256"],
        "seeds": list(expected_seeds),
        "application_deadline_s": 30.0,
        "drain_until_s": case.duration_s + 30.0,
        "input_sha256": expected_source_sha256,
        "prerequisite_manifest_sha256": predecessors,
        "stage_authorization_sha256": manifest["stage_authorization_sha256"],
        "summary": manifest["summary"],
    }
    if metadata != expected_metadata:
        raise ValueError("backup screen summary and manifest metadata differ")
    separated = set(ARTIFACT_KEYS) - {"summary", "runs"}
    saved_runs = [json.loads(line) for line in data["runs"].splitlines()]
    if [run["seed"] for run in saved_runs] != list(expected_seeds):
        raise ValueError("backup screen run seeds differ from manifest")
    grouped: dict[str, dict[int, list[Any]]] = {}
    for key in separated:
        grouped[key] = {seed: [] for seed in expected_seeds}
        for line in data[key].splitlines():
            wrapped = json.loads(line)
            if (type(wrapped.get("seed")) is not int
                    or wrapped["seed"] not in grouped[key]):
                raise ValueError(f"backup screen {key} has alien seed")
            grouped[key][wrapped["seed"]].append(wrapped["item"])
    runs = []
    for saved in saved_runs:
        seed = saved["seed"]
        run = {**saved, **{key: grouped[key][seed] for key in separated}}
        _audit_run(run, seed)
        runs.append(run)
    if _summarize_runs(runs, expected_mode) != manifest["summary"]:
        raise ValueError("backup screen summary differs from saved evidence")
    if strict_replay:
        for run in runs:
            replay = _json_value(_capture_seed(
                run["seed"], case, 30.0,
                stage_authorization_path=paths["authorization"],
                smoke_manifest_path=smoke_manifest_path,
            ))
            if replay != run:
                raise ValueError(
                    f"backup screen strict replay differs at seed {run['seed']}"
                )
    return manifest


def run_stage(
    mode: str, output_prefix: Path, *,
    stage_authorization_path: Path | None = None,
    smoke_manifest_path: Path | None = None,
) -> dict[str, Path]:
    case = sr.SR_CASES["recurring_fading"]
    _require_paths_available(output_prefix)
    source_sha256, authorization_data, predecessors = _validate_stage(
        mode, case, 30.0,
        stage_authorization_path, smoke_manifest_path,
    )
    runs = []
    for seed in seeds_for_mode(mode):
        run = _json_value(_capture_seed(
            seed, case, 30.0,
            stage_authorization_path=Path(stage_authorization_path),
            smoke_manifest_path=smoke_manifest_path,
        ))
        _audit_run(run, seed)
        if _source_hashes() != source_sha256:
            raise RuntimeError("backup screen inputs changed during the cohort")
        if Path(stage_authorization_path).read_bytes() != authorization_data:
            raise RuntimeError("backup screen permit changed during the cohort")
        if (mode == "explore"
                and hashlib.sha256(Path(smoke_manifest_path).read_bytes()).hexdigest()
                != predecessors["smoke_manifest"]):
            raise RuntimeError("backup screen predecessor changed during the cohort")
        runs.append(run)
    report = {
        "analysis_type": "passive destination-certified backup exposure",
        "counterfactual_outcomes_observed": False,
        "mode": mode,
        "protocol": PROTOCOL,
        "case": asdict(case),
        "case_sha256": _sha256_json(asdict(case)),
        "seeds": list(seeds_for_mode(mode)),
        "application_deadline_s": 30.0,
        "drain_until_s": case.duration_s + 30.0,
        "input_sha256": source_sha256,
        "prerequisite_manifest_sha256": predecessors,
        "stage_authorization_sha256": hashlib.sha256(
            authorization_data
        ).hexdigest(),
        "summary": _summarize_runs(runs, mode),
        "runs": runs,
        "_stage_authorization_data": authorization_data,
    }
    return write_report(report, output_prefix)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("smoke", "explore"))
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--stage-authorization", required=True, type=Path)
    parser.add_argument("--smoke-manifest", type=Path)
    args = parser.parse_args(argv)
    paths = run_stage(
        args.mode, args.output_prefix,
        stage_authorization_path=args.stage_authorization,
        smoke_manifest_path=args.smoke_manifest,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    from tools import run_destination_backup_screen as backup_screen

    backup_screen.main()
