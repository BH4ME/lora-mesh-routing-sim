"""Read-only source-local risk screen on archived delayed-ACK traces."""

from __future__ import annotations

from collections import defaultdict
import argparse
import hashlib
from itertools import product
import json
from math import sqrt
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable


PROTOCOL = "meshecho-dhr-flood-ack-delay"
FROZEN_MANIFEST_SHA256 = "2164ac0ad4850e6be52a55b0af62893a25cd8e029e61b442a65c7bbf6c7608d7"
FROZEN_ARTIFACT_SHA256 = {
    "actions": "48fead601fb04e430f23af6c92be988b030b4cc8a0e79cc2b714030b32aff90b",
    "flows": "a90a698ab516866d1fc58dc7ecc40ec668a89f7db0837e805ea309c1f806a0e7",
    "tx": "23502d73584923bc10c107a8553d288b7a669f34129ca46953cdffa4821b6413",
}
FROZEN_SOURCE_SHA256 = {
    "lora_mesh_sim.py": "cfc7e36b7c2c78096eaefaa27b49f70b877e4d43fa76fbaef6d34d5b16d2d383",
    "tools/run_fair_multihop_probe.py": "0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e",
    "tools/run_sr_experiment.py": "8dfdb0fdb487144923e1854f803c76f7302d7b4743081a5b3fbfb9d493c74508",
    "tools/run_delayed_ack_control.py": "566f593fbfa07b8459ebcebbb101ff8a1cab170a09c819b4a7b433e603427108",
    "docs/research/meshecho_dhr_design.md": "862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59",
    "docs/research/meshecho_delayed_ack_control_design.md": "86396835b850d9dfd7fc5753acb414a5c12208aafba1e9602fe0dca93c1d8441",
    "tests/test_meshecho_dhr.py": "0f6825b1bae3222a1bd6a2275f515887087600f27d055de7cf9b8e0e31d1d7b8",
    "tests/test_delayed_flood_ack_control.py": "ff0a75b45617a92883d2665549c70d2c0f1598f096077194abef644b1a344bda",
    "tests/test_delayed_ack_control_runner.py": "742e4134d8f54e5d00708840e2f2694746b9671fde4471dc3e051c96ce814852",
}


def build_risk_records(
    flows: Iterable[dict[str, Any]],
    actions: Iterable[dict[str, Any]],
    transmissions: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join initial-R starts to source-visible history and initial-R ACKs."""

    flow_rows = [row for row in flows if row.get("protocol") == PROTOCOL]
    action_rows = [row for row in actions if row.get("protocol") == PROTOCOL]
    tx_rows = [row for row in transmissions if row.get("protocol") == PROTOCOL]
    flow_by_key = {(row["seed"], row["flow_id"]): row for row in flow_rows}
    decisions: dict[tuple[int, int], dict[str, Any]] = {}
    pair_actions: dict[tuple[int, int, int], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    flow_actions: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(action_rows):
        key = (row["seed"], row["flow_id"])
        pair_actions[(row["seed"], row["src"], row["dst"])].append((index, row))
        flow_actions[key].append(row)
        if row["event"] == "decision":
            if key in decisions:
                raise ValueError(f"duplicate initial decision: {key}")
            decisions[key] = row

    starts: dict[tuple[int, int], dict[str, Any]] = {}
    for row in tx_rows:
        packet = row["packet"]
        if (packet["kind"] != "DATA" or packet.get("repair_index") is not None
                or row["sender"] != packet["origin"]):
            continue
        key = (row["seed"], packet["flow_id"])
        if decisions.get(key, {}).get("action") != "R":
            continue
        if key in starts:
            raise ValueError(f"duplicate initial R start: {key}")
        starts[key] = row

    records = []
    for key, decision in decisions.items():
        if decision.get("action") != "R":
            continue
        if key not in starts or key not in flow_by_key:
            raise ValueError(f"initial R missing flow or physical start: {key}")
        flow, tx = flow_by_key[key], starts[key]
        packet = tx["packet"]
        if (flow["src"] != decision["src"] or flow["dst"] != decision["dst"]
                or packet["origin"] != flow["src"] or packet["final_dst"] != flow["dst"]
                or packet["request_id"] != key[1]
                or abs(flow["enqueued_at"] - decision["time"]) > 1e-8
                or abs(flow["deadline_at"] - flow["enqueued_at"] - 30.0) > 1e-8
                or tx["start"] < flow["enqueued_at"] - 1e-8
                or ("source_action" in flow and flow["source_action"] != "R")):
            raise ValueError(f"incoherent initial R flow: {key}")
        if tx["start"] > flow["deadline_at"] + 1e-8:
            raise ValueError(f"initial R started after original deadline: {key}")
        path = packet["path"]
        if len(path) < 2 or path[0] != flow["src"] or path[-1] != flow["dst"]:
            raise ValueError(f"invalid initial R path: {key}")

        recent_r = []
        failed_r = set()
        last_ack_at = None
        pair_key = (key[0], flow["src"], flow["dst"])
        for _, event in sorted(pair_actions[pair_key], key=lambda item: (item[1]["time"], item[0])):
            if event["time"] >= decision["time"]:
                break
            event_flow = event["flow_id"]
            if event["event"] == "decision" and event.get("action") == "R" and event_flow != key[1]:
                recent_r.append(event_flow)
            elif event["event"] == "commit":
                recent_r.clear()
                failed_r.clear()
            elif (event["event"] == "timeout" and event.get("reason") == "source-ack-timeout"
                  and decisions.get((key[0], event_flow), {}).get("action") == "R"):
                failed_r.add(event_flow)
            elif event["event"] == "dhr_source_ack_rx" and event.get("accepted") is True:
                last_ack_at = event["time"]
                if event.get("repair_index") is None:
                    failed_r.discard(event_flow)
        prior_r_miss = bool(recent_r and recent_r[-1] in failed_r)

        cutoff = min(tx["start"] + 15.0, flow["deadline_at"])
        accepted_initial = [
            event["time"] for event in flow_actions[key]
            if event["event"] == "dhr_source_ack_rx"
            and event.get("accepted") is True
            and event.get("repair_index") is None
            and event["time"] <= cutoff + 1e-9
        ]
        if len(accepted_initial) > 1:
            raise ValueError(f"multiple accepted initial R ACKs: {key}")
        if accepted_initial and abs(flow["acked_at"] - accepted_initial[0]) > 1e-8:
            raise ValueError(f"initial R ACK disagrees with flow record: {key}")
        records.append({
            "seed": key[0], "flow_id": key[1], "src": flow["src"], "dst": flow["dst"],
            "enqueued_at": flow["enqueued_at"], "r_tx_start": tx["start"],
            "deadline_at": flow["deadline_at"], "hops": len(path) - 1,
            "prior_r_miss": prior_r_miss,
            "last_pair_ack_age_s": None if last_ack_at is None else decision["time"] - last_ack_at,
            "initial_r_ack_by_guard": bool(accepted_initial),
        })
    return sorted(records, key=lambda row: (row["seed"], row["flow_id"]))


def _risk_cell(row: dict[str, Any], model: str) -> tuple[bool, ...]:
    cell = (bool(row["prior_r_miss"]),)
    if model in {"M1", "M2"}:
        cell += (row["hops"] == 1,)
    if model == "M2":
        age = row["last_pair_ack_age_s"]
        cell += (age is None or age >= 120.0,)
    return cell


def leave_seed_out_predictions(
    records: Iterable[dict[str, Any]], seeds: Iterable[int],
) -> list[dict[str, float]]:
    """Predict R-ACK guard failure from other seeds with Laplace cells."""

    rows = list(records)
    expected_seeds = tuple(seeds)
    if len(set(expected_seeds)) != len(expected_seeds):
        raise ValueError("duplicate validation seed")
    if set(row["seed"] for row in rows) != set(expected_seeds):
        raise ValueError("record seeds do not match validation seeds")
    predictions = []
    for row in rows:
        prediction = {}
        for model in ("M0", "M1", "M2"):
            cell = _risk_cell(row, model)
            training = [
                other for other in rows
                if other["seed"] != row["seed"]
                and _risk_cell(other, model) == cell
            ]
            failures = sum(not other["initial_r_ack_by_guard"] for other in training)
            prediction[model] = (failures + 1) / (len(training) + 2)
        predictions.append(prediction)
    return predictions


def summarize_risk(
    records: Iterable[dict[str, Any]], seeds: Iterable[int],
) -> dict[str, Any]:
    """Evaluate prespecified leave-one-seed-out risk and support gates."""

    rows = list(records)
    seed_ids = tuple(seeds)
    if len(seed_ids) != 20 or len(set(seed_ids)) != 20:
        raise ValueError("frozen risk screen requires 20 distinct seeds")
    predictions = leave_seed_out_predictions(rows, seed_ids)
    per_seed = []
    for seed in seed_ids:
        indices = [index for index, row in enumerate(rows) if row["seed"] == seed]
        if not indices:
            raise ValueError(f"no initial R observations for seed {seed}")
        result = {"seed": seed, "n": len(indices)}
        for model in ("M0", "M1", "M2"):
            result[model] = mean(
                (predictions[index][model] - float(not rows[index]["initial_r_ack_by_guard"])) ** 2
                for index in indices
            )
        per_seed.append(result)

    cells = {}
    for model, width in (("M0", 1), ("M1", 2), ("M2", 3)):
        cell_rows = []
        for cell in product((False, True), repeat=width):
            matching = [row for row in rows if _risk_cell(row, model) == cell]
            failures = sum(not row["initial_r_ack_by_guard"] for row in matching)
            cell_rows.append({
                "prior_r_miss": cell[0],
                **({"one_hop": cell[1]} if width >= 2 else {}),
                **({"old_ack": cell[2]} if width >= 3 else {}),
                "n": len(matching), "seeds": len({row["seed"] for row in matching}),
                "failures": failures,
                "failure_rate": failures / len(matching) if matching else None,
            })
        cells[model] = cell_rows

    comparisons = {}
    for left, right in (("M0", "M1"), ("M1", "M2")):
        differences = [row[left] - row[right] for row in per_seed]
        gain = mean(differences)
        half_width = 2.093024054408263 * stdev(differences) / sqrt(20)
        comparisons[f"{left}_minus_{right}"] = {
            "mean_gain": gain, "ci95": [gain - half_width, gain + half_width],
        }

    hop_support = all(row["n"] >= 20 and row["seeds"] >= 8 for row in cells["M1"])
    hop_gap = all(row["n"] > 0 for row in cells["M1"]) and all(
        next(row["failure_rate"] for row in cells["M1"]
             if row["prior_r_miss"] == miss and row["one_hop"])
        > next(row["failure_rate"] for row in cells["M1"]
               if row["prior_r_miss"] == miss and not row["one_hop"])
        for miss in (False, True)
    )
    hop_gain = comparisons["M0_minus_M1"]
    age_support = all(row["n"] >= 20 and row["seeds"] >= 8 for row in cells["M2"])
    age_gain = comparisons["M1_minus_M2"]
    gates = {
        "hop_support": hop_support,
        "hop_gap_in_both_miss_strata": hop_gap,
        "hop_actionable_risk_prerequisite": (
            hop_support and hop_gap and hop_gain["mean_gain"] >= 0.005
            and hop_gain["ci95"][0] > 0.0
        ),
        "age_incremental_support": age_support,
        "age_incremental_signal": (
            age_support and age_gain["mean_gain"] >= 0.005
            and age_gain["ci95"][0] > 0.0
        ),
    }
    return {
        "seeds": list(seed_ids), "n_initial_r": len(rows),
        "n_initial_r_ack_by_guard": sum(row["initial_r_ack_by_guard"] for row in rows),
        "per_seed": per_seed,
        "models": {model: {"mean_brier": mean(row[model] for row in per_seed)}
                   for model in ("M0", "M1", "M2")},
        "comparisons": comparisons, "cells": cells, "gates": gates,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def load_frozen_screen(prefix: Path | str) -> dict[str, Any]:
    """Validate the archived 38xxx evidence and run the read-only screen."""

    stem = str(prefix)
    manifest_path = Path(f"{stem}.manifest.json")
    if _sha256(manifest_path) != FROZEN_MANIFEST_SHA256:
        raise ValueError("frozen manifest SHA-256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    seeds = tuple(range(38001, 38021))
    if (manifest.get("seeds") != list(seeds)
            or manifest.get("seed_split") != "explore"
            or manifest.get("protocols") != [PROTOCOL, "meshecho-dhr-flood"]
            or manifest.get("runs") != 40
            or manifest.get("case", {}).get("key") != "recurring_fading"
            or manifest.get("case", {}).get("nodes") != 50
            or manifest.get("application_deadline_s") != 30.0
            or manifest.get("fixed_flood_ack_delay_s") != 2.0
            or manifest.get("source_sha256") != FROZEN_SOURCE_SHA256):
        raise ValueError("frozen manifest contract mismatch")
    for name, digest in FROZEN_ARTIFACT_SHA256.items():
        if manifest.get("artifact_sha256", {}).get(name) != digest:
            raise ValueError(f"manifest {name} SHA-256 mismatch")
        if _sha256(Path(f"{stem}.{name}.jsonl")) != digest:
            raise ValueError(f"{name} SHA-256 mismatch")

    flows = _jsonl(Path(f"{stem}.flows.jsonl"))
    actions = _jsonl(Path(f"{stem}.actions.jsonl"))
    transmissions = _jsonl(Path(f"{stem}.tx.jsonl"))
    flow_keys = [
        (row["seed"], row["flow_id"]) for row in flows
        if row.get("protocol") == PROTOCOL
    ]
    if len(flow_keys) != 781 or len(set(flow_keys)) != len(flow_keys):
        raise ValueError("frozen delayed arm flow count or identity mismatch")
    rows = build_risk_records(flows, actions, transmissions)
    report = summarize_risk(rows, seeds)
    report["provenance"] = {
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "artifact_sha256": FROZEN_ARTIFACT_SHA256,
        "historical_source_sha256": FROZEN_SOURCE_SHA256,
        "policy": PROTOCOL,
        "observational_only": True,
    }
    return report


def main() -> None:
    default_prefix = (
        Path(__file__).resolve().parents[1] / "results"
        / "meshecho_delayed_ack_control_explore_38001_38020_20261004"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=default_prefix)
    args = parser.parse_args()
    print(json.dumps(load_frozen_screen(args.prefix), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
