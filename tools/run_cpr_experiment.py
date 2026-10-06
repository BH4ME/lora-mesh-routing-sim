#!/usr/bin/env python3
"""Independent, auditable mechanical-smoke runner for MeshEcho-CPR."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import random
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (  # noqa: E402
    EVENT_PRIORITY,
    Node,
    Packet,
    RadioConfig,
    Simulator,
    Transmission,
    build_protocol,
    generate_nodes,
)
from tools import run_drc_experiment as drc  # noqa: E402


CPR_PROTOCOLS = (
    "meshecho-cpr",
    "meshecho-cpr-nocancel",
    "meshecho-drc-no-rescue",
    "meshecho-drc",
)
SCHEMA = "meshecho-cpr-evidence-v2"
CONTRACT_PATH = ROOT / "docs" / "research" / "meshecho_cpr_smoke_contract_20261006.md"
VERSION_PATH = ROOT / "VERSION"


@dataclass(frozen=True)
class CprCase:
    key: str = "cpr_smoke"
    nodes: int = 8
    area_m: float = 250.0
    duration_s: float = 120.0
    rate_per_min: float = 4.0
    traffic: str = "unicast"
    pair_count: int = 4
    pair_schedule: str = "fixed-once"
    payload_bytes: int = 32
    tx_power_dbm: float = 17.0
    path_loss_exp: float = 2.75
    shadow_sigma_db: float = 4.0
    temporal_fading_sigma_db: float = 0.0
    temporal_fading_interval_s: float = 60.0
    capture_threshold_db: float = 6.0
    sf: int = 9
    bw_hz: int = 125_000
    cr: int = 1
    max_hops: int = 6
    route_ttl_s: float = 600.0
    flood_base_delay_s: float = 0.45
    flood_jitter_s: float = 0.65
    safety_margin_s: float = 0.25
    fixed_guard_s: float = 15.0

    def __post_init__(self) -> None:
        if self.nodes < 2 or self.area_m <= 0 or self.duration_s <= 0:
            raise ValueError("invalid CPR case dimensions")
        if self.pair_count <= 0 or self.pair_count > self.nodes * (self.nodes - 1):
            raise ValueError("invalid CPR pair count")
        if self.pair_schedule not in {"fixed-once", "poisson"}:
            raise ValueError("unknown CPR pair schedule")
        if self.traffic != "unicast":
            raise ValueError("CPR smoke currently requires unicast traffic")


CASE_PROFILES = {
    "smoke": CprCase(),
    "exposure": CprCase(
        key="cpr_exposure",
        nodes=20,
        area_m=3000.0,
        duration_s=240.0,
        rate_per_min=8.0,
        pair_count=4,
        pair_schedule="poisson",
        temporal_fading_sigma_db=6.0,
        temporal_fading_interval_s=60.0,
        sf=7,
    ),
}


@dataclass(frozen=True)
class CprRun:
    row: Dict[str, Any]
    flows: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    requests: List[Dict[str, Any]]
    transmissions: List[Dict[str, Any]]
    rx_attempts: List[Dict[str, Any]]
    acks: List[Dict[str, Any]]
    identity: Dict[str, Any]


@dataclass(frozen=True)
class CprExperiment:
    case: CprCase
    protocols: Tuple[str, ...]
    seeds: Tuple[int, ...]
    deadline_s: float
    split: str
    runs: List[Dict[str, Any]]
    flows: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    requests: List[Dict[str, Any]]
    transmissions: List[Dict[str, Any]]
    rx_attempts: List[Dict[str, Any]]
    acks: List[Dict[str, Any]]
    paired: List[Dict[str, Any]]
    contract_path: Path
    source_sha256: Dict[str, str]
    identities: Dict[int, Dict[str, Any]]


class _RecordingSimulator(Simulator):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tx_history: List[Transmission] = []

    def begin_transmission(self, sender: int, packet: Packet, pending: Any) -> None:
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > before:
            self.tx_history.append(self.transmissions[-1])


def _drc_case(case: CprCase) -> drc.DrcCase:
    return drc.DrcCase(**asdict(case))


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_canonical(item) for item in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return _canonical(value.value)
    if isinstance(value, float):
        return round(value, 12)
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    """Use repository-relative paths in manifests when possible."""

    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def _source_hashes(contract_path: Path = CONTRACT_PATH) -> Dict[str, str]:
    contract_path = Path(contract_path)
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    contract_path = contract_path.resolve()
    paths = (
        ROOT / "lora_mesh_sim.py",
        ROOT / "meshecho_cpr.py",
        ROOT / "meshecho_drc.py",
        ROOT / "meshecho_utility.py",
        Path(__file__).resolve(),
        contract_path,
        VERSION_PATH,
    )
    return {_display_path(path): _file_sha256(path) for path in paths}


def _git_revision() -> str:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip()
        dirty = subprocess.run(
            ["git", "diff", "--quiet", "--"], cwd=ROOT, check=False,
        ).returncode != 0
        return revision + ("+dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def _radio(case: CprCase) -> RadioConfig:
    return drc._radio(_drc_case(case))


def _make_pair_pool(nodes: Sequence[Node], seed: int, count: int) -> List[Tuple[int, int]]:
    return drc._make_pair_pool(nodes, seed, count)


def _schedule_traffic(sim: Simulator, case: CprCase, pairs: Sequence[Tuple[int, int]], seed: int) -> None:
    drc._schedule_traffic(sim, _drc_case(case), pairs, seed)


def _trace_from_events(sim: Simulator) -> Tuple[List[Dict[str, Any]], str]:
    return drc._trace_from_events(sim)


def _topology_identity(nodes: Sequence[Node], radio: RadioConfig, pairs: Sequence[Tuple[int, int]]) -> Dict[str, str]:
    return drc._topology_identity(nodes, radio, pairs)


def _packet_row(tx: Transmission, request_by_tx: Mapping[int, Mapping[str, Any]], deadline_by_flow: Mapping[int, float], cutoff: float) -> Dict[str, Any]:
    return drc._packet_row(tx, request_by_tx, deadline_by_flow, cutoff)


def _action_rows(protocol: Any, arm: str, seed: int, case: CprCase) -> List[Dict[str, Any]]:
    return [
        {
            "case": case.key,
            "protocol": arm,
            "seed": seed,
            "action_ordinal": ordinal,
            **_canonical(event),
        }
        for ordinal, event in enumerate(getattr(protocol, "action_events", []), start=1)
    ]


def _flow_rows(
    sim: Simulator,
    protocol: Any,
    trace: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    deadline_s: float,
    arm: str,
) -> List[Dict[str, Any]]:
    by_flow: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for request in requests:
        by_flow[int(request["flow_id"])].append(request)
    events: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for event in getattr(protocol, "action_events", []):
        if "flow_id" in event:
            events[int(event["flow_id"])].append(event)
    rows: List[Dict[str, Any]] = []
    for item in trace:
        flow_id = int(item["flow_id"])
        when = float(item["time"])
        deadline = when + deadline_s
        metric = sim.metrics.flows.get(flow_id)
        decisions = [event for event in events[flow_id] if event.get("event") == "decision"]
        started = [request for request in by_flow[flow_id] if request.get("status") == "started"]
        rows.append({
            "protocol": arm,
            "flow_id": flow_id,
            "src": int(item["src"]),
            "dst": int(item["dst"]),
            "enqueued_at": when,
            "deadline_at": deadline,
            "registered": metric is not None,
            "decision_count": len(decisions),
            "initial_action": decisions[0].get("action") if decisions else None,
            "decision_reason": decisions[0].get("reason") if decisions else None,
            "request_count": len(by_flow[flow_id]),
            "started_request_count": len(started),
            "accepted_ack_at": metric.acked_at if metric is not None else None,
            "first_delivery_at": metric.delivered_at if metric is not None else None,
            "ack_by_deadline": bool(metric is not None and metric.acked_at is not None and metric.acked_at <= deadline),
            "delivery_by_deadline": bool(metric is not None and metric.delivered_at is not None and metric.delivered_at <= deadline),
            "late_ack": bool(metric is not None and metric.acked_at is not None and metric.acked_at > deadline),
            "late_delivery": bool(metric is not None and metric.delivered_at is not None and metric.delivered_at > deadline),
            "no_start_count": len(by_flow[flow_id]) - len(started),
        })
    return rows


def run_one(
    case: CprCase,
    protocol_name: str,
    seed: int,
    deadline_s: float = 30.0,
    split: str = "smoke",
) -> CprRun:
    if protocol_name not in CPR_PROTOCOLS:
        raise ValueError(f"unknown CPR arm: {protocol_name}")
    if type(seed) is not int or deadline_s <= 0:
        raise ValueError("CPR seed and deadline are invalid")
    topology_rng = random.Random(seed)
    nodes = generate_nodes(case.nodes, case.area_m, topology_rng, repeater_ratio=0.0)
    radio = _radio(case)
    args = argparse.Namespace(
        calm_route_ttl_s=case.route_ttl_s,
        calm_flood_base_delay_s=case.flood_base_delay_s,
        calm_flood_jitter_s=case.flood_jitter_s,
        sr_app_deadline_s=deadline_s,
        drc_safety_margin_s=case.safety_margin_s,
        drc_fixed_guard_s=case.fixed_guard_s,
    )
    protocol = build_protocol(protocol_name, args)
    sim = _RecordingSimulator(
        nodes, radio, protocol, seed=seed, max_hops=case.max_hops,
        independent_random_streams=True, record_rx_attempts=True,
    )
    pairs = _make_pair_pool(nodes, seed, case.pair_count)
    _schedule_traffic(sim, case, pairs, seed)
    trace, trace_sha256 = _trace_from_events(sim)
    cutoff = case.duration_s + deadline_s
    identity = {
        "seed": seed,
        "protocol": protocol_name,
        "case_sha256": _digest(asdict(case)),
        "trace_sha256": trace_sha256,
        "trace_schema": "time+ordinal+src+dst+flow_id",
        **_topology_identity(nodes, radio, pairs),
    }
    sim.run(cutoff)
    sim.finalize_request_ledger(cutoff)
    requests = drc._request_rows(sim, protocol, trace, deadline_s, cutoff, protocol_name)
    request_by_tx = {
        int(row["tx_id"]): row for row in requests
        if row.get("status") == "started" and row.get("tx_id") is not None
    }
    deadlines = {int(item["flow_id"]): float(item["time"]) + deadline_s for item in trace}
    transmissions = [_packet_row(tx, request_by_tx, deadlines, cutoff) for tx in sim.tx_history]
    tx_request_by_tx = {int(row["tx_id"]): row.get("tx_request_id") for row in transmissions}
    rx_attempts = []
    for source in sim.rx_attempts:
        row = dict(source)
        row["protocol"] = protocol_name
        row["tx_request_id"] = tx_request_by_tx.get(int(row["tx_id"]))
        deadline = deadlines.get(int(row["flow_id"]))
        row["in_deadline"] = bool(deadline is not None and float(row["end"]) <= deadline)
        rx_attempts.append(_canonical(row))
    acks = []
    for source in sim.ack_provenance:
        row = dict(source)
        row["protocol"] = protocol_name
        row["ack_tx_request_id"] = tx_request_by_tx.get(row.get("ack_tx_id"))
        deadline = deadlines.get(int(row["flow_id"]))
        row["in_deadline"] = bool(deadline is not None and row.get("accepted_at") is not None and float(row["accepted_at"]) <= deadline)
        acks.append(_canonical(row))
    flows = _flow_rows(sim, protocol, trace, requests, deadline_s, protocol_name)
    actions = _action_rows(protocol, protocol_name, seed, case)
    metrics = sim.metrics.summarize(protocol_name, seed, cutoff)
    started = [row for row in requests if row.get("status") == "started"]
    tx_airtime = sum(float(row["toa_s"]) for row in transmissions if float(row["start"]) <= cutoff)
    tx_energy = sum(float(row["toa_s"]) * radio.supply_voltage_v * radio.tx_current_ma / 1000.0 for row in transmissions if float(row["start"]) <= cutoff)
    rx_count_by_tx = Counter(int(item["tx_id"]) for item in rx_attempts)
    incomplete = [item["tx_id"] for item in transmissions if float(item["start"]) <= cutoff and rx_count_by_tx.get(int(item["tx_id"]), 0) != case.nodes]
    row = {
        **metrics,
        "case": case.key,
        "protocol": protocol_name,
        "seed": seed,
        "generation_horizon_s": case.duration_s,
        "application_deadline_s": deadline_s,
        "drain_until_s": cutoff,
        "case_sha256": identity["case_sha256"],
        "scheduled_trace_sha256": trace_sha256,
        "topology_sha256": identity["topology_sha256"],
        "radio_sha256": identity["radio_sha256"],
        "pair_pool_sha256": identity["pair_pool_sha256"],
        "scheduled_unicast_flows": len(trace),
        "ack_by_deadline": sum(bool(item["ack_by_deadline"]) for item in flows),
        "delivery_by_deadline": sum(bool(item["delivery_by_deadline"]) for item in flows),
        "ack_pdr_deadline": sum(bool(item["ack_by_deadline"]) for item in flows) / len(trace),
        "delivery_pdr_deadline": sum(bool(item["delivery_by_deadline"]) for item in flows) / len(trace),
        "request_count": len(requests),
        "started_request_count": len(started),
        "no_start_count": len(requests) - len(started),
        "tx_ledger_airtime_s": tx_airtime,
        "tx_ledger_energy_j": tx_energy,
        "rx_attempt_count": len(rx_attempts),
        "accepted_ack_count": sum(bool(item["accepted"]) for item in acks),
        "protocol_action_count": len(actions),
        "incomplete_rx_tx_count": len(incomplete),
        "seed_split": split,
    }
    for collection in (flows, actions, requests, transmissions, rx_attempts, acks):
        for evidence in collection:
            evidence.setdefault("case", case.key)
            evidence.setdefault("seed", seed)
            evidence.setdefault("protocol", protocol_name)
    return CprRun(row, flows, actions, requests, transmissions, rx_attempts, acks, identity)


def _paired_rows(runs: Sequence[Mapping[str, Any]], protocols: Sequence[str]) -> List[Dict[str, Any]]:
    by_key = {(int(row["seed"]), str(row["protocol"])): row for row in runs}
    focus = protocols[0]
    rows = []
    for seed in sorted({int(row["seed"]) for row in runs}):
        base = by_key[(seed, focus)]
        for comparator in protocols[1:]:
            other = by_key[(seed, comparator)]
            rows.append({
                "seed": seed, "focus": focus, "comparator": comparator,
                "ack_pdr_gain": base["ack_pdr_deadline"] - other["ack_pdr_deadline"],
                "delivery_pdr_gain": base["delivery_pdr_deadline"] - other["delivery_pdr_deadline"],
                "relative_airtime_cost": ((base["tx_ledger_airtime_s"] - other["tx_ledger_airtime_s"]) / other["tx_ledger_airtime_s"] if other["tx_ledger_airtime_s"] else None),
                "trace_match": base["scheduled_trace_sha256"] == other["scheduled_trace_sha256"],
                "topology_match": base["topology_sha256"] == other["topology_sha256"],
                "pair_pool_match": base["pair_pool_sha256"] == other["pair_pool_sha256"],
            })
    return rows


def run_matrix(
    case: CprCase,
    protocols: Sequence[str] = CPR_PROTOCOLS,
    seeds: Sequence[int] = (92000,),
    deadline_s: float = 30.0,
    split: str = "smoke",
    contract_path: Path = CONTRACT_PATH,
) -> CprExperiment:
    protocols = tuple(protocols)
    seeds = tuple(seeds)
    if split not in {"smoke", "exploratory", "development", "holdout", "custom"}:
        raise ValueError("unknown CPR experiment split")
    if not protocols or not seeds or len(set(protocols)) != len(protocols) or len(set(seeds)) != len(seeds):
        raise ValueError("duplicate or empty CPR matrix")
    unknown = [name for name in protocols if name not in CPR_PROTOCOLS]
    if unknown:
        raise ValueError(f"unknown CPR arm: {unknown[0]}")
    runs: List[Dict[str, Any]] = []
    collections = {key: [] for key in ("flows", "actions", "requests", "transmissions", "rx_attempts", "acks")}
    identities: Dict[int, Dict[str, Any]] = {}
    for seed in seeds:
        expected: Optional[Dict[str, Any]] = None
        for protocol in protocols:
            result = run_one(case, protocol, seed, deadline_s, split)
            if expected is None:
                expected = result.identity
                identities[seed] = result.identity
            else:
                for key in ("case_sha256", "trace_sha256", "topology_sha256", "radio_sha256", "pair_pool_sha256"):
                    if result.identity[key] != expected[key]:
                        raise ValueError(f"paired identity mismatch: {key}")
            runs.append(result.row)
            for key in collections:
                collections[key].extend(getattr(result, key))
    paired = _paired_rows(runs, protocols)
    contract_path = Path(contract_path)
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    contract_path = contract_path.resolve()
    return CprExperiment(
        case, protocols, seeds, deadline_s, split, runs,
        collections["flows"], collections["actions"],
        collections["requests"], collections["transmissions"],
        collections["rx_attempts"], collections["acks"], paired,
        contract_path, _source_hashes(contract_path), identities,
    )


def _artifact_paths(prefix: Path) -> Dict[str, Path]:
    prefix = Path(prefix)
    return {
        "runs": Path(f"{prefix}.runs.csv"),
        "paired": Path(f"{prefix}.paired.csv"),
        "flows": Path(f"{prefix}.flows.jsonl"),
        "actions": Path(f"{prefix}.actions.jsonl"),
        "requests": Path(f"{prefix}.requests.jsonl"),
        "tx": Path(f"{prefix}.transmissions.jsonl"),
        "rx_attempts": Path(f"{prefix}.rx_attempts.jsonl"),
        "acks": Path(f"{prefix}.acks.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def _write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fields = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_canonical(record), sort_keys=True) + "\n")


def write_artifacts(prefix: Path, bundle: CprExperiment) -> Dict[str, Path]:
    paths = _artifact_paths(prefix)
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("CPR artifact prefix already exists")
    records = {
        "runs": bundle.runs, "paired": bundle.paired,
        "flows": bundle.flows, "actions": bundle.actions,
        "requests": bundle.requests, "tx": bundle.transmissions,
        "rx_attempts": bundle.rx_attempts, "acks": bundle.acks,
    }
    try:
        for key in ("runs", "paired"):
            _write_csv(paths[key], records[key])
        for key in ("flows", "actions", "requests", "tx", "rx_attempts", "acks"):
            _write_jsonl(paths[key], records[key])
        manifest = {
            "schema": SCHEMA,
            "contract_sha256": _file_sha256(bundle.contract_path),
            "contract_path": _display_path(bundle.contract_path),
            "source_sha256": bundle.source_sha256,
            "sim_version": VERSION_PATH.read_text(encoding="utf-8").strip(),
            "git_revision": _git_revision(),
            "python_version": platform.python_version(),
            "case": asdict(bundle.case),
            "case_sha256": _digest(asdict(bundle.case)),
            "protocols": list(bundle.protocols),
            "seeds": list(bundle.seeds),
            "seed_split": bundle.split,
            "experiment_stage": bundle.split,
            "deadline_s": bundle.deadline_s,
            "event_priority": dict(EVENT_PRIORITY),
            "application_trace_schema": "time+ordinal+src+dst+flow_id",
            "artifacts": {
                key: {"sha256": _file_sha256(paths[key]), "records": len(records[key])}
                for key in records
            },
            "counts": {
                "runs": len(bundle.runs),
                "scheduled_flows": len(bundle.flows),
                "requests": len(bundle.requests),
                "transmissions": len(bundle.transmissions),
                "rx_attempts": len(bundle.rx_attempts),
                "accepted_acks": sum(bool(row.get("accepted")) for row in bundle.acks),
                "incomplete_rx_tx": sum(int(row.get("incomplete_rx_tx_count", 0)) for row in bundle.runs),
            },
            "gates": {
                "mechanical_smoke": bundle.split in {"smoke", "exploratory", "custom"},
                "development": False,
                "holdout": False,
            },
        }
        with paths["manifest"].open("w", encoding="utf-8") as handle:
            json.dump(_canonical(manifest), handle, sort_keys=True, indent=2)
            handle.write("\n")
    except Exception:
        for path in paths.values():
            try:
                path.unlink()
            except OSError:
                pass
        raise
    return paths


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("JSONL record is not an object")
                yield value


def audit_artifacts(manifest_path: Path) -> Dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported CPR artifact schema")
    if manifest.get("event_priority") != dict(EVENT_PRIORITY):
        raise ValueError("event-priority contract differs")
    current_version = VERSION_PATH.read_text(encoding="utf-8").strip()
    if manifest.get("sim_version") != current_version:
        raise ValueError("CPR simulator version mismatch")
    contract_path_value = manifest.get("contract_path", str(CONTRACT_PATH))
    contract_path = Path(contract_path_value)
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    if not contract_path.exists():
        raise ValueError("CPR contract file is missing")
    if manifest.get("contract_sha256") != _file_sha256(contract_path):
        raise ValueError("CPR contract hash mismatch")
    if manifest.get("source_sha256") != _source_hashes(contract_path):
        raise ValueError("CPR source hash mismatch")
    prefix = Path(str(manifest_path)[:-len(".manifest.json")])
    paths = _artifact_paths(prefix)
    details = manifest.get("artifacts", {})
    expected_artifacts = set(paths) - {"manifest"}
    if set(details) != expected_artifacts:
        raise ValueError("CPR artifact inventory mismatch")
    for key in expected_artifacts:
        detail = details[key]
        if not paths[key].exists():
            raise ValueError(f"missing CPR artifact: {key}")
        if _file_sha256(paths[key]) != detail.get("sha256"):
            raise ValueError(f"CPR artifact hash mismatch: {key}")
    runs = list(csv.DictReader(paths["runs"].open(newline="", encoding="utf-8")))
    if len(runs) != int(manifest["counts"]["runs"]):
        raise ValueError("run count mismatch")
    expected_split = manifest.get("seed_split")
    if expected_split not in {"smoke", "exploratory", "development", "holdout", "custom"}:
        raise ValueError("invalid CPR seed split")
    if any(row.get("seed_split") != expected_split for row in runs):
        raise ValueError("CPR run row split mismatch")
    run_scopes = {(int(row["seed"]), row["protocol"]): row for row in runs}
    if len(run_scopes) != len(runs):
        raise ValueError("duplicate CPR run scope")
    expected_scopes = {
        (int(seed), str(protocol))
        for seed in manifest.get("seeds", [])
        for protocol in manifest.get("protocols", [])
    }
    if set(run_scopes) != expected_scopes:
        raise ValueError("CPR run scope inventory mismatch")
    jsonl_records = {
        key: list(_iter_jsonl(paths[key]))
        for key in ("flows", "actions", "requests", "tx", "rx_attempts", "acks")
    }
    expected_record_counts = {
        key: int(details[key].get("records", -1)) for key in jsonl_records
    }
    for key, records in jsonl_records.items():
        if len(records) != expected_record_counts[key]:
            raise ValueError(f"CPR {key} record count mismatch")
    if len(jsonl_records["flows"]) != int(manifest["counts"]["scheduled_flows"]):
        raise ValueError("CPR scheduled-flow count mismatch")
    if len(jsonl_records["requests"]) != int(manifest["counts"]["requests"]):
        raise ValueError("CPR request count mismatch")
    if len(jsonl_records["tx"]) != int(manifest["counts"]["transmissions"]):
        raise ValueError("CPR transmission count mismatch")
    if len(jsonl_records["rx_attempts"]) != int(manifest["counts"]["rx_attempts"]):
        raise ValueError("CPR RX-attempt count mismatch")

    def scope(row: Mapping[str, Any]) -> Tuple[int, str]:
        try:
            result = (int(row["seed"]), str(row["protocol"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("CPR artifact row has invalid scope") from exc
        if result not in run_scopes:
            raise ValueError("CPR artifact row references unknown run scope")
        return result

    for key, records in jsonl_records.items():
        for row in records:
            scope(row)

    started_by_scope: Dict[Tuple[int, str], set[int]] = defaultdict(set)
    tx_by_scope: Dict[Tuple[int, str], Dict[int, Mapping[str, Any]]] = defaultdict(dict)
    rx_count: Dict[Tuple[int, str], Counter[int]] = defaultdict(Counter)
    for row in jsonl_records["requests"]:
        row_scope = scope(row)
        if row.get("status") == "started":
            if row.get("tx_id") is None:
                raise ValueError("started CPR request lacks TX id")
            started_by_scope[row_scope].add(int(row["tx_id"]))
    for row in jsonl_records["tx"]:
        row_scope = scope(row)
        tx_id = int(row["tx_id"])
        if tx_id in tx_by_scope[row_scope]:
            raise ValueError("duplicate CPR TX")
        tx_by_scope[row_scope][tx_id] = row
        if abs(float(row["toa_s"]) - (float(row["end"]) - float(row["start"]))) > 1e-9:
            raise ValueError("CPR TX ToA mismatch")
    if dict(started_by_scope) != {
        row_scope: set(tx_rows)
        for row_scope, tx_rows in tx_by_scope.items()
    }:
        raise ValueError("CPR request/TX join failed")

    cpr_action_contract = {
        "R_INITIAL": ("CPR_REQUEST", "DATA", None),
        "F_INITIAL": ("CPR_REQUEST", "FLOOD", None),
        "R_REPEAT": ("CPR_REPEAT_REQUEST", "DATA", 1),
        "F_RECOVERY": ("CPR_RECOVERY_REQUEST", "FLOOD", 2),
    }
    requests_by_flow: Dict[Tuple[Tuple[int, str], int], List[Mapping[str, Any]]] = defaultdict(list)
    for row in jsonl_records["requests"]:
        requests_by_flow[(scope(row), int(row["flow_id"]))].append(row)
        if row.get("status") != "started":
            continue
        tx_id = int(row["tx_id"])
        tx = tx_by_scope[scope(row)].get(tx_id)
        if tx is None:
            raise ValueError("started CPR request lacks TX record")
        if (
            row.get("actual_packet_kind") != tx.get("packet_kind")
            or row.get("repair_index") != tx.get("repair_index")
            or int(row.get("flow_id")) != int(tx.get("flow_id"))
        ):
            raise ValueError("CPR request/TX packet identity mismatch")
    decisions_by_flow: Dict[Tuple[Tuple[int, str], int], List[Mapping[str, Any]]] = defaultdict(list)
    for row in jsonl_records["actions"]:
        row_scope = scope(row)
        if row.get("event") == "decision":
            decisions_by_flow[(row_scope, int(row["flow_id"]))].append(row)
            if (
                str(row_scope[1]).startswith("meshecho-cpr")
                and "route_generation" not in row
            ):
                raise ValueError("CPR decision lacks route-generation evidence")
    for flow_key, flow_requests in requests_by_flow.items():
        row_scope, flow_id = flow_key
        if not str(row_scope[1]).startswith("meshecho-cpr"):
            continue
        flow_decisions = decisions_by_flow.get(flow_key, [])
        for decision in flow_decisions:
            contract = cpr_action_contract.get(str(decision.get("action")))
            if contract is None:
                continue
            request_kind, actual_kind, marker = contract
            candidates = [
                request for request in flow_requests
                if request.get("packet_kind") == request_kind
            ]
            if len(candidates) != 1:
                raise ValueError("CPR action lacks unique request record")
            request = candidates[0]
            if request.get("status") != "started":
                raise ValueError("CPR action lacks started request")
            if (
                request.get("actual_packet_kind") != actual_kind
                or request.get("repair_index") != marker
            ):
                raise ValueError("CPR action/request packet mismatch")
        for request in flow_requests:
            if (
                request.get("status") != "started"
                or request.get("packet_kind") not in {
                    "CPR_REQUEST", "CPR_REPEAT_REQUEST", "CPR_RECOVERY_REQUEST",
                }
            ):
                continue
            expected_action = {
                "CPR_REQUEST": {
                    ("DATA", None): "R_INITIAL",
                    ("FLOOD", None): "F_INITIAL",
                },
                "CPR_REPEAT_REQUEST": {("DATA", 1): "R_REPEAT"},
                "CPR_RECOVERY_REQUEST": {("FLOOD", 2): "F_RECOVERY"},
            }[request["packet_kind"]].get(
                (request.get("actual_packet_kind"), request.get("repair_index"))
            )
            matching = [
                decision for decision in flow_decisions
                if decision.get("action") == expected_action
            ]
            if expected_action is None or len(matching) != 1:
                raise ValueError("CPR started request lacks action decision")

    accepted: Dict[Tuple[Tuple[int, str], int], Mapping[str, Any]] = {}
    for row in jsonl_records["acks"]:
        if str(row.get("accepted")).lower() not in {"true", "1"}:
            continue
        row_scope = scope(row)
        if row.get("ack_rx_attempt_id") is None or row.get("ack_tx_id") is None:
            raise ValueError("accepted CPR ACK lacks physical IDs")
        attempt = int(row["ack_rx_attempt_id"])
        key = (row_scope, attempt)
        if key in accepted:
            raise ValueError("duplicate accepted CPR ACK")
        accepted[key] = row
    if len(accepted) != int(manifest["counts"]["accepted_acks"]):
        raise ValueError("accepted CPR ACK count mismatch")

    for (row_scope, _), row in accepted.items():
        ack_tx_id = int(row["ack_tx_id"])
        ack_tx = tx_by_scope[row_scope].get(ack_tx_id)
        if ack_tx is None:
            raise ValueError("accepted CPR ACK references unknown TX")
        reverse_path = tuple(row.get("reverse_path") or ())
        try:
            reverse_hop = int(row["reverse_hop"])
            expected_sender = reverse_path[reverse_hop + 1]
            tx_path_index = int(ack_tx["path_index"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ValueError("accepted CPR ACK reverse-path identity is invalid") from exc
        if (
            ack_tx.get("packet_kind") != "ACK"
            or int(ack_tx.get("flow_id")) != int(row["flow_id"])
            or int(ack_tx.get("origin")) != int(row["destination"])
            or int(ack_tx.get("final_dst")) != int(row["source"])
            or tuple(ack_tx.get("path") or ()) != reverse_path
            or tx_path_index != reverse_hop
            or int(ack_tx.get("sender")) != int(expected_sender)
        ):
            raise ValueError("accepted CPR ACK TX identity mismatch")
        marker = row.get("repair_index")
        if marker not in {None, 1, 2}:
            raise ValueError("accepted CPR ACK marker invalid")
        if marker != ack_tx.get("repair_index"):
            raise ValueError("accepted CPR ACK marker/TX mismatch")
        reverse_path = tuple(row.get("reverse_path") or ())
        if (
            len(reverse_path) < 2
            or len(set(reverse_path)) != len(reverse_path)
            or reverse_path[0] != int(row["source"])
            or reverse_path[-1] != int(row["destination"])
        ):
            raise ValueError("accepted CPR ACK path invalid")
        accepted_at = row.get("accepted_at")
        deadline_at = row.get("deadline_at")
        if accepted_at is None or deadline_at is None or float(accepted_at) > float(deadline_at):
            raise ValueError("accepted CPR ACK is outside deadline")
        if (
            str(row_scope[1]).startswith("meshecho-cpr")
            and (
                row.get("route_generation") is None
                or row.get("route_generation_after") is None
            )
        ):
            raise ValueError("accepted CPR ACK lacks route-generation provenance")
        expected_kinds = {None: {"DATA", "FLOOD"}, 1: {"DATA"}, 2: {"FLOOD"}}[marker]
        matching_payload = any(
            tx.get("packet_kind") in expected_kinds
            and int(tx.get("flow_id")) == int(row["flow_id"])
            and int(tx.get("sender")) == int(row["source"])
            and int(tx.get("origin")) == int(row["source"])
            and int(tx.get("final_dst")) == int(row["destination"])
            and tx.get("repair_index") == marker
            and float(tx.get("start")) <= float(accepted_at)
            for tx in tx_by_scope[row_scope].values()
        )
        if not matching_payload:
            raise ValueError("ACK marker lacks started CPR packet")

    seen: set[Tuple[Tuple[int, str], int]] = set()
    rx_seen: set[Tuple[Tuple[int, str], int]] = set()
    node_count = int(manifest["case"]["nodes"])
    for row in jsonl_records["rx_attempts"]:
        row_scope = scope(row)
        tx_id = int(row["tx_id"])
        if tx_id not in tx_by_scope[row_scope]:
            raise ValueError("CPR RX references unknown TX")
        rx_count[row_scope][tx_id] += 1
        if row.get("rx_attempt_id") is not None:
            key = (row_scope, int(row["rx_attempt_id"]))
            if key in rx_seen:
                raise ValueError("duplicate CPR RX attempt")
            rx_seen.add(key)
            expected = accepted.get(key)
            if expected is not None:
                if row.get("reason") != "success" or not row.get("decoded"):
                    raise ValueError("accepted CPR ACK lacks physical decode")
                if (
                    tx_id != int(expected["ack_tx_id"])
                    or int(row["receiver"]) != int(expected["receiver"])
                ):
                    raise ValueError("CPR ACK provenance mismatch")
                seen.add(key)
    if seen != set(accepted):
        raise ValueError("accepted CPR ACK lacks RX attempt")
    for scope, tx_ids in tx_by_scope.items():
        for tx_id in tx_ids:
            if rx_count[scope][tx_id] != node_count:
                raise ValueError("CPR RX ledger incomplete")
    return manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--protocol", action="append", dest="protocols")
    parser.add_argument("--deadline-s", type=float, default=30.0)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--contract-path", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--case-profile", choices=tuple(CASE_PROFILES), default="smoke")
    parser.add_argument(
        "--split",
        choices=("smoke", "exploratory", "development", "holdout", "custom"),
        default="custom",
    )
    args = parser.parse_args(argv)
    args.seeds = tuple(args.seeds or (92000,))
    args.protocols = tuple(args.protocols or CPR_PROTOCOLS)
    return args


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    bundle = run_matrix(
        CASE_PROFILES[args.case_profile], args.protocols, args.seeds,
        args.deadline_s, args.split,
        contract_path=args.contract_path,
    )
    paths = write_artifacts(args.out_prefix, bundle)
    audit_artifacts(paths["manifest"])
    print(paths["manifest"])


if __name__ == "__main__":
    main()
