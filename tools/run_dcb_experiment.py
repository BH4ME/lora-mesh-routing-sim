#!/usr/bin/env python3
"""Staged, seed-paired causal experiment for MeshEcho-DCB."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet, PendingSend, Transmission
from tools import run_sr_experiment as sr


CONTRACT_PATH = ROOT / "docs" / "research" / "meshecho_dcb_protocol_contract.md"
TRIAL_CONTRACT_PATH = (
    ROOT / "docs" / "research" / "meshecho_ack_gated_trial_source_contract.md"
)
CORE_ARMS = (
    "meshecho-dcb",
    "meshecho-dcb-no-forward",
    "meshecho-dcb-unconditional",
    "meshecho-dcb-current-overhear",
    "meshecho-dhr-flood-ack-delay",
)
SOURCE_ARMS = ("meshecho-dcb-source-fr",)
TRIAL_ARMS = (
    "meshecho-dcb-trial",
    "meshecho-dcb-trial-no-switch",
    "meshecho-dcb-trial-blind",
)
TRIAL_ACK_GUARD_S = 15.0
TRIAL_GATE_BOUNDS = {
    TRIAL_ARMS[1]: {"ack_low": -0.02, "delivery_low": -0.01,
                    "air_high": 0.0, "air_mean": -0.02},
    TRIAL_ARMS[2]: {"ack_low": 0.0, "delivery_low": -0.01,
                    "air_high": 0.05, "air_mean": None},
    CORE_ARMS[0]: {"ack_low": -0.02, "delivery_low": -0.01,
                   "air_high": 0.0, "air_mean": -0.02},
    CORE_ARMS[4]: {"ack_low": -0.02, "delivery_low": -0.01,
                   "air_high": 0.0, "air_mean": -0.05},
    CORE_ARMS[3]: {"ack_low": -0.02, "delivery_low": -0.01,
                   "air_high": 0.0, "air_mean": -0.02},
}
CONTEXT_ARMS = (
    "meshecho-dhr-flood-ack-delay-flood2",
    "meshecho-sr-fr",
    "meshecho-lpr",
)
ARMS = CORE_ARMS + SOURCE_ARMS + TRIAL_ARMS + CONTEXT_ARMS
DCB_WIRE_ARMS = CORE_ARMS[:4] + SOURCE_ARMS + TRIAL_ARMS
SEEDS_BY_MODE = {
    "smoke": (47000,),
    "development": tuple(range(47001, 47021)),
    "holdout": tuple(range(48001, 48041)),
}
_CAPTURE_AUTHORIZATION = object()
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_meshecho_dcb.py",
    ROOT / "tests" / "test_dcb_experiment.py",
)


class DcbRecordingSimulator(sr.RecordingSimulator):
    """Pair each committed physical TX with its request-event time."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tx_request_times: dict[int, float] = {}
        self.committed_tx_requests: list[dict[str, Any]] = []

    def begin_transmission(self, sender: int, packet: Packet, pending: PendingSend) -> None:
        before = len(self.tx_history)
        request_time = self.now
        super().begin_transmission(sender, packet, pending)
        if len(self.tx_history) > before:
            tx_id = self.tx_history[-1].tx_id
            self.tx_request_times[tx_id] = request_time
            self.committed_tx_requests.append({
                "tx_id": tx_id, "sender": sender, "flow_id": packet.flow_id,
                "kind": packet.kind, "request_time": request_time,
            })


def queue_wait_metrics(
    transmissions: Sequence[dict[str, Any]], cutoff_s: float,
) -> dict[str, float | int]:
    waits = []
    tx_ids = set()
    for tx in transmissions:
        tx_id = tx["tx_id"]
        request_time = tx["request_time"]
        wait = tx["queue_wait_s"]
        if (tx_id in tx_ids or not all(math.isfinite(value) for value in
               (request_time, wait, tx["start"]))
                or request_time > tx["start"] + 1e-12
                or wait < -1e-12
                or not math.isclose(wait, tx["start"] - request_time,
                                    rel_tol=1e-10, abs_tol=1e-10)):
            raise ValueError("DCB TX request/start join or queue wait differs")
        tx_ids.add(tx_id)
        if tx["start"] <= cutoff_s:
            waits.append(max(0.0, wait))
    ordered = sorted(waits)
    return {
        "queued_tx_count": sum(wait > 1e-12 for wait in waits),
        "tx_queue_wait_mean_s": sum(waits) / len(waits) if waits else 0.0,
        "tx_queue_wait_p95_s": ordered[math.ceil(0.95 * len(ordered)) - 1]
        if ordered else 0.0,
        "tx_queue_wait_max_s": ordered[-1] if ordered else 0.0,
    }


def replay_state_peaks(
    actions: Sequence[dict[str, Any]], node_ids: Sequence[int],
) -> dict[str, dict[str, int]]:
    nodes = set(node_ids)
    windows: set[tuple[int, int, int, int | None]] = set()
    pending: set[tuple[int, int]] = set()
    feedback_peaks = {node_id: 0 for node_id in node_ids}
    pending_peaks = {node_id: 0 for node_id in node_ids}
    last_time = -math.inf
    for event in actions:
        name = event.get("event")
        if name not in {
            "dcb_feedback_window_open", "dcb_feedback_window_close",
            "dcb_relay_pending_open", "dcb_relay_pending_close",
        }:
            continue
        when = event["time"]
        if not math.isfinite(when) or when < last_time - 1e-9:
            raise ValueError("DCB state transition time differs")
        last_time = when
        if name.startswith("dcb_feedback"):
            node = event["dst"]
            key = (node, event["src"], event["flow_id"], event["repair_index"])
            active = windows
            cap = 8
        else:
            node = event["relay"]
            key = (node, event["flow_id"])
            active = pending
            cap = 4
        if node not in nodes:
            raise ValueError("DCB state transition node differs")
        if name.endswith("_open"):
            if key in active:
                raise ValueError("DCB duplicate state transition open")
            active.add(key)
        else:
            if key not in active:
                raise ValueError("DCB unmatched state transition close")
            active.remove(key)
        count = sum(item[0] == node for item in active)
        if event["active_count"] != count or count > cap:
            raise ValueError("DCB state transition count differs")
        if name == "dcb_feedback_window_open":
            feedback_peaks[node] = max(feedback_peaks[node], count)
        elif name == "dcb_relay_pending_open":
            pending_peaks[node] = max(pending_peaks[node], count)
    return {
        "peak_feedback_windows_by_destination": {
            str(node): peak for node, peak in feedback_peaks.items()
        },
        "peak_pending_backups_by_relay": {
            str(node): peak for node, peak in pending_peaks.items()
        },
    }


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("ascii")).hexdigest()


def input_hashes() -> dict[str, str]:
    hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }
    hashes["docs/research/meshecho_dcb_protocol_contract.md"] = hashlib.sha256(
        CONTRACT_PATH.read_bytes()
    ).hexdigest()
    hashes["docs/research/meshecho_ack_gated_trial_source_contract.md"] = hashlib.sha256(
        TRIAL_CONTRACT_PATH.read_bytes()
    ).hexdigest()
    return hashes


def _validate_stage(
    mode: str, seeds: tuple[int, ...], case: sr.SrCase, deadline_s: float,
    stage_authorization_path: Path | None,
    prerequisite_manifest_path: Path | None = None,
) -> tuple[dict[str, str], bytes]:
    if mode not in SEEDS_BY_MODE:
        raise ValueError(f"unknown DCB mode: {mode}")
    if seeds != SEEDS_BY_MODE[mode] or any(type(seed) is not int for seed in seeds):
        raise ValueError(f"{mode} seeds must match the exact DCB cohort")
    if case != sr.SR_CASES["recurring_fading"] or deadline_s != 30.0:
        raise ValueError("DCB stages require the frozen recurring-fading case and 30-s deadline")
    status_lines = [
        line for line in CONTRACT_PATH.read_text(encoding="utf-8").splitlines()[:15]
        if "Status:" in line
    ]
    if len(status_lines) != 1 or not re.search(
        r"\bStatus:\s*frozen\b", status_lines[0], flags=re.IGNORECASE,
    ):
        raise ValueError("DCB contract must be frozen before simulation")
    trial_status_lines = [
        line for line in TRIAL_CONTRACT_PATH.read_text(encoding="utf-8").splitlines()[:15]
        if "Status:" in line
    ]
    if len(trial_status_lines) != 1 or not re.search(
        r"\bStatus:\s*frozen\b", trial_status_lines[0], flags=re.IGNORECASE,
    ):
        raise ValueError("DCB trial contract must be frozen before simulation")
    if mode == "smoke" and prerequisite_manifest_path is not None:
        raise ValueError("DCB smoke cannot name a predecessor")
    if mode != "smoke" and prerequisite_manifest_path is None:
        raise ValueError(f"{mode} requires a verified predecessor manifest")
    if stage_authorization_path is None:
        raise ValueError(f"{mode} stage authorization is required")
    authorization_data = Path(stage_authorization_path).read_bytes()
    authorization = json.loads(authorization_data)
    frozen_inputs = input_hashes()
    prerequisites = {}
    if prerequisite_manifest_path is not None:
        prerequisites["predecessor_manifest"] = hashlib.sha256(
            Path(prerequisite_manifest_path).read_bytes()
        ).hexdigest()
    expected = {
        "mode": mode,
        "seeds": list(seeds),
        "protocols": list(ARMS),
        "case_sha256": _hash_json(asdict(case)),
        "application_deadline_s": deadline_s,
        "input_sha256": frozen_inputs,
        "prerequisite_manifest_sha256": prerequisites,
    }
    if authorization != expected:
        raise ValueError(f"{mode} stage authorization differs from frozen inputs")
    if prerequisite_manifest_path is not None:
        prior_mode = "smoke" if mode == "development" else "development"
        try:
            audited = audit_artifacts(
                Path(prerequisite_manifest_path), expected_mode=prior_mode,
                expected_input_sha256=frozen_inputs,
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("DCB predecessor artifact audit failed") from exc
        if mode == "holdout" and audited.get("trial_project_gate") is not True:
            raise ValueError("DCB holdout predecessor trial core gate did not pass")
    return frozen_inputs, authorization_data


def _physical_initial_starts(run: dict[str, Any]) -> dict[int, dict[str, Any]]:
    flows = {flow["flow_id"]: flow for flow in run["flows"]}
    decisions = {}
    duplicate_decisions = set()
    for event in run["actions"]:
        if event.get("event") != "decision":
            continue
        flow_id = event["flow_id"]
        if flow_id in decisions:
            duplicate_decisions.add(flow_id)
        decisions[flow_id] = event
    packet_kinds = {"F": "FLOOD", "R": "DATA", "D": "RREQ"}
    starts: dict[int, dict[str, Any]] = {}
    for tx in run["transmissions"]:
        packet = tx["packet"]
        flow_id = packet["flow_id"]
        flow = flows.get(flow_id)
        decision = decisions.get(flow_id)
        if flow is None or decision is None or flow_id in duplicate_decisions:
            continue
        action = decision.get("action")
        path = tuple(packet["path"])
        if (decision.get("src") != flow["src"]
                or decision.get("dst") != flow["dst"]
                or not math.isclose(decision["time"], flow["enqueued_at"], abs_tol=1e-9)
                or (action != "D" and flow.get("source_action") != action)
                or packet["kind"] != packet_kinds.get(action)
                or packet["repair_index"] is not None
                or packet["request_id"] != flow_id
                or packet["origin"] != flow["src"]
                or packet["final_dst"] != flow["dst"]
                or tx["sender"] != flow["src"]
                or not path or path[0] != flow["src"]
                or (action == "R" and path[-1] != flow["dst"])
                or (action in {"F", "D"} and path != (flow["src"],))
                or not flow["enqueued_at"] - 1e-9 <= tx["start"] <= flow["deadline_at"] + 1e-9
                or tx["start"] < decision["time"] - 1e-9):
            continue
        previous = starts.get(flow_id)
        if previous is None or tx["start"] < previous["start"]:
            starts[flow_id] = {
                "action": action, "path": path, "start": tx["start"],
            }
    return starts


def _physical_trial_exposure(
    rows: Sequence[dict[str, Any]], actions: Sequence[dict[str, Any]],
    physical_runs: Sequence[dict[str, Any]] | None,
) -> dict[str, Any]:
    names = (
        "accepted_backup_acks", "physical_trial_starts",
        "ordinary_trial_ack_commits", "source_guard_abandonments",
        "guard_divergent_followups", "initial_source_decision_differences",
        "initial_path_differences",
    )
    exposure: dict[str, Any] = {
        "physical_evidence_complete": False,
        **{name: 0 for name in names},
        **{f"{name}_seeds": 0 for name in names},
        "initial_actions": {
            role: {action: 0 for action in ("F", "R", "D")}
            for role in ("trial", "blind", "old_dcb")
        },
    }
    if physical_runs is None:
        return exposure
    by_key = {(run.get("seed"), run.get("protocol")): run for run in physical_runs}
    row_by_key = {(row["seed"], row["protocol"]): row for row in rows}
    if (len(by_key) != len(rows) or set(by_key) != set(row_by_key)
            or any(run.get("row") != row_by_key[key]
                   or not all(field in run for field in
                              ("flows", "actions", "transmissions"))
                   for key, run in by_key.items())
            or list(actions) != [event for run in physical_runs
                                 for event in run["actions"]]):
        return exposure
    exposure["physical_evidence_complete"] = True
    seeds_by_name: dict[str, set[int]] = {name: set() for name in names}
    flows_by_name: dict[str, set[tuple[int, int]]] = {name: set() for name in names}

    def count(name: str, seed: int, flow_id: int) -> None:
        key = (seed, flow_id)
        if key in flows_by_name[name]:
            return
        flows_by_name[name].add(key)
        exposure[name] += 1
        seeds_by_name[name].add(seed)

    for seed in sorted({row["seed"] for row in rows}):
        trial = by_key[(seed, TRIAL_ARMS[0])]
        blind = by_key[(seed, TRIAL_ARMS[2])]
        old_dcb = by_key[(seed, CORE_ARMS[0])]
        trial_flows = {flow["flow_id"]: flow for flow in trial["flows"]}
        blind_flows = {flow["flow_id"]: flow for flow in blind["flows"]}
        old_flows = {flow["flow_id"]: flow for flow in old_dcb["flows"]}
        starts = {
            "trial": _physical_initial_starts(trial),
            "blind": _physical_initial_starts(blind),
            "old_dcb": _physical_initial_starts(old_dcb),
        }
        for role, run in (("trial", trial), ("blind", blind), ("old_dcb", old_dcb)):
            for start in starts[role].values():
                exposure["initial_actions"][role][start["action"]] += 1

        def ack_tx(flow_id: int, when: float, path: tuple[int, ...],
                   repair_index: int | None) -> bool:
            flow = trial_flows.get(flow_id)
            if flow is None or len(path) < 2:
                return False
            return any(
                tx["sender"] == path[1]
                and tx["packet"]["kind"] == "ACK"
                and tx["packet"]["flow_id"] == flow_id
                and tx["packet"]["origin"] == flow["dst"]
                and tx["packet"]["final_dst"] == flow["src"]
                and tx["packet"]["repair_index"] == repair_index
                and tuple(tx["packet"]["path"]) == path
                and math.isclose(tx["end"], when, abs_tol=1e-9)
                for tx in trial["transmissions"]
            )

        pending_paths: dict[tuple[int, int], tuple[tuple[int, ...], float]] = {}
        for event in trial["actions"]:
            name = event.get("event")
            flow_id = event.get("flow_id")
            flow = trial_flows.get(flow_id)
            if flow is None:
                continue
            if name == "trial_pending":
                pending_paths[(flow["src"], flow["dst"])] = (
                    tuple(event["path"]), event["time"],
                )
            elif name == "dcb_source_ack_rx" and event.get("accepted"):
                path = tuple(event["path"])
                if (flow["acked_at"] is not None
                        and event["time"] <= flow["deadline_at"] + 1e-9
                        and math.isclose(flow["acked_at"], event["time"], abs_tol=1e-9)
                        and ack_tx(flow_id, event["time"], path, 4)):
                    count("accepted_backup_acks", seed, flow_id)
            elif name == "decision" and event.get("reason") == "ack-proven-trial":
                pending = pending_paths.pop((flow["src"], flow["dst"]), None)
                start = starts["trial"].get(flow_id)
                if (pending is not None and pending[1] <= event["time"] + 1e-9
                        and start is not None and start["action"] == "R"
                        and start["path"] == pending[0]):
                    count("physical_trial_starts", seed, flow_id)
            elif name == "commit" and event.get("action") == "R-trial":
                start = starts["trial"].get(flow_id)
                path = tuple(event["path"])
                if (start is not None and start["path"] == path
                        and flow["acked_at"] is not None
                        and event["time"] <= flow["deadline_at"] + 1e-9
                        and math.isclose(flow["acked_at"], event["time"], abs_tol=1e-9)
                        and ack_tx(flow_id, event["time"], path, None)):
                    count("ordinary_trial_ack_commits", seed, flow_id)
            elif name == "trial_abandoned" and event.get("reason") == "source-ack-guard":
                start = starts["trial"].get(flow_id)
                if (start is None or start["action"] != "R"
                        or not math.isclose(event["time"],
                                            start["start"] + TRIAL_ACK_GUARD_S,
                                            abs_tol=1e-9)
                        or event["time"] > flow["deadline_at"] + 1e-9
                        or (flow["acked_at"] is not None
                            and flow["acked_at"] <= event["time"] + 1e-9)):
                    continue
                count("source_guard_abandonments", seed, flow_id)
                following = min((
                    later for later in trial_flows.values()
                    if later["src"] == flow["src"] and later["dst"] == flow["dst"]
                    and later["enqueued_at"] > event["time"] + 1e-9
                ), key=lambda later: (later["enqueued_at"], later["flow_id"]), default=None)
                if following is None:
                    continue
                next_id = following["flow_id"]
                control_flow = blind_flows.get(next_id)
                trial_start = starts["trial"].get(next_id)
                blind_start = starts["blind"].get(next_id)
                if (control_flow is not None
                        and control_flow["src"] == following["src"]
                        and control_flow["dst"] == following["dst"]
                        and control_flow["enqueued_at"] == following["enqueued_at"]
                        and trial_start is not None and blind_start is not None
                        and (trial_start["action"], trial_start["path"])
                        != (blind_start["action"], blind_start["path"])):
                    count("guard_divergent_followups", seed, flow_id)

        for flow_id, trial_start in starts["trial"].items():
            control_flow = old_flows.get(flow_id)
            trial_flow = trial_flows[flow_id]
            control_start = starts["old_dcb"].get(flow_id)
            if (control_flow is None or control_start is None
                    or (trial_flow["src"], trial_flow["dst"], trial_flow["enqueued_at"])
                    != (control_flow["src"], control_flow["dst"], control_flow["enqueued_at"])):
                continue
            if trial_start["action"] != control_start["action"]:
                count("initial_source_decision_differences", seed, flow_id)
            if trial_start["path"] != control_start["path"]:
                count("initial_path_differences", seed, flow_id)
    for name, selected in seeds_by_name.items():
        exposure[f"{name}_seeds"] = len(selected)
    return exposure


def _trial_exposure_gate(exposure: dict[str, Any], *, evaluable: bool) -> bool:
    floors = {
        "physical_trial_starts": (20, 10),
        "ordinary_trial_ack_commits": (10, 5),
        "guard_divergent_followups": (10, 5),
        "initial_source_decision_differences": (20, 10),
    }
    return bool(
        evaluable and exposure["physical_evidence_complete"]
        and all(exposure[name] >= count and exposure[f"{name}_seeds"] >= seeds
                for name, (count, seeds) in floors.items())
    )


def summarize_dcb(
    rows: Sequence[dict[str, Any]], actions: Sequence[dict[str, Any]],
    mode: str, *, invalid_accepted_acks: int = 0,
    physical_runs: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate the prespecified paired and physical-action DCB gates."""

    if mode not in SEEDS_BY_MODE:
        raise ValueError(f"unknown DCB mode: {mode}")
    seeds = SEEDS_BY_MODE[mode]
    run_keys = [(row["seed"], row["protocol"]) for row in rows]
    expected_keys = {(seed, arm) for seed in seeds for arm in ARMS}
    if (len(run_keys) != len(expected_keys) or set(run_keys) != expected_keys
            or any(row.get("seed_split") != mode for row in rows)):
        raise ValueError("DCB run matrix differs from the exact staged cohort")
    comparisons = sr.summarize_paired(rows, ARMS[0], ARMS[1:])
    by_comparator = {item["comparator"]: item for item in comparisons}
    evaluable = mode != "smoke" and len(seeds) >= 20
    trial_comparisons = sr.summarize_paired(
        rows, TRIAL_ARMS[0], tuple(TRIAL_GATE_BOUNDS),
    )
    trial_by_comparator = {item["comparator"]: item for item in trial_comparisons}
    for item in trial_comparisons:
        bounds = TRIAL_GATE_BOUNDS[item["comparator"]]
        item.pop("reliability_cost_gate", None)
        item["trial_primary_gate"] = bool(
            evaluable
            and item["ack_pdr_ci95_low"] > bounds["ack_low"]
            and item["destination_pdr_ci95_low"] > bounds["delivery_low"]
            and item["relative_airtime_ci95_high"] < bounds["air_high"]
            and (bounds["air_mean"] is None
                 or item["relative_airtime_cost"] <= bounds["air_mean"])
        )
    trial_statistical_gate = all(
        item["trial_primary_gate"] for item in trial_comparisons
    )
    trial_exposure = _physical_trial_exposure(rows, actions, physical_runs)
    invalid_trial_actions = (
        _invalid_trial_action_count(physical_runs)
        if trial_exposure["physical_evidence_complete"] else None
    )
    trial_exposure_gate = _trial_exposure_gate(trial_exposure, evaluable=evaluable)
    trial_provenance_gate = bool(
        trial_exposure["physical_evidence_complete"]
        and invalid_accepted_acks == 0 and invalid_trial_actions == 0
    )
    for item in comparisons:
        comparator = item["comparator"]
        if comparator in SOURCE_ARMS + TRIAL_ARMS:
            item.pop("reliability_cost_gate", None)
            item["dcb_primary_gate"] = None
            item["comparison_role"] = (
                "source-candidate" if comparator == TRIAL_ARMS[0]
                else "source-control"
            )
            item["seed_split"] = mode
            continue
        if comparator in CONTEXT_ARMS:
            item.pop("reliability_cost_gate", None)
            item["dcb_primary_gate"] = None
            item["comparison_role"] = "contextual"
            item["seed_split"] = mode
            continue
        ack_ok = item["ack_pdr_ci95_low"] > -0.02
        delivery_ok = item["destination_pdr_ci95_low"] > -0.01
        air_ok = item["relative_airtime_ci95_high"] < 0.0
        if comparator == ARMS[4]:
            gate = ack_ok and delivery_ok and air_ok and item["relative_airtime_cost"] <= -0.05
        elif comparator == ARMS[3]:
            gate = ack_ok and delivery_ok and air_ok and item["relative_airtime_cost"] <= -0.02
        elif comparator == ARMS[1]:
            gate = ack_ok and delivery_ok and air_ok
        else:
            gate = air_ok
        item.pop("reliability_cost_gate", None)
        item["dcb_primary_gate"] = bool(evaluable and gate)
        item["comparison_role"] = "component"
        item["seed_split"] = mode
    backup_actions = [
        event
        for event in actions
        if event.get("event") == "dcb_backup_tx"
        and event.get("protocol") == ARMS[0]
        and float(event["time"]) <= 630.0
    ]
    trial_actions = [
        event for event in actions
        if event.get("protocol") == TRIAL_ARMS[0]
        and float(event["time"]) <= 630.0
    ]
    blind_actions = [
        event for event in actions
        if event.get("protocol") == TRIAL_ARMS[2]
        and float(event["time"]) <= 630.0
    ]
    trial_events = {
        "pending": sum(event.get("event") == "trial_pending"
                       for event in trial_actions),
        "attempted": sum(event.get("event") == "decision"
                         and event.get("reason") == "ack-proven-trial"
                         for event in trial_actions),
        "committed": sum(event.get("event") == "commit"
                         and event.get("action") == "R-trial"
                         for event in trial_actions),
        "abandoned": sum(event.get("event") == "trial_abandoned"
                         for event in trial_actions),
        "blind_committed": sum(event.get("event") == "commit"
                               and event.get("action") == "R-backup-blind"
                               for event in blind_actions),
    }
    current_actions = [
        event
        for event in actions
        if event.get("event") == "dcb_backup_tx"
        and event.get("protocol") == ARMS[3]
        and float(event["time"]) <= 630.0
    ]
    def forwarding_by_flow(events: Sequence[dict[str, Any]]) -> dict[tuple[int, int], set[int]]:
        forwarding: dict[tuple[int, int], set[int]] = {}
        for event in events:
            forwarding.setdefault((event["seed"], event["flow_id"]), set()).add(
                event["relay"]
            )
        return forwarding

    backup_by_flow = forwarding_by_flow(backup_actions)
    current_by_flow = forwarding_by_flow(current_actions)
    differences = {
        key for key in backup_by_flow.keys() | current_by_flow.keys()
        if backup_by_flow.get(key, set()) != current_by_flow.get(key, set())
    }
    exposure_gate = bool(
        evaluable
        and len(backup_actions) >= 20
        and len({event["seed"] for event in backup_actions}) >= 10
        and len(differences) >= 20
        and len({event[0] for event in differences}) >= 10
    )
    statistical_gate = bool(
        len(by_comparator) == len(ARMS) - 1
        and all(by_comparator[arm]["dcb_primary_gate"]
                for arm in CORE_ARMS[1:])
    )
    current = by_comparator[ARMS[3]]
    equivalent_to_current = bool(
        evaluable
        and current["relative_airtime_ci95_low"] >= -0.02
        and current["relative_airtime_ci95_high"] <= 0.02
        and current["ack_pdr_ci95_low"] >= -0.01
        and current["ack_pdr_ci95_high"] <= 0.01
    )
    return {
        "comparisons": comparisons,
        "trial_comparisons": trial_comparisons,
        "trial_vs_no_switch": trial_by_comparator[TRIAL_ARMS[1]],
        "trial_vs_blind": trial_by_comparator[TRIAL_ARMS[2]],
        "trial_events": trial_events,
        "trial_exposure": trial_exposure,
        "invalid_trial_actions": invalid_trial_actions,
        "trial_statistical_gate": trial_statistical_gate,
        "trial_exposure_gate": trial_exposure_gate,
        "trial_provenance_gate": trial_provenance_gate,
        "trial_project_gate": bool(
            trial_statistical_gate and trial_exposure_gate and trial_provenance_gate
        ),
        "statistical_gate": statistical_gate,
        "backup_tx_starts": len(backup_actions),
        "backup_tx_seeds": len({event["seed"] for event in backup_actions}),
        "forwarding_action_differences": len(differences),
        "forwarding_difference_seeds": len({event[0] for event in differences}),
        "exposure_gate": exposure_gate,
        "accepted_invalid_acks": invalid_accepted_acks,
        "provenance_gate": invalid_accepted_acks == 0,
        "equivalent_to_current_overhear": equivalent_to_current,
        "project_gate": bool(
            statistical_gate and exposure_gate and invalid_accepted_acks == 0
        ),
    }


def capture_arm(
    case: sr.SrCase, protocol: str, seed: int, deadline_s: float,
    *, mode: str, stage_authorization_path: Path,
    prerequisite_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Capture the unchanged SR-runner metrics and every physical TX start."""

    _validate_stage(
        mode, SEEDS_BY_MODE.get(mode, ()), case, deadline_s,
        stage_authorization_path, prerequisite_manifest_path,
    )
    if type(seed) is not int or seed not in SEEDS_BY_MODE[mode]:
        raise ValueError("DCB capture requires the stage's exact reserved cohort")
    if protocol not in ARMS:
        raise ValueError(f"non-DCB experiment arm: {protocol}")
    recorder_type = DcbRecordingSimulator
    captured: list[DcbRecordingSimulator] = []

    def make_recorder(*args: Any, **kwargs: Any) -> DcbRecordingSimulator:
        simulator = recorder_type(*args, **kwargs)
        captured.append(simulator)
        return simulator

    with patch.object(sr, "RecordingSimulator", make_recorder):
        result = sr.run_one_sr(
            case, protocol, seed, deadline_s,
            research_authorization=_CAPTURE_AUTHORIZATION,
            stage_authorization_path=stage_authorization_path,
            prerequisite_manifest_path=prerequisite_manifest_path,
        )
    if len(captured) != 1:
        raise AssertionError("SR runner did not create exactly one simulator")
    simulator = captured[0]
    transmissions = []
    for tx in simulator.tx_history:
        request_time = simulator.tx_request_times[tx.tx_id]
        transmissions.append({
            **asdict(tx), "request_time": request_time,
            "queue_wait_s": tx.start - request_time,
        })
    result.row.update(queue_wait_metrics(
        transmissions, case.duration_s + deadline_s,
    ))
    protocol_state = simulator.protocol
    node_ids = sorted(simulator.nodes)
    feedback_peaks = getattr(protocol_state, "peak_feedback_windows_by_destination", {})
    pending_peaks = getattr(protocol_state, "peak_pending_backups_by_relay", {})
    seen_floods = getattr(protocol_state, "seen_floods", {})
    state = {
        "peak_feedback_windows_by_destination": {
            str(node_id): feedback_peaks.get(node_id, 0) for node_id in node_ids
        },
        "peak_pending_backups_by_relay": {
            str(node_id): pending_peaks.get(node_id, 0) for node_id in node_ids
        },
        "peak_seen_floods_by_node": {
            str(node_id): len(seen_floods.get(node_id, ())) for node_id in node_ids
        },
        "seen_floods_unbounded": True,
    }
    result.row.update({
        "feedback_window_sum_of_node_peaks": sum(
            state["peak_feedback_windows_by_destination"].values()
        ),
        "relay_pending_sum_of_node_peaks": sum(
            state["peak_pending_backups_by_relay"].values()
        ),
        "seen_floods_final_total": sum(state["peak_seen_floods_by_node"].values()),
    })
    return {
        "seed": seed,
        "protocol": protocol,
        "row": result.row,
        "flows": result.flows,
        "actions": result.actions,
        "transmissions": transmissions,
        "tx_requests": simulator.committed_tx_requests,
        "state": state,
    }


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


def _invalid_accepted_ack_count(runs: Sequence[dict[str, Any]]) -> int:
    invalid = 0
    for run in runs:
        if run["protocol"] not in DCB_WIRE_ARMS:
            continue
        flows = {flow["flow_id"]: flow for flow in run["flows"]}
        transmissions = [_decode_transmission(tx) for tx in run["transmissions"]]
        for event in run["actions"]:
            if event.get("event") != "dcb_source_ack_rx" or not event.get("accepted"):
                continue
            flow = flows.get(event["flow_id"])
            path = tuple(event["path"])
            epoch = event.get("epoch")
            when = event["time"]
            if (flow is None or len(path) != 3 or len(set(path)) != 3
                    or path[0] != flow["src"] or path[-1] != flow["dst"]
                    or when > flow["deadline_at"]
                    or flow.get("acked_at") is None
                    or not math.isclose(when, flow["acked_at"], abs_tol=1e-9)
                    or not flow["ack_by_deadline"]):
                invalid += 1
                continue
            source, relay, destination = path
            nominated = any(
                tx.sender == source and tx.packet.kind == "DATA"
                and tx.packet.flow_id == event["flow_id"]
                and tx.packet.repair_index is None
                and tx.packet.path == (source, destination)
                and tx.packet.backup_relay_id is not None
                and tx.packet.backup_epoch_id == epoch
                and tx.start <= when
                and (run["protocol"] == ARMS[3]
                     or tx.packet.backup_relay_id == relay)
                for tx in transmissions
            )
            backup = any(
                tx.sender == relay and tx.packet.kind == "DATA"
                and tx.packet.flow_id == event["flow_id"]
                and tx.packet.repair_index == 4
                and tx.packet.path == path
                and tx.packet.backup_epoch_id == epoch
                and tx.end <= when
                for tx in transmissions
            )
            destination_decode = any(
                receipt.get("event") == "dhr_destination_rx"
                and receipt.get("flow_id") == event["flow_id"]
                and receipt.get("src") == source
                and receipt.get("dst") == destination
                and receipt.get("repair_index") == 4
                and any(
                    tx.sender == relay and tx.packet.kind == "DATA"
                    and tx.packet.flow_id == event["flow_id"]
                    and tx.packet.repair_index == 4
                    and tx.packet.path == path
                    and tx.packet.backup_epoch_id == epoch
                    and math.isclose(receipt["time"], tx.end, abs_tol=1e-9)
                    for tx in transmissions
                )
                for receipt in run["actions"]
            )
            ack_hops = {
                tx.sender for tx in transmissions
                if tx.packet.kind == "ACK"
                and tx.packet.flow_id == event["flow_id"]
                and tx.packet.repair_index == 4
                and tx.packet.path == path
                and tx.packet.backup_epoch_id == epoch
                and tx.end <= when + 1e-9
            }
            if (not nominated or not backup or not destination_decode
                    or not {destination, relay} <= ack_hops):
                invalid += 1
    return invalid


def _invalid_trial_action_count(runs: Sequence[dict[str, Any]]) -> int:
    invalid = 0
    for run in runs:
        protocol = run["protocol"]
        if protocol not in TRIAL_ARMS:
            continue
        flows = {flow["flow_id"]: flow for flow in run["flows"]}
        transmissions = [_decode_transmission(tx) for tx in run["transmissions"]]
        accepted_backups = {
            (event["flow_id"], event["time"], tuple(event["path"]))
            for event in run["actions"]
            if event.get("event") == "dcb_source_ack_rx"
            and event.get("accepted")
        }
        pending: dict[tuple[int, int], tuple[int, tuple[int, ...], float]] = {}
        attempts: dict[int, tuple[tuple[int, ...], float]] = {}
        for event in run["actions"]:
            name = event.get("event")
            trial_decision = name == "decision" and event.get("reason") == "ack-proven-trial"
            trial_commit = name == "commit" and event.get("action") == "R-trial"
            blind_commit = name == "commit" and event.get("action") == "R-backup-blind"
            if (protocol != TRIAL_ARMS[0]
                    and (name in {"trial_pending", "trial_abandoned"}
                         or trial_decision or trial_commit)):
                invalid += 1
                continue
            if protocol != TRIAL_ARMS[2] and blind_commit:
                invalid += 1
                continue
            if name == "trial_pending":
                flow = flows.get(event["flow_id"])
                path = tuple(event["path"])
                if (flow is None or len(path) != 3 or len(set(path)) != 3
                        or path[0] != flow["src"] or path[-1] != flow["dst"]
                        or event["src"] != flow["src"]
                        or event["dst"] != flow["dst"]
                        or (event["flow_id"], event["time"], path)
                        not in accepted_backups):
                    invalid += 1
                    continue
                pending[(flow["src"], flow["dst"])] = (
                    event["flow_id"], path, event["time"],
                )
            elif trial_decision:
                flow = flows.get(event["flow_id"])
                key = (event["src"], event["dst"])
                candidate = pending.pop(key, None)
                first_tx = min((
                    tx for tx in transmissions
                    if tx.sender == key[0] and tx.packet.kind == "DATA"
                    and tx.packet.flow_id == event["flow_id"]
                    and tx.packet.repair_index is None
                ), key=lambda tx: (tx.start, tx.tx_id), default=None)
                if (flow is None or candidate is None
                        or flow["src"] != key[0] or flow["dst"] != key[1]
                        or event["action"] != "R"
                        or event["flow_id"] <= candidate[0]
                        or candidate[2] > event["time"] + 1e-9
                        or first_tx is None
                        or first_tx.packet.request_id != event["flow_id"]
                        or first_tx.packet.origin != key[0]
                        or first_tx.packet.final_dst != key[1]
                        or first_tx.packet.path != candidate[1]
                        or first_tx.start < event["time"] - 1e-9
                        or first_tx.start > flow["deadline_at"] + 1e-9):
                    invalid += 1
                    continue
                attempts[event["flow_id"]] = (candidate[1], first_tx.start)
            elif trial_commit:
                flow = flows.get(event["flow_id"])
                attempt = attempts.get(event["flow_id"])
                path = attempt[0] if attempt is not None else None
                if (flow is None or path is None
                        or tuple(event["path"]) != path
                        or event["src"] != flow["src"]
                        or event["dst"] != flow["dst"]
                        or flow["acked_at"] is None
                        or not math.isclose(flow["acked_at"], event["time"], abs_tol=1e-9)
                        or not any(
                            tx.sender == path[1] and tx.packet.kind == "ACK"
                            and tx.packet.flow_id == event["flow_id"]
                            and tx.packet.repair_index is None
                            and tx.packet.path == path
                            and math.isclose(tx.end, event["time"], abs_tol=1e-9)
                            for tx in transmissions
                        )):
                    invalid += 1
            elif name == "trial_abandoned":
                flow = flows.get(event["flow_id"])
                attempt = attempts.get(event["flow_id"])
                if (flow is None or attempt is None
                        or event.get("reason") not in
                        {"source-ack-guard", "new-route-commit"}
                        or (event.get("reason") == "source-ack-guard"
                            and not math.isclose(
                                event["time"], attempt[1] + TRIAL_ACK_GUARD_S,
                                abs_tol=1e-9,
                            ))
                        or (flow["acked_at"] is not None
                            and flow["acked_at"] <= event["time"])):
                    invalid += 1
            elif blind_commit:
                flow = flows.get(event["flow_id"])
                path = tuple(event["path"])
                if (flow is None or len(path) != 3
                        or event["src"] != flow["src"]
                        or event["dst"] != flow["dst"]
                        or (event["flow_id"], event["time"], path)
                        not in accepted_backups):
                    invalid += 1
    return invalid


def _write_jsonl(path: Path, records: Sequence[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(
                record, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source]


def _persist_evidence(
    output_dir: Path, report: dict[str, Any], case: sr.SrCase,
    deadline_s: float, authorization_data: bytes,
) -> Path:
    output_dir.mkdir()
    runs = report["runs"]
    artifacts = {
        "runs.jsonl": [
            {"seed": run["seed"], "protocol": run["protocol"], "row": run["row"]}
            for run in runs
        ],
        "flows.jsonl": [flow for run in runs for flow in run["flows"]],
        "actions.jsonl": [action for run in runs for action in run["actions"]],
        "transmissions.jsonl": [
            {"seed": run["seed"], "protocol": run["protocol"], **tx}
            for run in runs for tx in run["transmissions"]
        ],
        "tx_requests.jsonl": [
            {"seed": run["seed"], "protocol": run["protocol"], **request}
            for run in runs for request in run["tx_requests"]
        ],
        "state.jsonl": [
            {"seed": run["seed"], "protocol": run["protocol"], "state": run["state"]}
            for run in runs
        ],
        "paired.jsonl": report["summary"]["comparisons"],
    }
    for name, records in artifacts.items():
        _write_jsonl(output_dir / name, records)
    with (output_dir / "authorization.json").open("xb") as output:
        output.write(authorization_data)
    manifest = {
        "format": "meshecho-dcb-evidence-v1",
        "mode": report["mode"],
        "case": asdict(case),
        "application_deadline_s": deadline_s,
        "seeds": report["seeds"],
        "protocols": report["protocols"],
        "tx_cost_window": {
            "last_tx_start_s": case.duration_s + deadline_s,
            "full_packet_toa_for_included_tx": True,
            "includes_all_network_transmissions": True,
        },
        "input_sha256": report["input_sha256"],
        "stage_authorization_sha256": report["stage_authorization_sha256"],
        "prerequisite_manifest_sha256": report["prerequisite_manifest_sha256"],
        "artifact_sha256": {
            name: hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
            for name in artifacts
        },
        "runs": len(runs),
        "scheduled_unicast_flows": sum(
            run["row"]["scheduled_unicast_flows"] for run in runs
        ),
        "gate_summary": {
            key: value for key, value in report["summary"].items()
            if key != "comparisons"
        },
    }
    path = output_dir / "manifest.json"
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n")
    return path


def audit_artifacts(
    manifest_path: Path, *, expected_mode: str | None = None,
    expected_input_sha256: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Reconstruct paired outcomes and physical costs from archived evidence."""

    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    directory = manifest_path.parent
    mode = manifest["mode"]
    if (manifest.get("format") != "meshecho-dcb-evidence-v1"
            or mode not in SEEDS_BY_MODE
            or (expected_mode is not None and mode != expected_mode)
            or manifest["seeds"] != list(SEEDS_BY_MODE[mode])
            or manifest["protocols"] != list(ARMS)
            or manifest["application_deadline_s"] != 30.0):
        raise ValueError("DCB archived stage identity differs")
    case = sr.SrCase(**manifest["case"])
    if case != sr.SR_CASES["recurring_fading"]:
        raise ValueError("DCB archived case differs from frozen case")
    frozen_inputs = input_hashes()
    if (manifest["input_sha256"] != frozen_inputs
            or (expected_input_sha256 is not None
                and manifest["input_sha256"] != expected_input_sha256)):
        raise ValueError("DCB archived input hashes differ from frozen source")
    names = ("runs.jsonl", "flows.jsonl", "actions.jsonl",
             "transmissions.jsonl", "tx_requests.jsonl", "state.jsonl",
             "paired.jsonl")
    if set(manifest["artifact_sha256"]) != set(names):
        raise ValueError("DCB archived artifact inventory differs")
    records = {}
    for name in names:
        path = directory / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["artifact_sha256"][name]:
            raise ValueError(f"DCB artifact hash differs: {name}")
        records[name] = _read_jsonl(path)
    authorization_data = (directory / "authorization.json").read_bytes()
    expected_authorization = {
        "mode": mode, "seeds": manifest["seeds"],
        "protocols": manifest["protocols"],
        "case_sha256": _hash_json(asdict(case)),
        "application_deadline_s": 30.0,
        "input_sha256": manifest["input_sha256"],
        "prerequisite_manifest_sha256": manifest["prerequisite_manifest_sha256"],
    }
    if (json.loads(authorization_data) != expected_authorization
            or hashlib.sha256(authorization_data).hexdigest()
            != manifest["stage_authorization_sha256"]):
        raise ValueError("DCB archived authorization differs from stage")
    expected_keys = {(seed, arm) for seed in SEEDS_BY_MODE[mode] for arm in ARMS}
    run_records = records["runs.jsonl"]
    run_keys = [(record["seed"], record["protocol"]) for record in run_records]
    if len(run_keys) != len(expected_keys) or set(run_keys) != expected_keys:
        raise ValueError("DCB archived run cohort differs")
    grouped = {
        name: {key: [] for key in expected_keys}
        for name in ("flows.jsonl", "actions.jsonl", "transmissions.jsonl",
                     "tx_requests.jsonl", "state.jsonl")
    }
    for name in grouped:
        for record in records[name]:
            key = (record["seed"], record["protocol"])
            if key not in expected_keys:
                raise ValueError(f"DCB {name} has an out-of-cohort record")
            grouped[name][key].append(record)
    radio = sr.make_radio(sr.make_args(case))
    cutoff = case.duration_s + 30.0
    captures = []
    paired_traces: dict[int, tuple[tuple[float, int, int, int], ...]] = {}
    for record in run_records:
        key = (record["seed"], record["protocol"])
        row = record["row"]
        if (row.get("seed") != key[0] or row.get("protocol") != key[1]
                or row.get("case") != case.key or row.get("seed_split") != mode
                or row.get("case_config_sha256") != _hash_json(asdict(case))
                or row.get("generation_horizon_s") != case.duration_s
                or row.get("application_deadline_s") != 30.0
                or row.get("drain_until_s") != cutoff):
            raise ValueError(f"DCB run identity differs: {key}")
        flows = grouped["flows.jsonl"][key]
        trace = tuple(sorted(
            (flow["enqueued_at"], flow["src"], flow["dst"], flow["flow_id"])
            for flow in flows
        ))
        trace_hash = hashlib.sha256(json.dumps(
            trace, separators=(",", ":"),
        ).encode("ascii")).hexdigest()
        if (len(trace) != row["scheduled_unicast_flows"]
                or len({flow["flow_id"] for flow in flows}) != len(flows)
                or trace_hash != row["scheduled_trace_sha256"]):
            raise ValueError(f"DCB scheduled trace differs from flows: {key}")
        if key[0] in paired_traces and paired_traces[key[0]] != trace:
            raise ValueError(f"DCB paired application trace differs: seed {key[0]}")
        paired_traces[key[0]] = trace
        for flow in flows:
            deadline = flow["enqueued_at"] + 30.0
            acked = flow["acked_at"] is not None and flow["acked_at"] <= deadline
            delivered = (flow["delivered_at"] is not None
                         and flow["delivered_at"] <= deadline)
            if (flow["deadline_at"] != deadline
                    or flow["ack_by_deadline"] is not acked
                    or flow["delivery_by_deadline"] is not delivered):
                raise ValueError(f"DCB flow deadline differs: {key}")
        ack_count = sum(flow["ack_by_deadline"] for flow in flows)
        delivery_count = sum(flow["delivery_by_deadline"] for flow in flows)
        if (not flows or row["ack_by_deadline"] != ack_count
                or row["delivery_by_deadline"] != delivery_count
                or not math.isclose(row["ack_pdr_deadline"], ack_count / len(flows), abs_tol=1e-12)
                or not math.isclose(row["destination_pdr_deadline"], delivery_count / len(flows), abs_tol=1e-12)):
            raise ValueError(f"DCB all-flow denominator differs: {key}")
        raw_txs = grouped["transmissions.jsonl"][key]
        raw_requests = grouped["tx_requests.jsonl"][key]
        request_by_id = {request["tx_id"]: request for request in raw_requests}
        if (len(raw_requests) != len(raw_txs)
                or len(request_by_id) != len(raw_requests)
                or set(request_by_id) != set(range(1, len(raw_txs) + 1))
                or {tx["tx_id"] for tx in raw_txs} != set(request_by_id)):
            raise ValueError(f"DCB committed request/TX IDs differ: {key}")
        for tx in raw_txs:
            request = request_by_id[tx["tx_id"]]
            if (request["sender"] != tx["sender"]
                    or request["flow_id"] != tx["packet"]["flow_id"]
                    or request["kind"] != tx["packet"]["kind"]
                    or request["request_time"] != tx["request_time"]
                    or not 0.0 <= request["request_time"] <= cutoff):
                raise ValueError(f"DCB committed request/TX join differs: {key}")
        transmissions = [_decode_transmission(tx) for tx in raw_txs]
        for tx in transmissions:
            if (tx.packet.protocol != key[1]
                    or not math.isfinite(tx.start) or not math.isfinite(tx.end)
                    or not math.isclose(
                        tx.end - tx.start, radio.packet_toa_s(tx.packet),
                        rel_tol=1e-10, abs_tol=1e-10,
                    )):
                raise ValueError(f"DCB physical TX identity or ToA differs: {key}")
        physical = sr.summarize_windowed_transmissions(
            transmissions, cutoff, case.payload_bytes,
        )
        queue_metrics = queue_wait_metrics(raw_txs, cutoff)
        for name, measured in queue_metrics.items():
            if not math.isclose(row[name], measured, rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError(f"DCB TX queue wait differs: {key} {name}")
        for name, measured in physical.items():
            reported = row[name]
            if (not math.isclose(reported, measured, rel_tol=1e-10, abs_tol=1e-10)
                    if isinstance(measured, (int, float)) else reported != measured):
                raise ValueError(f"DCB physical cost differs: {key} {name}")
        energy = (physical["whole_network_tx_airtime_s"]
                  * radio.supply_voltage_v * radio.tx_current_ma / 1000.0)
        if not math.isclose(row["tx_energy_j"], energy, rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError(f"DCB physical TX energy differs: {key}")
        state_records = grouped["state.jsonl"][key]
        if len(state_records) != 1:
            raise ValueError(f"DCB state record count differs: {key}")
        state = state_records[0]["state"]
        expected_nodes = {str(node_id) for node_id in range(case.nodes)}
        state_fields = (
            ("peak_feedback_windows_by_destination", 8,
             "feedback_window_sum_of_node_peaks"),
            ("peak_pending_backups_by_relay", 4,
             "relay_pending_sum_of_node_peaks"),
            ("peak_seen_floods_by_node", None, "seen_floods_final_total"),
        )
        if state.get("seen_floods_unbounded") is not True:
            raise ValueError(f"DCB inherited seen-set declaration differs: {key}")
        for field, cap, total in state_fields:
            counts = state[field]
            if (set(counts) != expected_nodes
                    or any(type(value) is not int or value < 0
                           or (cap is not None and value > cap)
                           for value in counts.values())
                    or row[total] != sum(counts.values())):
                raise ValueError(f"DCB state peak or total differs: {key} {field}")
            if key[1] not in DCB_WIRE_ARMS and cap is not None and any(counts.values()):
                raise ValueError(f"DCB baseline state has DCB-only peaks: {key}")
        actions = grouped["actions.jsonl"][key]
        replayed_peaks = replay_state_peaks(actions, tuple(range(case.nodes)))
        for field, replayed in replayed_peaks.items():
            if state[field] != replayed:
                raise ValueError(f"DCB state peak differs from transitions: {key} {field}")
        starts = Counter(
            (tx.packet.flow_id, tx.sender, tx.start, tx.end, tx.packet.backup_epoch_id)
            for tx in transmissions
            if tx.packet.kind == "DATA" and tx.packet.repair_index == 4
            and tx.sender != tx.packet.origin
        )
        logged = Counter(
            (event["flow_id"], event["relay"], event["time"], event["end"], event["epoch"])
            for event in actions if event.get("event") == "dcb_backup_tx"
        )
        if starts != logged:
            raise ValueError(f"DCB logged backup starts differ from physical TX: {key}")
        captures.append({
            "seed": key[0], "protocol": key[1], "row": row,
            "flows": flows, "actions": actions, "state": state,
            "tx_requests": [
                {name: value for name, value in request.items()
                 if name not in {"seed", "protocol"}}
                for request in raw_requests
            ],
            "transmissions": [
                {name: value for name, value in tx.items()
                 if name not in {"seed", "protocol"}}
                for tx in raw_txs
            ],
        })
    if _invalid_trial_action_count(captures):
        raise ValueError("DCB trial action provenance differs from physical evidence")
    summary = summarize_dcb(
        [run["row"] for run in captures],
        [event for run in captures for event in run["actions"]],
        mode, invalid_accepted_acks=_invalid_accepted_ack_count(captures),
        physical_runs=captures,
    )
    if (summary["comparisons"] != records["paired.jsonl"]
            or {key: value for key, value in summary.items() if key != "comparisons"}
            != manifest["gate_summary"]
            or manifest["runs"] != len(captures)
            or manifest["scheduled_unicast_flows"] != sum(
                run["row"]["scheduled_unicast_flows"] for run in captures
            )):
        raise ValueError("DCB archived paired results or gates differ from evidence")
    return {
        "runs": len(captures),
        "scheduled_unicast_flows": manifest["scheduled_unicast_flows"],
        "project_gate": summary["project_gate"],
        "trial_project_gate": summary["trial_project_gate"],
    }


def run_experiment(
    *, mode: str = "smoke", seeds: Sequence[int] | None = None,
    case: sr.SrCase = sr.SR_CASES["recurring_fading"], deadline_s: float = 30.0,
    stage_authorization_path: Path | None = None,
    prerequisite_manifest_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    selected_seeds = tuple(seeds) if seeds is not None else SEEDS_BY_MODE.get(mode, ())
    frozen_inputs, authorization_data = _validate_stage(
        mode, selected_seeds, case, deadline_s, stage_authorization_path,
        prerequisite_manifest_path,
    )
    if output_dir is None:
        raise ValueError("DCB output directory is required")
    output_dir = Path(output_dir)
    if not output_dir.parent.is_dir() or output_dir.exists():
        raise ValueError("DCB output directory must be new with an existing parent")
    runs = []
    for seed in selected_seeds:
        for protocol in ARMS:
            observed = capture_arm(
                case, protocol, seed, deadline_s, mode=mode,
                stage_authorization_path=Path(stage_authorization_path),
                prerequisite_manifest_path=prerequisite_manifest_path,
            )
            observed["row"]["seed_split"] = mode
            observed["flows"] = [
                {**flow, "seed_split": mode} for flow in observed["flows"]
            ]
            observed["actions"] = [
                {**event, "seed_split": mode} for event in observed["actions"]
            ]
            if (input_hashes() != frozen_inputs
                    or Path(stage_authorization_path).read_bytes()
                    != authorization_data):
                raise RuntimeError("DCB source or authorization changed during the matrix")
            runs.append(observed)
    if _invalid_trial_action_count(runs):
        raise ValueError("DCB trial action provenance differs from physical evidence")
    summary = summarize_dcb(
        [run["row"] for run in runs],
        [event for run in runs for event in run["actions"]],
        mode, invalid_accepted_acks=_invalid_accepted_ack_count(runs),
        physical_runs=runs,
    )
    prerequisites = {}
    if prerequisite_manifest_path is not None:
        prerequisites["predecessor_manifest"] = hashlib.sha256(
            Path(prerequisite_manifest_path).read_bytes()
        ).hexdigest()
    report = {
        "mode": mode,
        "seeds": list(selected_seeds),
        "protocols": list(ARMS),
        "input_sha256": frozen_inputs,
        "stage_authorization_sha256": hashlib.sha256(authorization_data).hexdigest(),
        "prerequisite_manifest_sha256": prerequisites,
        "runs": runs,
        "summary": summary,
    }
    report["manifest_path"] = str(_persist_evidence(
        output_dir, report, case, deadline_s, authorization_data,
    ))
    report["audit"] = audit_artifacts(Path(report["manifest_path"]))
    return report


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=SEEDS_BY_MODE)
    parser.add_argument("--stage-authorization", type=Path)
    parser.add_argument("--prerequisite-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--audit-manifest", type=Path)
    args = parser.parse_args(argv)
    if args.audit_manifest is not None:
        if any((args.mode, args.stage_authorization, args.prerequisite_manifest,
                args.output_dir)):
            parser.error("--audit-manifest cannot be combined with run options")
        print(json.dumps(audit_artifacts(args.audit_manifest), sort_keys=True))
        return
    if args.mode is None or args.stage_authorization is None or args.output_dir is None:
        parser.error("--mode, --stage-authorization and --output-dir are required")
    report = run_experiment(
        mode=args.mode,
        stage_authorization_path=args.stage_authorization,
        prerequisite_manifest_path=args.prerequisite_manifest,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "manifest_path": report["manifest_path"],
        "runs": report["audit"]["runs"],
        "project_gate": report["summary"]["project_gate"],
        "gate_summary": {
            key: value for key, value in report["summary"].items()
            if key != "comparisons"
        },
    }, sort_keys=True))


if __name__ == "__main__":
    from tools import run_dcb_experiment as dcb

    dcb.main()
