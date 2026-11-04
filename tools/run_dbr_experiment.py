#!/usr/bin/env python3
"""Provisional, fail-closed experiment entry point for MeshEcho-DBR."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence
from unittest.mock import patch

from lora_mesh_sim import Packet, Transmission
from tools import run_sr_experiment as sr

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "research" / "meshecho_deadline_backup_core_draft.md"
ARMS = (
    "meshecho-dbr",
    "meshecho-dbr-same",
    "meshecho-dbr-first-alt",
    "meshecho-dbr-fixed-f",
    "meshecho-dbr-fixed-f-plain",
)
SEEDS_BY_MODE = {
    "smoke": (44200,),
    "development": tuple(range(44001, 44021)),
    "holdout": tuple(range(44101, 44141)),
}
_CAPTURE_AUTHORIZATION = object()
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_meshecho_dbr.py",
    ROOT / "tests" / "test_dbr_experiment.py",
    ROOT / "tests" / "test_dbr_artifact_identity.py",
)


def input_hashes() -> dict[str, str]:
    files = {str(path.relative_to(ROOT)): path for path in SOURCE_FILES}
    files["docs/research/meshecho_deadline_backup_core_draft.md"] = CONTRACT_PATH
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in files.items()
    }


def _case_hash(case: sr.SrCase) -> str:
    data = json.dumps(asdict(case), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def _json_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_stage(
    mode: str, selected_seeds: tuple[int, ...], case: sr.SrCase,
    deadline_s: float, stage_authorization_path: Path | None,
) -> tuple[dict[str, str], bytes]:
    if mode not in SEEDS_BY_MODE:
        raise ValueError(f"unknown DBR mode: {mode}")
    if selected_seeds != SEEDS_BY_MODE[mode]:
        raise ValueError(f"{mode} seeds must match the exact reserved cohort")
    if case != sr.SR_CASES["recurring_fading"] or deadline_s != 30.0:
        raise ValueError("real DBR stages require the frozen case and 30-s deadline")
    status_lines = [
        line for line in CONTRACT_PATH.read_text(encoding="utf-8").splitlines()[:15]
        if "Status:" in line
    ]
    if len(status_lines) != 1 or not re.search(
        r"\bStatus:\s*frozen\b", status_lines[0], flags=re.IGNORECASE,
    ):
        raise ValueError("DBR contract must be frozen before simulation")
    if stage_authorization_path is None:
        raise ValueError(f"{mode} stage authorization is required")
    authorization_data = Path(stage_authorization_path).read_bytes()
    authorization = json.loads(authorization_data)
    frozen_inputs = input_hashes()
    expected = {
        "mode": mode,
        "seeds": list(selected_seeds),
        "protocols": list(ARMS),
        "case_sha256": _case_hash(case),
        "application_deadline_s": deadline_s,
        "input_sha256": frozen_inputs,
        "prerequisite_manifest_sha256": {},
    }
    if authorization != expected:
        raise ValueError(f"{mode} stage authorization differs from frozen inputs")
    if mode != "smoke":
        raise ValueError("development and holdout require predecessor artifact audit")
    return frozen_inputs, authorization_data


def capture_arm(
    case: sr.SrCase, protocol: str, seed: int, deadline_s: float,
    *, research_authorization: object | None = None,
    stage_authorization_path: Path | None = None, mode: str = "smoke",
) -> dict[str, Any]:
    """Capture one unchanged SR-runner arm and its complete physical trace."""

    _validate_stage(mode, SEEDS_BY_MODE.get(mode, ()), case, deadline_s,
                    stage_authorization_path)
    if seed not in SEEDS_BY_MODE[mode]:
        raise ValueError("DBR capture requires the stage's reserved seed")
    if protocol not in ARMS:
        raise ValueError(f"non-DBR protocol is not an experiment arm: {protocol}")
    recorder_type = sr.RecordingSimulator
    captured: list[sr.RecordingSimulator] = []

    def make_recorder(*args: Any, **kwargs: Any) -> sr.RecordingSimulator:
        simulator = recorder_type(*args, **kwargs)
        captured.append(simulator)
        return simulator

    with patch.object(sr, "RecordingSimulator", make_recorder):
        result = sr.run_one_sr(
            case, protocol, seed, deadline_s,
            research_authorization=_CAPTURE_AUTHORIZATION,
            stage_authorization_path=stage_authorization_path,
        )
    if len(captured) != 1:
        raise AssertionError("SR runner did not create exactly one simulator")
    simulator = captured[0]
    return {
        "seed": seed,
        "protocol": protocol,
        "row": result.row,
        "flows": result.flows,
        "actions": result.actions,
        "transmissions": [asdict(tx) for tx in simulator.tx_history],
        "physical": physical_cost(
            simulator.tx_history, case.duration_s + deadline_s,
            case.payload_bytes,
        ),
        "random_state_sha256": hashlib.sha256(
            repr(simulator.random.getstate()).encode("ascii")
        ).hexdigest(),
        "channel_random_state_sha256": hashlib.sha256(
            repr(simulator.channel_random.getstate()).encode("ascii")
        ).hexdigest(),
    }


def write_transmissions(path: Path, transmissions: Sequence[Transmission]) -> None:
    """Persist every physical TX field without overwriting prior evidence."""

    with Path(path).open("x", encoding="utf-8") as output:
        for transmission in transmissions:
            output.write(json.dumps(
                asdict(transmission), sort_keys=True, separators=(",", ":"),
                allow_nan=False,
            ) + "\n")


def load_transmissions(path: Path) -> list[Transmission]:
    """Restore packet path tuples before any wire-size calculation."""

    transmissions = []
    with Path(path).open(encoding="utf-8") as source:
        for line in source:
            transmissions.append(_decode_transmission(json.loads(line)))
    return transmissions


def _decode_transmission(record: dict[str, Any]) -> Transmission:
    fields = record["packet"]
    packet = Packet(**{
        **fields,
        "path": tuple(fields["path"]),
        "learned_path": tuple(fields["learned_path"]),
        "alternate_path": tuple(fields["alternate_path"]),
    })
    return Transmission(
        tx_id=record["tx_id"], sender=record["sender"],
        packet=packet, start=record["start"], end=record["end"],
    )


def physical_cost(
    transmissions: Sequence[Transmission], cutoff_s: float,
    app_payload_bytes: int,
) -> dict[str, int | float]:
    """Charge complete physical packets whose TX starts by the drain cutoff."""

    observed = [tx for tx in transmissions if tx.start <= cutoff_s]
    ack_txs = [tx for tx in observed if tx.packet.kind == "ACK"]
    backup_txs = [
        tx for tx in observed
        if tx.packet.protocol in ARMS and tx.packet.kind == "DATA"
        and tx.packet.repair_index == 3
    ]
    return {
        "whole_network_tx_airtime_s": sum(tx.end - tx.start for tx in observed),
        "windowed_tx_count": len(observed),
        "queued_future_tx_count": len(transmissions) - len(observed),
        "windowed_tx_bytes": sum(
            tx.packet.wire_size_bytes(app_payload_bytes) for tx in observed
        ),
        "windowed_ack_bytes": sum(
            tx.packet.wire_size_bytes(app_payload_bytes) for tx in ack_txs
        ),
        "windowed_ack_backup_field_bytes": sum(
            1 + 2 * len(tx.packet.alternate_path)
            for tx in ack_txs if tx.packet.alternate_path
        ),
        "windowed_backup_data_tx": len(backup_txs),
        "windowed_backup_data_source_tx": sum(
            tx.sender == tx.packet.origin for tx in backup_txs
        ),
    }


def _write_jsonl(path: Path, records: Sequence[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(
                record, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ) + "\n")


def _persist_evidence(
    output_dir: Path, report: dict[str, Any], case: sr.SrCase,
    deadline_s: float, authorization_data: bytes,
) -> Path:
    output_dir.mkdir()
    runs = report["runs"]
    artifacts = {
        "runs.jsonl": [
            {key: value for key, value in run.items()
             if key not in {"flows", "actions", "transmissions"}}
            for run in runs
        ],
        "flows.jsonl": [flow for run in runs for flow in run["flows"]],
        "actions.jsonl": [action for run in runs for action in run["actions"]],
        "transmissions.jsonl": [
            {"seed": run["seed"], "protocol": run["protocol"], **tx}
            for run in runs for tx in run["transmissions"]
        ],
    }
    for name, records in artifacts.items():
        _write_jsonl(output_dir / name, records)
    with (output_dir / "authorization.json").open("xb") as output:
        output.write(authorization_data)
    manifest = {
        "format": "meshecho-dbr-evidence-v1",
        "mode": report["mode"],
        "case": asdict(case),
        "application_deadline_s": deadline_s,
        "seeds": report["seeds"],
        "protocols": report["protocols"],
        "input_sha256": report["input_sha256"],
        "stage_authorization_sha256": report["stage_authorization_sha256"],
        "strict_replay_exact": report["strict_replay_exact"],
        "artifact_sha256": {
            name: hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
            for name in (*artifacts, "authorization.json")
        },
    }
    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ) + "\n")
    return manifest_path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source]


def _same_metric(reported: Any, recomputed: int | float) -> bool:
    if isinstance(recomputed, float):
        return (isinstance(reported, (int, float))
                and math.isclose(reported, recomputed,
                                 rel_tol=1e-12, abs_tol=1e-12))
    return reported == recomputed


def _audit_flows(
    run: dict[str, Any], flows: Sequence[dict[str, Any]],
    case: sr.SrCase, deadline_s: float,
) -> tuple[tuple[float, int, int, int], ...]:
    key = (run["seed"], run["protocol"])
    row = run["row"]
    if not flows or len(flows) != row["scheduled_unicast_flows"]:
        raise ValueError(f"DBR scheduled-flow denominator differs: {key}")
    scheduled = []
    seen_ids = set()
    for flow in flows:
        flow_id = flow["flow_id"]
        when = flow["enqueued_at"]
        deadline_at = when + deadline_s
        if (flow_id in seen_ids or flow["seed"] != key[0]
                or flow["protocol"] != key[1] or flow["case"] != case.key
                or not 0 <= when < case.duration_s
                or not math.isclose(flow["deadline_at"], deadline_at,
                                    rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError(f"DBR scheduled flow identity differs: {key}")
        seen_ids.add(flow_id)
        scheduled.append((when, flow["src"], flow["dst"], flow_id))
        for event_name, result_name, late_name in (
            ("acked_at", "ack_by_deadline", "late_ack"),
            ("delivered_at", "delivery_by_deadline", "late_delivery"),
        ):
            observed_at = flow[event_name]
            expected_by_deadline = (
                observed_at is not None and observed_at <= deadline_at
            )
            expected_late = observed_at is not None and observed_at > deadline_at
            if (observed_at is not None and observed_at < when
                    or flow[result_name] is not expected_by_deadline
                    or flow[late_name] is not expected_late):
                raise ValueError(f"DBR flow deadline semantics differ: {key}")
        expected_delay = (
            flow["acked_at"] - when if flow["ack_by_deadline"] else deadline_s
        )
        if (not _same_metric(flow["completion_delay_capped_s"], expected_delay)
                or not flow["registered"] and (
                    flow["acked_at"] is not None or flow["delivered_at"] is not None
                )):
            raise ValueError(f"DBR flow completion semantics differ: {key}")
    checks = {
        "registered_unicast_flows": sum(flow["registered"] for flow in flows),
        "ack_by_deadline": sum(flow["ack_by_deadline"] for flow in flows),
        "late_ack_count": sum(flow["late_ack"] for flow in flows),
        "delivery_by_deadline": sum(flow["delivery_by_deadline"] for flow in flows),
        "late_delivery_count": sum(flow["late_delivery"] for flow in flows),
        "ack_pdr_deadline": sum(flow["ack_by_deadline"] for flow in flows) / len(flows),
        "destination_pdr_deadline": (
            sum(flow["delivery_by_deadline"] for flow in flows) / len(flows)
        ),
        "mean_completion_delay_capped_s": (
            sum(flow["completion_delay_capped_s"] for flow in flows) / len(flows)
        ),
    }
    for name, expected in checks.items():
        if not _same_metric(row.get(name), expected):
            raise ValueError(f"DBR all-scheduled-flow metric differs: {key} {name}")
    trace = tuple(sorted(scheduled))
    digest = hashlib.sha256(json.dumps(
        trace, separators=(",", ":"),
    ).encode("ascii")).hexdigest()
    if row["scheduled_trace_sha256"] != digest:
        raise ValueError(f"DBR scheduled trace hash differs: {key}")
    return trace


def audit_artifacts(manifest_path: Path) -> dict[str, Any]:
    """Reload the persisted evidence and reject changed artifact bytes."""

    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    jsonl_names = ("runs.jsonl", "flows.jsonl", "actions.jsonl", "transmissions.jsonl")
    names = (*jsonl_names, "authorization.json")
    if (manifest.get("format") != "meshecho-dbr-evidence-v1"
            or set(manifest.get("artifact_sha256", {})) != set(names)):
        raise ValueError("DBR manifest format or artifact hashes are incomplete")
    if manifest.get("strict_replay_exact") is not True:
        raise ValueError("DBR manifest requires exact strict replay")
    if not isinstance(manifest.get("mode"), str) or manifest["mode"] not in SEEDS_BY_MODE:
        raise ValueError("DBR manifest mode is not a reserved stage")
    if (manifest.get("seeds") != list(SEEDS_BY_MODE[manifest["mode"]])
            or any(type(seed) is not int for seed in manifest["seeds"])):
        raise ValueError("DBR manifest seeds differ from reserved stage")
    if manifest.get("protocols") != list(ARMS):
        raise ValueError("DBR manifest protocol arms differ from frozen cohort")
    if manifest.get("case") != asdict(sr.SR_CASES["recurring_fading"]):
        raise ValueError("DBR manifest case differs from frozen stage")
    if manifest.get("application_deadline_s") != 30.0:
        raise ValueError("DBR manifest deadline differs from frozen stage")
    records = {}
    for name in names:
        path = manifest_path.parent / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != manifest["artifact_sha256"][name]:
            raise ValueError(f"DBR artifact SHA-256 mismatch: {name}")
        if name in jsonl_names:
            records[name] = _read_jsonl(path)
    authorization_data = (manifest_path.parent / "authorization.json").read_bytes()
    authorization = json.loads(authorization_data)
    case = sr.SrCase(**manifest["case"])
    expected_authorization = {
        "mode": manifest["mode"],
        "seeds": manifest["seeds"],
        "protocols": manifest["protocols"],
        "case_sha256": _case_hash(case),
        "application_deadline_s": manifest["application_deadline_s"],
        "input_sha256": manifest["input_sha256"],
        "prerequisite_manifest_sha256": {},
    }
    if (authorization != expected_authorization
            or hashlib.sha256(authorization_data).hexdigest()
            != manifest["stage_authorization_sha256"]):
        raise ValueError("DBR archived stage authorization differs from manifest")
    cutoff_s = case.duration_s + manifest["application_deadline_s"]
    radio = sr.make_radio(sr.make_args(case))
    flows: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for flow in records["flows.jsonl"]:
        flows.setdefault((flow["seed"], flow["protocol"]), []).append(flow)
    transmissions: dict[tuple[int, str], list[Transmission]] = {}
    raw_transmissions: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for record in records["transmissions.jsonl"]:
        key = (record["seed"], record["protocol"])
        tx = _decode_transmission(record)
        if tx.packet.protocol != key[1]:
            raise ValueError(f"DBR physical TX protocol differs: {key}")
        if (not math.isfinite(tx.start) or not math.isfinite(tx.end)
                or not math.isclose(
                    tx.end - tx.start, radio.packet_toa_s(tx.packet),
                    rel_tol=1e-10, abs_tol=1e-10,
                )):
            raise ValueError(f"DBR physical TX ToA differs: {key} {tx.tx_id}")
        transmissions.setdefault(key, []).append(tx)
        raw_transmissions.setdefault(key, []).append({
            name: value for name, value in record.items()
            if name not in {"seed", "protocol"}
        })
    actions: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for action in records["actions.jsonl"]:
        actions.setdefault((action["seed"], action["protocol"]), []).append(action)
    expected_keys = {
        (seed, protocol)
        for seed in manifest["seeds"] for protocol in manifest["protocols"]
    }
    run_keys = [(run["seed"], run["protocol"])
                for run in records["runs.jsonl"]]
    if len(run_keys) != len(expected_keys) or set(run_keys) != expected_keys:
        raise ValueError("DBR run cohort differs from manifest")
    for run in records["runs.jsonl"]:
        if type(run["seed"]) is not int or type(run["row"].get("seed")) is not int:
            raise ValueError("DBR run and row seeds must be integers")
        if run["row"].get("protocol") != run["protocol"]:
            raise ValueError("DBR row protocol differs from run wrapper")
        if run["row"].get("seed") != run["seed"]:
            raise ValueError("DBR row seed differs from run wrapper")
        if run["row"].get("case") != case.key:
            raise ValueError("DBR row case differs from manifest case")
        expected_row_identity = {
            "case_config_sha256": _case_hash(case),
            "generation_horizon_s": case.duration_s,
            "application_deadline_s": manifest["application_deadline_s"],
            "drain_until_s": cutoff_s,
        }
        for name, expected in expected_row_identity.items():
            if run["row"].get(name) != expected:
                raise ValueError(f"DBR row {name} differs from manifest")
    if (set(flows) != expected_keys or set(transmissions) != expected_keys
            or set(actions) - expected_keys):
        raise ValueError("DBR flow, action, or TX cohort differs from manifest")
    paired_traces: dict[int, tuple[tuple[float, int, int, int], ...]] = {}
    for run in records["runs.jsonl"]:
        key = (run["seed"], run["protocol"])
        trace = _audit_flows(
            run, flows.get(key, []), case, manifest["application_deadline_s"],
        )
        if key[0] in paired_traces and paired_traces[key[0]] != trace:
            raise ValueError(f"DBR cross-arm paired trace parity differs: {key[0]}")
        paired_traces[key[0]] = trace
    for run in records["runs.jsonl"]:
        key = (run["seed"], run["protocol"])
        backup_actions = Counter(
            (event["flow_id"], event["src"], event["dst"],
             tuple(event["path"]), event["time"], event["end"])
            for event in actions.get(key, [])
            if event.get("event") == "dbr_backup_tx"
        )
        backup_transmissions = Counter(
            (tx.packet.flow_id, tx.sender, tx.packet.final_dst,
             tx.packet.path, tx.start, tx.end)
            for tx in transmissions.get(key, [])
            if (tx.packet.kind == "DATA" and tx.packet.repair_index == 3
                and tx.sender == tx.packet.origin)
        )
        if backup_actions != backup_transmissions:
            raise ValueError(f"DBR backup action differs from physical TX: {key}")
        recovery_actions = Counter(
            (event["flow_id"], event["src"], event["dst"],
             event["time"], event["end"], event["repair_index"],
             event["action"])
            for event in actions.get(key, [])
            if event.get("event") == "dhr_recovery_tx"
        )
        recovery_transmissions = Counter(
            (tx.packet.flow_id, tx.sender, tx.packet.final_dst,
             tx.start, tx.end, tx.packet.repair_index,
             "R" if tx.packet.repair_index == 1 else "F")
            for tx in transmissions.get(key, [])
            if tx.sender == tx.packet.origin and (
                (tx.packet.kind, tx.packet.repair_index) in {
                    ("DATA", 1), ("FLOOD", 2),
                }
            )
        )
        if recovery_actions != recovery_transmissions:
            raise ValueError(f"DBR recovery action differs from physical TX: {key}")
        measured = physical_cost(
            transmissions.get(key, []), cutoff_s, case.payload_bytes,
        )
        for name, value in measured.items():
            reported = run.get("physical", {}).get(name)
            if not _same_metric(reported, value):
                raise ValueError(f"DBR physical cost differs: {key} {name}")
            if name in run["row"]:
                row_value = run["row"][name]
                if not _same_metric(row_value, value):
                    raise ValueError(f"DBR physical row differs: {key} {name}")
        tx_energy_j = (measured["whole_network_tx_airtime_s"]
                       * radio.supply_voltage_v * radio.tx_current_ma / 1000.0)
        if not _same_metric(run["row"].get("tx_energy_j"), tx_energy_j):
            raise ValueError(f"DBR TX energy differs from physical TX: {key}")
        replay_record = {
            **{name: value for name, value in run.items()
               if name != "strict_replay_sha256"},
            "flows": flows[key],
            "actions": actions.get(key, []),
            "transmissions": raw_transmissions[key],
        }
        if run.get("strict_replay_sha256") != _json_hash(replay_record):
            raise ValueError(f"DBR full strict replay digest differs: {key}")
    return {
        "runs": len(records["runs.jsonl"]),
        "scheduled_unicast_flows": len(records["flows.jsonl"]),
    }


def run_experiment(
    *, mode: str = "smoke", seeds: Sequence[int] | None = None,
    case: sr.SrCase = sr.SR_CASES["recurring_fading"], deadline_s: float = 30.0,
    stage_authorization_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    selected_seeds = tuple(seeds) if seeds is not None else SEEDS_BY_MODE.get(mode, ())
    frozen_inputs, authorization_data = _validate_stage(
        mode, selected_seeds, case, deadline_s, stage_authorization_path,
    )
    if output_dir is None:
        raise ValueError("DBR output directory is required")
    output_dir = Path(output_dir)
    if not output_dir.parent.is_dir():
        raise ValueError("DBR output directory parent must exist")
    if output_dir.exists():
        raise ValueError("DBR output directory already exists")
    runs = []
    for seed in selected_seeds:
        for protocol in ARMS:
            observed = capture_arm(
                case, protocol, seed, deadline_s,
                stage_authorization_path=stage_authorization_path, mode=mode,
            )
            replay = capture_arm(
                case, protocol, seed, deadline_s,
                stage_authorization_path=stage_authorization_path, mode=mode,
            )
            if observed != replay:
                raise ValueError(f"strict DBR replay differs: {seed} {protocol}")
            observed["strict_replay_sha256"] = _json_hash(replay)
            if (input_hashes() != frozen_inputs
                    or Path(stage_authorization_path).read_bytes()
                    != authorization_data):
                raise RuntimeError("DBR inputs or stage authorization changed during run")
            runs.append(observed)
    report = {
        "mode": mode,
        "seeds": list(selected_seeds),
        "protocols": list(ARMS),
        "input_sha256": frozen_inputs,
        "stage_authorization_sha256": hashlib.sha256(
            authorization_data
        ).hexdigest(),
        "strict_replay_exact": True,
        "runs": runs,
    }
    report["manifest_path"] = str(_persist_evidence(
        output_dir, report, case, deadline_s, authorization_data,
    ))
    report["audit"] = audit_artifacts(Path(report["manifest_path"]))
    return report
