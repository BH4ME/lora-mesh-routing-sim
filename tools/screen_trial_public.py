#!/usr/bin/env python3
"""Nonreserved, exploratory physical-action screen for the DCB trial core."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Sequence
from unittest.mock import patch

from tools import run_sr_experiment as sr


SEEDS = tuple(range(49201, 49211))
ARMS = (
    "meshecho-dcb-trial",
    "meshecho-dcb-trial-no-switch",
    "meshecho-dcb-trial-blind",
    "meshecho-dcb",
    "meshecho-dhr-flood-ack-delay",
)
make_recorder = sr.RecordingSimulator
ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "lora_mesh_sim.py",
    "tools/run_sr_experiment.py",
    "tools/screen_trial_public.py",
    "docs/research/meshecho_trial_public_mechanism_screen.md",
)


def fixed_case_hash() -> str:
    case = sr.SR_CASES["recurring_fading"]
    encoded = json.dumps(asdict(case), sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def source_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }


def source_initial_profiles(capture: dict[str, Any]) -> dict[int, dict[str, Any]]:
    flows = {flow["flow_id"]: flow for flow in capture["flows"]}
    decisions = {
        event["flow_id"]: event["action"]
        for event in capture["actions"]
        if event.get("event") == "decision" and event.get("flow_id") in flows
    }
    first_tx = {}
    tx_actions = {"DATA": "R", "FLOOD": "F", "RREQ": "D"}
    for tx in capture["transmissions"]:
        packet = tx.packet
        flow = flows.get(packet.flow_id)
        if (flow is None or tx.sender != flow["src"]
                or packet.origin != flow["src"] or packet.final_dst != flow["dst"]
                or packet.kind not in tx_actions or packet.repair_index is not None
                or tx.start > 630.0):
            continue
        current = first_tx.get(packet.flow_id)
        if current is None or (tx.start, tx.tx_id) < (current.start, current.tx_id):
            first_tx[packet.flow_id] = tx
    profiles = {}
    for flow_id in flows:
        tx = first_tx.get(flow_id)
        physical_action = tx_actions[tx.packet.kind] if tx is not None else None
        profiles[flow_id] = {
            "decision_action": decisions.get(flow_id),
            "physical_action": physical_action,
            "initial_path": (
                tuple(tx.packet.path) if physical_action == "R" else None
            ),
        }
    return profiles


def capture_arm(seed: int, arm: str) -> dict[str, Any]:
    if type(seed) is not int or seed not in SEEDS or arm not in ARMS:
        raise ValueError("public trial screen allows only seeds 49201--49210 and five fixed arms")
    recorders = []

    def recording_factory(*args: Any, **kwargs: Any):
        recorder = make_recorder(*args, **kwargs)
        recorders.append(recorder)
        return recorder

    with patch.object(sr, "RecordingSimulator", recording_factory):
        result = sr.run_one_sr(sr.SR_CASES["recurring_fading"], arm, seed, 30.0)
    if len(recorders) != 1:
        raise ValueError("public trial screen requires exactly one physical recorder")
    return {
        "row": result.row,
        "flows": result.flows,
        "actions": result.actions,
        "transmissions": list(recorders[0].tx_history),
    }


def summarize_screen(captures: dict[tuple[int, str], dict[str, Any]]) -> dict[str, Any]:
    expected = {(seed, arm) for seed in SEEDS for arm in ARMS}
    if set(captures) != expected:
        raise ValueError("public trial screen matrix must contain each fixed seed/arm once")
    case_hashes = {
        capture["row"].get("case_config_sha256") for capture in captures.values()
    }
    if len(case_hashes) != 1 or not next(iter(case_hashes)):
        raise ValueError("public trial screen paired case config differs between runs")
    for seed in SEEDS:
        seed_runs = [captures[(seed, arm)] for arm in ARMS]
        rows = [run["row"] for run in seed_runs]
        if any(row.get("seed") != seed or row.get("protocol") != arm
               for row, arm in zip(rows, ARMS)):
            raise ValueError("public trial screen matrix has a wrong run identity")
        if any(row.get("case") != "recurring_fading"
               or row.get("application_deadline_s") != 30.0 for row in rows):
            raise ValueError("public trial screen requires fixed case and 30-s deadline")
        if (len({row.get("case_config_sha256") for row in rows}) != 1
                or len({row.get("scheduled_trace_sha256") for row in rows}) != 1
                or len({row.get("scheduled_unicast_flows") for row in rows}) != 1
                or len({row.get("application_deadline_s") for row in rows}) != 1):
            raise ValueError("public trial screen paired case or application trace differs")
        if any(len(run["flows"]) != row["scheduled_unicast_flows"]
               for run, row in zip(seed_runs, rows)):
            raise ValueError("public trial screen saved flow count differs from scheduled count")
        traces = [tuple(sorted(
            (flow["enqueued_at"], flow["src"], flow["dst"], flow["flow_id"])
            for flow in run["flows"]
        )) for run in seed_runs]
        if len(set(traces)) != 1:
            raise ValueError("public trial screen paired scheduled flows differ")
    per_seed = []
    for seed in SEEDS:
        trial = captures[(seed, ARMS[0])]
        trial_flows = {flow["flow_id"]: flow for flow in trial["flows"]}
        trial_decisions = {
            event["flow_id"]: event for event in trial["actions"]
            if event.get("event") == "decision"
            and event.get("reason") == "ack-proven-trial"
        }
        physical_trials = {
            tx.packet.flow_id: tx for tx in trial["transmissions"]
            if tx.packet.flow_id in trial_decisions
            and tx.sender == trial_decisions[tx.packet.flow_id]["src"]
            and tx.packet.kind == "DATA"
            and tx.packet.repair_index is None
            and tx.packet.origin == tx.sender
            and tx.packet.final_dst == trial_decisions[tx.packet.flow_id]["dst"]
            and tx.packet.request_id == tx.packet.flow_id
            and len(tx.packet.path) == 3
            and len(set(tx.packet.path)) == 3
            and tx.packet.path[0] == tx.sender
            and tx.packet.path[-1] == tx.packet.final_dst
            and tx.start <= 630.0
        }
        trial_ack_commits = sum(
            event.get("event") == "commit"
            and event.get("action") == "R-trial"
            and event.get("flow_id") in physical_trials
            and tuple(event.get("path", ())) == physical_trials[event["flow_id"]].packet.path
            and trial_flows[event["flow_id"]].get("acked_at") is not None
            and math.isclose(trial_flows[event["flow_id"]]["acked_at"], event["time"], abs_tol=1e-9)
            and any(
                tx.sender == event["path"][1]
                and tx.packet.kind == "ACK"
                and tx.packet.repair_index is None
                and tx.packet.flow_id == event["flow_id"]
                and tx.packet.path == tuple(event["path"])
                and math.isclose(tx.end, event["time"], abs_tol=1e-9)
                for tx in trial["transmissions"]
            )
            for event in trial["actions"]
            if event.get("event") == "commit" and event.get("action") == "R-trial"
        )
        guard_abandonments = sum(
            event.get("event") == "trial_abandoned"
            and event.get("reason") == "source-ack-guard"
            and event.get("flow_id") in physical_trials
            and math.isclose(event["time"], physical_trials[event["flow_id"]].start + 15.0,
                             abs_tol=1e-9)
            and (trial_flows[event["flow_id"]].get("acked_at") is None
                 or trial_flows[event["flow_id"]]["acked_at"] > event["time"])
            for event in trial["actions"]
            if event.get("event") == "trial_abandoned"
        )
        blind = captures[(seed, ARMS[2])]
        accepted_blind = {
            (event["flow_id"], event["time"], tuple(event["path"]))
            for event in blind["actions"]
            if event.get("event") == "dcb_source_ack_rx" and event.get("accepted")
        }
        blind_commits = sum(
            (event["flow_id"], event["time"], tuple(event["path"])) in accepted_blind
            and any(
                tx.sender == event["path"][1]
                and tx.packet.kind == "ACK"
                and tx.packet.repair_index == 4
                and tx.packet.flow_id == event["flow_id"]
                and tx.packet.path == tuple(event["path"])
                and math.isclose(tx.end, event["time"], abs_tol=1e-9)
                for tx in blind["transmissions"]
            )
            for event in blind["actions"]
            if event.get("event") == "commit"
            and event.get("action") == "R-backup-blind"
        )
        arm_metrics = {
            arm: {
                "scheduled_unicast_flows": captures[(seed, arm)]["row"]["scheduled_unicast_flows"],
                "ack_pdr_deadline": float(captures[(seed, arm)]["row"]["ack_pdr_deadline"]),
                "destination_pdr_deadline": float(
                    captures[(seed, arm)]["row"]["destination_pdr_deadline"]
                ),
                "whole_network_tx_airtime_s": float(
                    captures[(seed, arm)]["row"]["whole_network_tx_airtime_s"]
                ),
            }
            for arm in ARMS
        }
        focus = arm_metrics[ARMS[0]]
        paired_deltas = {}
        for arm in ARMS[1:]:
            control = arm_metrics[arm]
            if control["whole_network_tx_airtime_s"] <= 0:
                raise ValueError("public trial screen comparator airtime must be positive")
            paired_deltas[arm] = {
                "ack_pdr_delta": focus["ack_pdr_deadline"] - control["ack_pdr_deadline"],
                "destination_pdr_delta": (
                    focus["destination_pdr_deadline"] - control["destination_pdr_deadline"]
                ),
                "relative_airtime_delta": (
                    focus["whole_network_tx_airtime_s"]
                    / control["whole_network_tx_airtime_s"] - 1.0
                ),
            }
        profiles = {
            arm: source_initial_profiles(captures[(seed, arm)]) for arm in ARMS
        }
        flow_divergences = {}
        for arm in ARMS[1:]:
            diverged = []
            for flow_id in sorted(profiles[ARMS[0]]):
                focus_profile = profiles[ARMS[0]][flow_id]
                control_profile = profiles[arm][flow_id]
                decision_differs = (
                    focus_profile["decision_action"] != control_profile["decision_action"]
                )
                physical_action_differs = (
                    focus_profile["physical_action"] != control_profile["physical_action"]
                )
                physical_path_differs = (
                    focus_profile["physical_action"] == "R"
                    and control_profile["physical_action"] == "R"
                    and focus_profile["initial_path"] != control_profile["initial_path"]
                )
                if decision_differs or physical_action_differs or physical_path_differs:
                    diverged.append({
                        "flow_id": flow_id,
                        "trial_decision_action": focus_profile["decision_action"],
                        "control_decision_action": control_profile["decision_action"],
                        "trial_physical_action": focus_profile["physical_action"],
                        "control_physical_action": control_profile["physical_action"],
                        "trial_initial_path": focus_profile["initial_path"],
                        "control_initial_path": control_profile["initial_path"],
                        "decision_action_differs": decision_differs,
                        "physical_action_differs": physical_action_differs,
                        "physical_path_differs": physical_path_differs,
                    })
            flow_divergences[arm] = diverged
        flow_divergence_counts = {
            arm: {
                "decision_action": sum(item["decision_action_differs"] for item in diverged),
                "physical_action": sum(item["physical_action_differs"] for item in diverged),
                "physical_path": sum(item["physical_path_differs"] for item in diverged),
                "physical_action_or_path": sum(
                    item["physical_action_differs"] or item["physical_path_differs"]
                    for item in diverged
                ),
            }
            for arm, diverged in flow_divergences.items()
        }
        per_seed.append({
            "seed": seed,
            "arm_metrics": arm_metrics,
            "paired_deltas": paired_deltas,
            "flow_divergences": flow_divergences,
            "flow_divergence_counts": flow_divergence_counts,
            "trial_decisions": len(trial_decisions),
            "physical_trial_starts": len(physical_trials),
            "ordinary_trial_ack_commits": trial_ack_commits,
            "source_guard_abandonments": guard_abandonments,
            "blind_commits": blind_commits,
        })
    starts = sum(row["physical_trial_starts"] for row in per_seed)
    start_seeds = sum(row["physical_trial_starts"] > 0 for row in per_seed)
    guard_count = sum(row["source_guard_abandonments"] for row in per_seed)
    return {
        "fixed_inputs": {
            "case": "recurring_fading",
            "case_config_sha256": next(iter(case_hashes)),
            "application_deadline_s": 30.0,
            "seeds": SEEDS,
            "arms": ARMS,
        },
        "per_seed": per_seed,
        "aggregate": {
            "trial_decisions": sum(row["trial_decisions"] for row in per_seed),
            "physical_trial_starts": starts,
            "physical_trial_start_seeds": start_seeds,
            "ordinary_trial_ack_commits": sum(
                row["ordinary_trial_ack_commits"] for row in per_seed
            ),
            "source_guard_abandonments": guard_count,
            "blind_commits": sum(row["blind_commits"] for row in per_seed),
            "exposure_screen_pass": starts >= 5 and start_seeds >= 3 and guard_count >= 1,
            "flow_divergence_counts": {
                arm: {
                    metric: sum(row["flow_divergence_counts"][arm][metric]
                                for row in per_seed)
                    for metric in ("decision_action", "physical_action",
                                   "physical_path", "physical_action_or_path")
                }
                for arm in ARMS[1:]
            },
            "mean_paired_deltas": {
                arm: {
                    metric: statistics.fmean(row["paired_deltas"][arm][metric]
                                             for row in per_seed)
                    for metric in ("ack_pdr_delta", "destination_pdr_delta",
                                   "relative_airtime_delta")
                }
                for arm in ARMS[1:]
            },
        },
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-public-screen", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.run_public_screen:
        parser.error("explicit --run-public-screen is required")
    if args.out.exists():
        raise FileExistsError(f"public trial screen output already exists: {args.out}")
    if not args.out.parent.is_dir():
        raise FileNotFoundError(f"public trial screen output directory does not exist: {args.out.parent}")

    hashes_before = source_hashes()
    captures = {
        (seed, arm): capture_arm(seed, arm)
        for seed in SEEDS for arm in ARMS
    }
    summary = summarize_screen(captures)
    if summary["fixed_inputs"]["case_config_sha256"] != fixed_case_hash():
        raise ValueError("public trial screen case config does not match fixed input")
    if hashes_before != source_hashes():
        raise ValueError("public trial screen source files changed during capture")
    summary["provenance"] = {"source_sha256": hashes_before}
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(summary, output, indent=2, sort_keys=True, allow_nan=False)
        output.write("\n")
    print(args.out)


if __name__ == "__main__":
    main()
