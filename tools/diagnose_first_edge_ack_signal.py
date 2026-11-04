#!/usr/bin/env python3
"""Passive first-edge and reverse-ACK observation for the fixed-delay control."""

from __future__ import annotations

import sys
import math
import hashlib
import json
import random
import argparse
from collections import Counter
from collections import defaultdict
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet, PendingSend, RxInfo, Transmission, required_snr_db
from tools.diagnose_ack_failure_causes import classify_failed_hop
from tools.diagnose_delayed_ack_rx import capture_run, require_stock_parity
from tools import run_sr_experiment as sr
from tools.run_sr_experiment import RecordingSimulator


ACK_WINDOW_S = 2.0
ACK2_SPACING_S = 0.5
Q_FEATURE_SCALE = 12.0
Q_SLOPE_RIDGE = 1.0
BOOTSTRAP_REPLICATES = 1000
Q_BIN_BOUNDS = (-12, -6, 0, 6, 12)
Q_BIN_LABELS = ("lt_-12", "-12_to_-6", "-6_to_0", "0_to_6",
                "6_to_12", "ge_12")
PROTOCOL = "meshecho-dhr-flood-ack-delay"
SMOKE_SEEDS = (42000,)
EXPLORATORY_SEEDS = tuple(range(42001, 42021))
VALIDATION_SEEDS = tuple(range(42101, 42121))
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "tools" / "diagnose_flood_ack_hops.py",
    ROOT / "tools" / "diagnose_ack_failure_causes.py",
    ROOT / "tools" / "diagnose_delayed_ack_rx.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_first_edge_ack_signal.py",
    ROOT / "docs" / "research" / "meshecho_first_edge_ack_signal_gate.md",
)
ARTIFACT_KEYS = (
    "summary", "runs", "paths", "epochs", "predictor_rows", "flows",
    "actions", "transmissions",
)
EPOCH_CAUSAL_REJECTION_REASONS = frozenset({
    "missing_or_multiple_source_txs",
    "missing_or_cyclic_causal_parent",
    "incoherent_causal_parent",
    "wrong_source_causal_parent",
    "missing_first_edge_decode",
})


def seeds_for_mode(mode: str) -> tuple[int, ...]:
    if mode == "smoke":
        return SMOKE_SEEDS
    if mode == "explore":
        return EXPLORATORY_SEEDS
    if mode == "validation":
        return VALIDATION_SEEDS
    raise ValueError(f"unknown first-edge diagnostic mode: {mode}")


class PassiveFirstEdgeSimulator(RecordingSimulator):
    """Retain outcomes returned by the simulator's only receive attempt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.flood_decodes: dict[int, dict[int, RxInfo]] = {}
        self.destination_flood_decodes: list[tuple[int, int]] = []
        self.ack_decodes: dict[tuple[int, int], bool] = {}
        self.ack_rxinfo: dict[tuple[int, int], RxInfo] = {}
        self.flood_parent_tx_id: dict[int, int] = {}
        self.ack_parent_tx_id: dict[int, int] = {}
        self.tx_commitment_times: dict[int, float] = {}
        self._pending_parents: dict[int, tuple[int, int]] = {}
        self._handling_tx_id: int | None = None
        self._handling_rx: tuple[int, int] | None = None

    def handle_tx_end(self, tx: Transmission) -> None:
        self._handling_tx_id = tx.tx_id
        try:
            super().handle_tx_end(tx)
        finally:
            self._handling_tx_id = None
            self._handling_rx = None

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        decoded = super().try_receive(tx, receiver)
        self._handling_rx = (tx.tx_id, receiver) if decoded is not None else None
        if tx.packet.kind == "FLOOD" and decoded is not None:
            self.flood_decodes.setdefault(tx.tx_id, {})[receiver] = decoded
            if receiver == tx.packet.final_dst:
                self.destination_flood_decodes.append((tx.tx_id, receiver))
        if tx.packet.kind == "ACK":
            index = tx.packet.path_index
            if (0 <= index < len(tx.packet.path)
                    and receiver == tx.packet.path[index]):
                self.ack_decodes[(tx.tx_id, receiver)] = decoded is not None
                if decoded is not None:
                    self.ack_rxinfo[(tx.tx_id, receiver)] = decoded
        return decoded

    def transmit_later(
        self, sender: int, packet: Packet, delay_s: float,
        pending: PendingSend | None = None,
    ) -> PendingSend:
        handle = super().transmit_later(sender, packet, delay_s, pending)
        if (self._handling_rx is not None and sender == self._handling_rx[1]
                and packet.kind in {"FLOOD", "ACK"}):
            self._pending_parents[id(handle)] = self._handling_rx
        return handle

    def begin_transmission(
        self, sender: int, packet: Packet, pending: PendingSend,
    ) -> None:
        previous_count = self.metrics.tx_count
        committed_at = self.now
        super().begin_transmission(sender, packet, pending)
        parent = self._pending_parents.pop(id(pending), None)
        if self.metrics.tx_count == previous_count:
            return
        tx_id = self.tx_history[-1].tx_id
        self.tx_commitment_times[tx_id] = committed_at
        if parent is None:
            return
        if packet.kind == "FLOOD":
            self.flood_parent_tx_id[tx_id] = parent[0]
        elif packet.kind == "ACK":
            self.ack_parent_tx_id[tx_id] = parent[0]


def trace_actual_ack(
    sim: PassiveFirstEdgeSimulator, root: Transmission,
    deadline_at_s: float, observation_cutoff_s: float,
) -> dict[str, Any]:
    """Follow actual ACK child TXs, censoring when no final-hop TX exists."""

    path = root.packet.path
    row: dict[str, Any] = {
        "ack_tx_id": root.tx_id,
        "path": list(path),
        "reverse_hops": [],
        "first_unphysical_hop": None,
        "final_hop_attempted": False,
        "final_hop_tx_id": None,
        "final_hop_physically_decoded": None,
        "final_hop_after_deadline": None,
        "final_hop_decoded_by_deadline": None,
        "source_final_first_failure": False,
    }
    if (len(path) < 2 or root.sender != path[-1]
            or root.packet.path_index != len(path) - 2):
        row["termination"] = "invalid_ack_root"
        return row
    children: dict[int, list[Transmission]] = defaultdict(list)
    for tx in sim.tx_history:
        if tx.packet.kind == "ACK":
            parent_id = sim.ack_parent_tx_id.get(tx.tx_id)
            if parent_id is not None:
                children[parent_id].append(tx)
    current = root
    visited = set()
    while current.tx_id not in visited:
        visited.add(current.tx_id)
        index = current.packet.path_index
        if index < 0 or index >= len(path) - 1:
            row["termination"] = "invalid_ack_index"
            break
        receiver = path[index]
        if index == 0:
            row["final_hop_attempted"] = True
            row["final_hop_tx_id"] = current.tx_id
            row["final_hop_after_deadline"] = current.end > deadline_at_s
        if current.end > observation_cutoff_s:
            row["termination"] = "observation_censored"
            break
        decoded = sim.ack_decodes.get((current.tx_id, receiver))
        if decoded is None:
            row["termination"] = "missing_physical_ack_observation"
            break
        hop = {
            "tx_id": current.tx_id, "edge": [current.sender, receiver],
            "decoded_at_s": current.end, "physically_decoded": decoded,
            "after_deadline": current.end > deadline_at_s,
        }
        row["reverse_hops"].append(hop)
        if index == 0:
            row["final_hop_physically_decoded"] = decoded
            if current.end <= deadline_at_s:
                row["final_hop_decoded_by_deadline"] = decoded
        if not decoded:
            row["first_unphysical_hop"] = hop
            row["source_final_first_failure"] = (
                index == 0 and current.end <= deadline_at_s
            )
            row["failure_cause"] = classify_failed_hop(
                sim, current, receiver, sim.tx_history,
                sim.tx_commitment_times, None,
            )["class"]
            row["termination"] = "physical_decode_failure"
            break
        if index == 0:
            row["termination"] = "source_physically_decoded"
            break
        next_txs = [
            child for child in children.get(current.tx_id, [])
            if child.sender == receiver and child.packet.flow_id == root.packet.flow_id
            and child.packet.request_id == root.packet.request_id
            and child.packet.repair_index == root.packet.repair_index
            and child.packet.path == path
            and child.packet.path_index == index - 1
            and child.start >= current.end - 1e-9
        ]
        if len(next_txs) != 1:
            row["termination"] = (
                "decoded_no_matching_forward" if not next_txs
                else "ambiguous_matching_forwards"
            )
            break
        current = next_txs[0]
    else:
        row["termination"] = "ack_parent_cycle"
    return row


def _epoch_key(sim: PassiveFirstEdgeSimulator, tx: Transmission) -> tuple[Any, ...]:
    packet = tx.packet
    return (sim.seed, packet.origin, packet.final_dst, packet.flow_id,
            packet.request_id, packet.repair_index)


def _causal_path(
    sim: PassiveFirstEdgeSimulator, dest_tx: Transmission,
    source_txs: dict[tuple[Any, ...], list[Transmission]],
    tx_by_id: dict[int, Transmission],
) -> tuple[dict[str, Any] | None, str | None]:
    packet = dest_tx.packet
    src, dst = packet.origin, packet.final_dst
    path = packet.path + (dst,)
    key = _epoch_key(sim, dest_tx)
    origins = source_txs.get(key, [])
    if len(origins) != 1:
        return None, "missing_or_multiple_source_txs"
    if (packet.kind != "FLOOD" or packet.request_id != packet.flow_id
            or not packet.path or dest_tx.sender != packet.path[-1]):
        return None, "invalid_destination_identity"
    if (len(path) < 2 or len(path) > sim.max_hops + 1
            or path[0] != src or path[-1] != dst or len(set(path)) != len(path)
            or packet.ttl < 1):
        return None, "invalid_path_or_ttl"
    chain = [dest_tx]
    visited = {dest_tx.tx_id}
    current = dest_tx
    while current.sender != src:
        parent_id = sim.flood_parent_tx_id.get(current.tx_id)
        parent = tx_by_id.get(parent_id)
        if parent is None or parent.tx_id in visited:
            return None, "missing_or_cyclic_causal_parent"
        prior = parent.packet
        child = current.packet
        if (prior.kind != "FLOOD" or _epoch_key(sim, parent) != key
                or prior.created_at != child.created_at
                or child.path != prior.path + (current.sender,)
                or child.ttl != prior.ttl - 1
                or current.sender not in sim.flood_decodes.get(parent.tx_id, {})
                or parent.end > current.start + 1e-9):
            return None, "incoherent_causal_parent"
        chain.append(parent)
        visited.add(parent.tx_id)
        current = parent
    source_tx = origins[0]
    if chain[-1].tx_id != source_tx.tx_id or source_tx.packet.path != (src,):
        return None, "wrong_source_causal_parent"
    first_rx = sim.flood_decodes.get(source_tx.tx_id, {}).get(path[1])
    if first_rx is None:
        return None, "missing_first_edge_decode"
    margin_q = max(-126, min(126, round(
        2.0 * (first_rx.snr_db - required_snr_db(sim.radio.sf))
    )))
    return {
        "seed": sim.seed,
        "flow_id": packet.flow_id,
        "src": src,
        "dst": dst,
        "request_id": packet.request_id,
        "repair_index": packet.repair_index,
        "path": list(path),
        "dest_tx_id": dest_tx.tx_id,
        "decoded_at_s": dest_tx.end,
        "causal_tx_ids": [tx.tx_id for tx in reversed(chain)],
        "first_edge_source_tx_id": source_tx.tx_id,
        "first_edge_rx_snr_db": first_rx.snr_db,
        "first_edge_q": margin_q,
    }, None


def analyze_first_edge(
    sim: PassiveFirstEdgeSimulator, flow_rows: Sequence[dict[str, Any]],
    observation_cutoff_s: float,
) -> dict[str, Any]:
    """Validate causally linked physical destination FLOOD decodes."""

    tx_by_id = {tx.tx_id: tx for tx in sim.tx_history}
    source_txs: dict[tuple[Any, ...], list[Transmission]] = defaultdict(list)
    for tx in sim.tx_history:
        if tx.packet.kind == "FLOOD" and tx.sender == tx.packet.origin:
            source_txs[_epoch_key(sim, tx)].append(tx)
    paths = []
    rejected = []
    ambiguous_epoch_keys = set()
    first_decode_at: dict[tuple[Any, ...], float] = {}
    for tx_id, receiver in sorted(
        sim.destination_flood_decodes,
        key=lambda entry: (tx_by_id[entry[0]].end, entry[0]),
    ):
        tx = tx_by_id[tx_id]
        if tx.end > observation_cutoff_s or receiver != tx.packet.final_dst:
            continue
        key = _epoch_key(sim, tx)
        first_decode_at.setdefault(key, tx.end)
        path, reason = _causal_path(sim, tx, source_txs, tx_by_id)
        if path is None:
            rejected.append({"dest_tx_id": tx_id, "reason": reason})
            if reason in EPOCH_CAUSAL_REJECTION_REASONS:
                ambiguous_epoch_keys.add(key)
        else:
            paths.append(path)
    paths_by_epoch: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        key = (path["seed"], path["src"], path["dst"], path["flow_id"],
               path["request_id"], path["repair_index"])
        paths_by_epoch[key].append(path)
    ack_roots_by_parent: dict[int, list[Transmission]] = defaultdict(list)
    for ack in sim.tx_history:
        if ack.packet.kind == "ACK" and ack.sender == ack.packet.origin:
            parent_id = sim.ack_parent_tx_id.get(ack.tx_id)
            if parent_id is not None:
                ack_roots_by_parent[parent_id].append(ack)
    flows = {row["flow_id"]: row for row in flow_rows}
    epochs = []
    for key in sorted(first_decode_at, key=lambda item: item[3]):
        u = first_decode_at[key]
        if key in ambiguous_epoch_keys:
            epochs.append({"flow_id": key[3], "repair_index": key[5],
                           "first_destination_decode_at_s": u,
                           "reason": "ambiguous_causal_epoch"})
            continue
        decoded = paths_by_epoch.get(key, [])
        if not decoded:
            epochs.append({"flow_id": key[3], "repair_index": key[5],
                           "first_destination_decode_at_s": u,
                           "reason": "no_valid_destination_path"})
            continue
        earliest_paths: dict[tuple[int, ...], dict[str, Any]] = {}
        for path in sorted(decoded, key=lambda item: (item["decoded_at_s"],
                                                      item["dest_tx_id"])):
            if path["decoded_at_s"] <= u + ACK_WINDOW_S + 1e-9:
                earliest_paths.setdefault(tuple(path["path"]), path)
        originals = []
        for path in decoded:
            for root in ack_roots_by_parent.get(path["dest_tx_id"], []):
                if (root.packet.path == tuple(path["path"])
                        and root.packet.repair_index == path["repair_index"]
                        and root.packet.flow_id == path["flow_id"]):
                    originals.append((root, path))
        originals.sort(key=lambda entry: (entry[0].start, entry[0].tx_id))
        if not originals:
            epochs.append({"flow_id": key[3], "repair_index": key[5],
                           "first_destination_decode_at_s": u,
                           "reason": "no_causally_linked_destination_ack"})
            continue
        root, original = originals[0]
        deadline = flows[key[3]]["deadline_at"] if key[3] in flows else None
        if deadline is None:
            epochs.append({"flow_id": key[3], "repair_index": key[5],
                           "first_destination_decode_at_s": u,
                           "reason": "missing_scheduled_flow"})
            continue

        def ack_cost(path: list[int], extra_bytes: int) -> float:
            candidate = replace(root.packet, path=tuple(path),
                                path_index=len(path) - 2)
            return ((len(path) - 1) * sim.radio.toa_s_for_bytes(
                candidate.wire_size_bytes(sim.radio.payload_bytes) + extra_bytes
            ))

        original_cost = ack_cost(original["path"], 1)
        original_first_tx_cost = original_cost / (len(original["path"]) - 1)
        alternatives = []
        for path in earliest_paths.values():
            if path["path"] == original["path"]:
                continue
            cost = ack_cost(path["path"], 1)
            source_distinct = path["path"][1] != original["path"][1]
            dest_distinct = path["path"][-2] != original["path"][-2]
            budget = source_distinct and cost <= 2 * original_cost + 1e-9
            signal = budget and path["first_edge_q"] - original["first_edge_q"] >= 6
            earliest_ack1 = u + ACK_WINDOW_S + cost
            ack2_requested = (
                u + ACK_WINDOW_S + original_first_tx_cost + ACK2_SPACING_S
            )
            earliest_ack2 = ack2_requested + cost
            both_complete_earliest = max(
                u + ACK_WINDOW_S + original_cost, earliest_ack2,
            )
            serial_completion = (
                u + ACK_WINDOW_S + original_cost + ACK2_SPACING_S + cost
            )
            alternatives.append({
                "path": path["path"], "dest_tx_id": path["dest_tx_id"],
                "first_edge_q": path["first_edge_q"],
                "destination_adjacent_distinct": dest_distinct,
                "A_distinct_first_edge": source_distinct,
                "B_within_two_original_ack_copies": budget,
                "C_first_edge_q_gain_at_least_6": signal,
                "ack_cost_s": cost,
                "ack_cost_lifetime_plus_2_bytes_s": ack_cost(path["path"], 3),
                "two_ack_pair_cost_s": original_cost + cost,
                "two_same_path_ack_cost_s": 2 * original_cost,
                "nominal_ack1_completion_at_s": earliest_ack1,
                "nominal_ack1_deadline_feasible": (
                    earliest_ack1 <= deadline if deadline is not None else None
                ),
                "nominal_ack2_completion_at_s": earliest_ack2,
                "nominal_ack2_deadline_feasible": (
                    both_complete_earliest <= deadline
                    if deadline is not None else None
                ),
                "nominal_ack2_requested_at_s": ack2_requested,
                "nominal_both_acks_complete_at_s": both_complete_earliest,
                "serial_nonoverlap_pair_completion_at_s": serial_completion,
            })
        epochs.append({
            "flow_id": key[3], "repair_index": key[5],
            "epoch_type": "initial_F" if key[5] is None else "R_to_F",
            "first_destination_decode_at_s": u,
            "original_dest_tx_id": original["dest_tx_id"],
            "original_ack_tx_id": root.tx_id,
            "original_path": original["path"],
            "first_edge_q": original["first_edge_q"],
            "original_ack_cost_s": original_cost,
            "original_ack_cost_lifetime_plus_2_bytes_s": ack_cost(original["path"], 3),
            "nominal_original_ack_completion_at_s": u + ACK_WINDOW_S + original_cost,
            "deadline_at_s": deadline,
            "ack_attempt": trace_actual_ack(
                sim, root, deadline, observation_cutoff_s,
            ),
            "alternatives": alternatives,
        })
    predictor_rows = []
    for epoch in epochs:
        attempt = epoch.get("ack_attempt")
        if attempt is None or attempt["final_hop_decoded_by_deadline"] is None:
            continue
        final_tx = tx_by_id[attempt["final_hop_tx_id"]]
        source_tx = tx_by_id[next(
            item["first_edge_source_tx_id"] for item in paths
            if item["dest_tx_id"] == epoch["original_dest_tx_id"]
        )]
        interval = sim.radio.temporal_fading_interval_s
        crossed = (
            sim.radio.temporal_fading_sigma_db > 0 and interval > 0
            and math.floor(source_tx.start / interval)
            != math.floor(final_tx.start / interval)
        )
        predictor_rows.append({
            "seed": sim.seed, "flow_id": epoch["flow_id"],
            "repair_index": epoch["repair_index"],
            "first_edge_q": epoch["first_edge_q"],
            "path_type": "direct" if len(epoch["original_path"]) == 2 else "multihop",
            "success_by_deadline": attempt["final_hop_decoded_by_deadline"],
            "final_hop_tx_id": final_tx.tx_id,
            "final_hop_rx_collided": (
                sim.ack_rxinfo[(final_tx.tx_id, epoch["original_path"][0])].collided
                if sim.ack_decodes.get((final_tx.tx_id, epoch["original_path"][0]))
                else None
            ),
            "failure_cause": (
                attempt.get("failure_cause")
                if attempt["first_unphysical_hop"] is not None
                else "after_deadline" if not attempt["final_hop_decoded_by_deadline"]
                else None
            ),
            "fading_block_crossed": crossed,
        })
    delivered_unacked = {
        flow_id for flow_id, flow in flows.items()
        if flow["delivery_by_deadline"] and not flow["ack_by_deadline"]
    }
    strata: dict[str, set[int]] = {
        key: set() for key in ("destination_flood", "final_failed", "A", "B", "C", "D")
    }
    for epoch in epochs:
        flow_id = epoch["flow_id"]
        if flow_id not in delivered_unacked or "ack_attempt" not in epoch:
            continue
        strata["destination_flood"].add(flow_id)
        if not epoch["ack_attempt"]["source_final_first_failure"]:
            continue
        strata["final_failed"].add(flow_id)
        alternatives = epoch["alternatives"]
        for level, field in (
            ("A", "A_distinct_first_edge"),
            ("B", "B_within_two_original_ack_copies"),
            ("C", "C_first_edge_q_gain_at_least_6"),
        ):
            if any(alt[field] for alt in alternatives):
                strata[level].add(flow_id)
        if any(alt["C_first_edge_q_gain_at_least_6"]
               and alt["nominal_ack1_deadline_feasible"]
               for alt in alternatives):
            strata["D"].add(flow_id)
    q_bins: dict[str, dict[str, int]] = {
        label: {"samples": 0, "successes": 0, "failures": 0}
        for label in Q_BIN_LABELS
    }
    path_types: dict[str, dict[str, int]] = {
        label: {"samples": 0, "successes": 0, "failures": 0,
                "fading_block_crossings": 0}
        for label in ("direct", "multihop")
    }
    for row in predictor_rows:
        index = next((index for index, bound in enumerate(Q_BIN_BOUNDS)
                      if row["first_edge_q"] < bound), len(Q_BIN_BOUNDS))
        q_bucket = q_bins[Q_BIN_LABELS[index]]
        type_bucket = path_types[row["path_type"]]
        for bucket in (q_bucket, type_bucket):
            bucket["samples"] += 1
            bucket["successes" if row["success_by_deadline"] else "failures"] += 1
        type_bucket["fading_block_crossings"] += int(row["fading_block_crossed"])

    def screen_stratum(selected: Sequence[dict[str, Any]]) -> dict[str, int]:
        return {
            "source_final_failed_flows": len({epoch["flow_id"] for epoch in selected}),
            "A_flows": len({epoch["flow_id"] for epoch in selected
                            if any(alt["A_distinct_first_edge"]
                                   for alt in epoch["alternatives"])}),
            "B_flows": len({epoch["flow_id"] for epoch in selected
                            if any(alt["B_within_two_original_ack_copies"]
                                   for alt in epoch["alternatives"])}),
            "C_flows": len({epoch["flow_id"] for epoch in selected
                            if any(alt["C_first_edge_q_gain_at_least_6"]
                                   for alt in epoch["alternatives"])}),
            "C_deadline_feasible_flows": len({
                epoch["flow_id"] for epoch in selected
                if any(alt["C_first_edge_q_gain_at_least_6"]
                       and alt["nominal_ack1_deadline_feasible"]
                       for alt in epoch["alternatives"])
            }),
        }

    failed_epochs = [
        epoch for epoch in epochs
        if epoch["flow_id"] in delivered_unacked
        and epoch.get("ack_attempt", {}).get("source_final_first_failure")
    ]
    screen_by_path_type = {
        label: screen_stratum([
            epoch for epoch in failed_epochs
            if ("direct" if len(epoch["original_path"]) == 2 else "multihop") == label
        ]) for label in ("direct", "multihop")
    }
    screen_by_epoch_type = {
        label: screen_stratum([
            epoch for epoch in failed_epochs if epoch["epoch_type"] == label
        ]) for label in ("initial_F", "R_to_F")
    }
    summary = {
        "scheduled_flows": len(flow_rows),
        "physical_destination_flood_decodes": sum(
            tx_by_id[tx_id].end <= observation_cutoff_s
            for tx_id, _ in sim.destination_flood_decodes
        ),
        "destination_flood_epochs": len(first_decode_at),
        "valid_path_decodes": len(paths),
        "rejected_path_decodes": len(rejected),
        "epochs_with_causal_ack": sum("ack_attempt" in item for item in epochs),
        "original_direct_epochs": sum(
            len(epoch["original_path"]) == 2
            for epoch in epochs if "original_path" in epoch
        ),
        "original_multihop_epochs": sum(
            len(epoch["original_path"]) > 2
            for epoch in epochs if "original_path" in epoch
        ),
        "initial_f_epochs": sum(
            epoch.get("epoch_type") == "initial_F" for epoch in epochs
        ),
        "r_to_f_epochs": sum(
            epoch.get("epoch_type") == "R_to_F" for epoch in epochs
        ),
        "source_adjacent_diversity_epochs": sum(
            any(alt["A_distinct_first_edge"] for alt in epoch["alternatives"])
            for epoch in epochs if "alternatives" in epoch
        ),
        "destination_adjacent_diversity_epochs": sum(
            any(alt["destination_adjacent_distinct"]
                for alt in epoch["alternatives"])
            for epoch in epochs if "alternatives" in epoch
        ),
        "delivered_unacked_flood_flows": len(strata["destination_flood"]),
        "source_final_failed_flows": len(strata["final_failed"]),
        "A_flows": len(strata["A"]),
        "B_flows": len(strata["B"]),
        "C_flows": len(strata["C"]),
        "C_deadline_feasible_flows": len(strata["D"]),
        "final_hop_predictor_samples": len(predictor_rows),
        "final_hop_predictor_successes": sum(
            row["success_by_deadline"] for row in predictor_rows
        ),
        "final_hop_predictor_failures": sum(
            not row["success_by_deadline"] for row in predictor_rows
        ),
        "late_final_hop_txs": sum(
            epoch.get("ack_attempt", {}).get("final_hop_after_deadline") is True
            for epoch in epochs
        ),
        "ack_attempts_without_source_adjacent_tx": sum(
            "ack_attempt" in epoch
            and not epoch["ack_attempt"]["final_hop_attempted"]
            for epoch in epochs
        ),
        "final_hop_failure_causes": dict(sorted(Counter(
            row["failure_cause"] for row in predictor_rows
            if row["failure_cause"] is not None
        ).items())),
        "predictor_by_q_bin": q_bins,
        "predictor_by_path_type": path_types,
        "screen_by_original_path_type": screen_by_path_type,
        "screen_by_epoch_type": screen_by_epoch_type,
    }
    return {"paths": paths, "rejected_paths": rejected,
            "epochs": epochs, "predictor_rows": predictor_rows,
            "summary": summary}


def run_diagnostic(
    seed: int, case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> dict[str, Any]:
    """Replay fixed-delay stock and passive runs, then strictly repeat the latter."""

    stock, _ = capture_run(case, seed, sr.RecordingSimulator, deadline_s)
    observed, sim = capture_run(case, seed, PassiveFirstEdgeSimulator, deadline_s)
    parity = require_stock_parity(stock, observed)

    def assert_analysis_rng_unchanged(evidence: Any, analyzed_sim: Any) -> None:
        if (hashlib.sha256(repr(analyzed_sim.random.getstate()).encode("ascii")).hexdigest()
                != evidence.random_state_sha256
                or hashlib.sha256(repr(analyzed_sim.channel_random.getstate()).encode("ascii")).hexdigest()
                != evidence.channel_random_state_sha256):
            raise AssertionError(f"passive analysis consumed RNG at seed {seed}")

    analysis = analyze_first_edge(
        sim, observed.flows, case.duration_s + deadline_s,
    )
    assert_analysis_rng_unchanged(observed, sim)
    replay, replay_sim = capture_run(
        case, seed, PassiveFirstEdgeSimulator, deadline_s,
    )
    if observed != replay:
        raise AssertionError(f"instrumented physical replay differed at seed {seed}")
    replay_analysis = analyze_first_edge(
        replay_sim, replay.flows, case.duration_s + deadline_s,
    )
    assert_analysis_rng_unchanged(replay, replay_sim)
    if analysis != replay_analysis:
        raise AssertionError(f"diagnostic analysis replay differed at seed {seed}")
    return {
        "seed": seed,
        "case": asdict(case),
        "protocol": PROTOCOL,
        "parity": parity,
        "strict_replay_exact": True,
        "row": observed.row,
        "flows": observed.flows,
        "actions": observed.actions,
        "transmissions": observed.transmissions,
        **analysis,
    }


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def fit_q_predictor(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Fit the frozen monotone one-feature ridge logistic predictor."""

    if not rows or any(row.get("first_edge_q") is None for row in rows):
        raise ValueError("q training rows must be nonempty and unambiguous")
    observed = [(row["first_edge_q"] / Q_FEATURE_SCALE,
                 int(row["success_by_deadline"])) for row in rows]
    rate = sum(label for _, label in observed) / len(observed)
    clipped = max(1e-6, min(1 - 1e-6, rate))
    intercept = math.log(clipped / (1 - clipped))
    slope = 0.0
    for _ in range(100):
        g0 = g1 = h00 = h01 = 0.0
        h11 = Q_SLOPE_RIDGE
        g1 += Q_SLOPE_RIDGE * slope
        for x, label in observed:
            p = _sigmoid(intercept + slope * x)
            weight = max(1e-9, p * (1 - p))
            g0 += p - label
            g1 += (p - label) * x
            h00 += weight
            h01 += weight * x
            h11 += weight * x * x
        determinant = h00 * h11 - h01 * h01
        if determinant <= 0:
            break
        delta0 = (g0 * h11 - g1 * h01) / determinant
        delta1 = (g1 * h00 - g0 * h01) / determinant
        if slope - delta1 < 0:
            intercept = math.log(clipped / (1 - clipped))
            slope = 0.0
            break
        intercept -= delta0
        slope -= delta1
        if max(abs(delta0), abs(delta1)) < 1e-10:
            break
    training_by_path_type = {}
    for path_type in ("direct", "multihop"):
        subset = [row for row in rows if row["path_type"] == path_type]
        training_by_path_type[path_type] = {
            **_sample_support(subset),
            "success_rate": (
                sum(row["success_by_deadline"] for row in subset) / len(subset)
                if subset else None
            ),
        }
    return {
        "model": "nonnegative_slope_ridge_logistic_q_only",
        "intercept": intercept, "slope": slope,
        "q_feature_scale": Q_FEATURE_SCALE,
        "slope_ridge": Q_SLOPE_RIDGE,
        "training_success_rate": rate,
        "training_samples": len(observed),
        "training_successes": sum(label for _, label in observed),
        "training_seeds": len({row["seed"] for row in rows}),
        "training_by_path_type": training_by_path_type,
    }


def _rank_auc(scores_and_labels: Sequence[tuple[float, int]]) -> float | None:
    positives = sum(label for _, label in scores_and_labels)
    negatives = len(scores_and_labels) - positives
    if positives == 0 or negatives == 0:
        return None
    ordered = sorted(scores_and_labels)
    lower_negatives = 0
    concordant = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        group_positive = sum(label for _, label in ordered[index:end])
        group_negative = end - index - group_positive
        concordant += group_positive * (
            lower_negatives + 0.5 * group_negative
        )
        lower_negatives += group_negative
        index = end
    return concordant / (positives * negatives)


def evaluate_q_predictor(
    model: dict[str, Any], rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Apply a frozen training model to untouched rows and seed-bootstrap AUC."""

    if not rows or any(row.get("first_edge_q") is None for row in rows):
        raise ValueError("q validation rows must be nonempty and unambiguous")
    scored = [
        (row, _sigmoid(model["intercept"]
                       + model["slope"] * row["first_edge_q"] / Q_FEATURE_SCALE),
         int(row["success_by_deadline"]))
        for row in rows
    ]

    def assess(
        selected: Sequence[tuple[dict[str, Any], float, int]],
        constant_rate: float,
    ) -> dict[str, Any]:
        labels = [label for _, _, label in selected]
        by_seed: dict[int, list[tuple[float, int]]] = defaultdict(list)
        for row, score, label in selected:
            by_seed[row["seed"]].append((score, label))
        seeds = sorted(by_seed)
        boot_auc = []
        if seeds:
            boot_rng = random.Random(42100)
            for _ in range(BOOTSTRAP_REPLICATES):
                sampled = [pair for _ in seeds
                           for seed in [boot_rng.choice(seeds)]
                           for pair in by_seed[seed]]
                auc = _rank_auc(sampled)
                if auc is not None:
                    boot_auc.append(auc)
        boot_auc.sort()
        lower = (boot_auc[int(0.025 * (len(boot_auc) - 1))]
                 if len(boot_auc) >= 0.95 * BOOTSTRAP_REPLICATES else None)
        brier_model = (
            sum((score - label) ** 2 for _, score, label in selected) / len(selected)
            if selected else None
        )
        brier_constant = (
            sum((constant_rate - label) ** 2 for label in labels) / len(selected)
            if selected else None
        )
        sample_gate = (
            len(selected) >= 100 and sum(labels) >= 20
            and len(selected) - sum(labels) >= 20 and len(seeds) >= 10
        )
        return {
            "samples": len(selected), "successes": sum(labels),
            "failures": len(selected) - sum(labels), "seeds": len(seeds),
            "brier_model": brier_model,
            "brier_training_constant": brier_constant,
            "auc": _rank_auc([(score, label) for _, score, label in selected]),
            "seed_bootstrap_auc_replicates": len(boot_auc),
            "seed_bootstrap_auc_95_lower": lower,
            "sample_gate_passed": sample_gate,
            "prediction_gate_passed": bool(
                sample_gate and brier_model is not None
                and brier_constant is not None and brier_model < brier_constant
                and lower is not None and lower > 0.5
            ),
        }

    pooled = assess(scored, model["training_success_rate"])
    strata = {}
    for path_type in ("direct", "multihop"):
        training = model["training_by_path_type"][path_type]
        training_rate = training["success_rate"]
        selected = [item for item in scored if item[0]["path_type"] == path_type]
        strata[path_type] = assess(
            selected,
            training_rate if training_rate is not None
            else model["training_success_rate"],
        )
        strata[path_type]["training_sample_gate_passed"] = training["passed"]
        strata[path_type]["prediction_gate_passed"] &= training["passed"]
    validated = [
        path_type for path_type in ("direct", "multihop")
        if strata[path_type]["prediction_gate_passed"]
    ]
    return {
        **pooled,
        "pooled_prediction_gate_passed": pooled["prediction_gate_passed"],
        "prediction_gate_passed": bool(pooled["sample_gate_passed"] and validated),
        "any_validated_path_type": bool(pooled["sample_gate_passed"] and validated),
        "claim_scope": (
            "both" if len(validated) == 2 else
            validated[0] if pooled["sample_gate_passed"] and validated else "none"
        ),
        "validated_path_types": validated,
        "by_path_type": strata,
    }


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def _sample_support(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(row["success_by_deadline"] for row in rows)
    return {
        "samples": len(rows), "successes": successes,
        "failures": len(rows) - successes,
        "seeds": len({row["seed"] for row in rows}),
        "passed": bool(
            len(rows) >= 100 and successes >= 20
            and len(rows) - successes >= 20
            and len({row["seed"] for row in rows}) >= 10
        ),
    }


def run_report(
    seeds: Sequence[int], case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    mode: str = "synthetic", deadline_s: float = 30.0,
    smoke_manifest_path: Path | None = None,
    explore_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Run a frozen split only after its prior artifact gate passes."""

    seed_tuple = tuple(seeds)
    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("diagnostic seeds must be nonempty and unique")
    if mode == "synthetic":
        if any(35001 <= seed <= 36040 or 42000 <= seed <= 42120
               for seed in seed_tuple):
            raise ValueError("synthetic mode cannot open reserved or sealed seeds")
    elif seed_tuple != seeds_for_mode(mode):
        raise ValueError(f"{mode} requires its exact preregistered seed cohort")
    source_sha256 = _source_hashes()
    case_sha256 = _sha256_json(asdict(case))
    prerequisite_sha256: dict[str, str] = {}
    if mode in {"explore", "validation"}:
        if smoke_manifest_path is None:
            raise ValueError("exploration and validation require a verified smoke manifest")
        validate_manifest(
            smoke_manifest_path, expected_mode="smoke",
            expected_source_sha256=source_sha256,
            expected_case_sha256=case_sha256,
            expected_deadline_s=deadline_s,
        )
        prerequisite_sha256["smoke_manifest"] = hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()
    explore_manifest = None
    if mode == "validation":
        if explore_manifest_path is None:
            raise ValueError("validation requires a verified exploration manifest")
        explore_manifest = validate_manifest(
            explore_manifest_path, expected_mode="explore",
            expected_source_sha256=source_sha256,
            expected_case_sha256=case_sha256,
            expected_deadline_s=deadline_s,
        )
        if (explore_manifest["prerequisite_manifest_sha256"].get("smoke_manifest")
                != prerequisite_sha256["smoke_manifest"]):
            raise ValueError("exploration manifest belongs to a different smoke run")
        if not explore_manifest["summary"]["predictor_training_support"]["passed"]:
            raise ValueError("exploration did not pass predictor sample-support gate")
        prerequisite_sha256["explore_manifest"] = hashlib.sha256(
            Path(explore_manifest_path).read_bytes()
        ).hexdigest()
    runs = []
    for seed in seed_tuple:
        run = run_diagnostic(seed, case, deadline_s)
        if (run["seed"] != seed or run["parity"]["exact"] is not True
                or run["strict_replay_exact"] is not True):
            raise AssertionError(f"incomplete parity or strict replay at seed {seed}")
        if _source_hashes() != source_sha256:
            raise RuntimeError("diagnostic source changed during the cohort")
        runs.append(run)
    counts = Counter()
    failures = Counter()
    for run in runs:
        counts.update({
            key: value for key, value in run["summary"].items()
            if isinstance(value, int)
        })
        failures.update(run["summary"]["final_hop_failure_causes"])
    counts["source_final_failed_flows"] = len({
        (run["seed"], epoch["flow_id"])
        for run in runs for epoch in run["epochs"]
        if epoch.get("ack_attempt", {}).get("source_final_first_failure")
        and any(flow["flow_id"] == epoch["flow_id"]
                and flow["delivery_by_deadline"] and not flow["ack_by_deadline"]
                for flow in run["flows"])
    })
    denom = counts["source_final_failed_flows"]
    numerator = counts["C_deadline_feasible_flows"]
    summary: dict[str, Any] = dict(sorted(counts.items()))
    summary["final_hop_failure_causes"] = dict(sorted(failures.items()))

    def sum_nested(values: Sequence[dict[str, Any]]) -> dict[str, Any]:
        keys = set(values[0])
        if any(set(value) != keys for value in values):
            raise AssertionError("per-seed diagnostic strata differ")
        return {
            key: (sum_nested([value[key] for value in values])
                  if isinstance(values[0][key], dict)
                  else sum(value[key] for value in values))
            for key in sorted(keys)
        }

    for key in ("predictor_by_q_bin", "predictor_by_path_type",
                "screen_by_original_path_type", "screen_by_epoch_type"):
        summary[key] = sum_nested([run["summary"][key] for run in runs])
    summary["path_screen_fraction_of_source_final_failures"] = (
        numerator / denom if denom else None
    )
    summary["alternate_path_gate_passed"] = (
        numerator >= 8 and denom > 0 and numerator / denom >= 0.20
        if mode == "explore" else None
    )
    predictor_rows = [item for run in runs for item in run["predictor_rows"]]
    summary["predictor_training_support"] = _sample_support(predictor_rows)
    model = None
    validation = None
    if mode == "explore" and predictor_rows:
        model = fit_q_predictor(predictor_rows)
    if mode == "validation":
        model = explore_manifest["predictor_model"]
        validation = evaluate_q_predictor(model, predictor_rows) if predictor_rows else {
            "samples": 0, "sample_gate_passed": False,
            "prediction_gate_passed": False,
        }
    summary["predictor_validation"] = validation
    return {
        "analysis_type": "passive fixed-delay first-edge and actual ACK observation",
        "counterfactual_estimates": None,
        "mode": mode, "protocol": PROTOCOL,
        "case": asdict(case), "case_sha256": case_sha256,
        "seeds": list(seed_tuple), "application_deadline_s": deadline_s,
        "drain_until_s": case.duration_s + deadline_s,
        "source_sha256": source_sha256,
        "prerequisite_manifest_sha256": prerequisite_sha256,
        "summary": summary,
        "predictor_model": model,
        "runs": runs,
    }


def _artifact_paths(prefix: Path) -> dict[str, Path]:
    paths = {
        key: prefix.with_name(prefix.name + (
            ".summary.json" if key == "summary" else f".{key}.jsonl"
        )) for key in ARTIFACT_KEYS
    }
    paths["manifest"] = prefix.with_name(prefix.name + ".manifest.json")
    paths["manifest_sha256"] = prefix.with_name(prefix.name + ".manifest.sha256")
    return paths


def write_report(report: dict[str, Any], output_prefix: Path) -> dict[str, Path]:
    """Write lossless diagnostics and a sidecar-hashed manifest without overwrite."""

    prefix = Path(output_prefix)
    paths = _artifact_paths(prefix)
    if prefix.exists() or any(path.exists() for path in paths.values()):
        raise FileExistsError(f"diagnostic output prefix already exists: {prefix}")
    if not all(run["parity"]["exact"] and run["strict_replay_exact"]
               for run in report["runs"]):
        raise AssertionError("cannot save an unverified diagnostic")

    def json_line(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"

    metadata = {key: value for key, value in report.items() if key != "runs"}
    data = {
        "summary": (json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode("utf-8")
    }
    data["runs"] = "".join(json_line({
        key: value for key, value in run.items()
        if key not in {"paths", "epochs", "predictor_rows", "flows", "actions",
                       "transmissions"}
    }) for run in report["runs"]).encode("utf-8")
    for key in ("paths", "epochs", "predictor_rows", "flows", "actions",
                "transmissions"):
        data[key] = "".join(json_line({"seed": run["seed"], "item": item})
                             for run in report["runs"] for item in run[key]).encode("utf-8")
    manifest = {
        "mode": report["mode"], "protocol": report["protocol"],
        "seeds": report["seeds"],
        "case_sha256": report["case_sha256"],
        "application_deadline_s": report["application_deadline_s"],
        "drain_until_s": report["drain_until_s"],
        "source_sha256": report["source_sha256"],
        "prerequisite_manifest_sha256": report["prerequisite_manifest_sha256"],
        "summary": report["summary"],
        "predictor_model": report["predictor_model"],
        "artifacts": {
            key: {"file": paths[key].name,
                  "sha256": hashlib.sha256(data[key]).hexdigest()}
            for key in ARTIFACT_KEYS
        },
    }
    manifest_data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    sidecar_data = (
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    ).encode("ascii")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for key in ARTIFACT_KEYS:
        with paths[key].open("xb") as output:
            output.write(data[key])
    with paths["manifest"].open("xb") as output:
        output.write(manifest_data)
    with paths["manifest_sha256"].open("xb") as output:
        output.write(sidecar_data)
    return paths


def validate_manifest(
    manifest_path: Path, *, expected_mode: str,
    expected_source_sha256: dict[str, str], expected_case_sha256: str,
    expected_deadline_s: float | None = None,
) -> dict[str, Any]:
    """Verify every prior artifact and its manifest before opening a split."""

    path = Path(manifest_path)
    manifest_data = path.read_bytes()
    sidecar = path.with_suffix(".sha256")
    if sidecar.read_text(encoding="ascii") != (
        hashlib.sha256(manifest_data).hexdigest() + "  " + path.name + "\n"
    ):
        raise ValueError("manifest SHA-256 sidecar differs")
    manifest = json.loads(manifest_data)
    if (manifest["mode"] != expected_mode
            or manifest["source_sha256"] != expected_source_sha256
            or _source_hashes() != expected_source_sha256
            or manifest["case_sha256"] != expected_case_sha256
            or (expected_deadline_s is not None
                and manifest["application_deadline_s"] != expected_deadline_s)
            or set(manifest["artifacts"]) != set(ARTIFACT_KEYS)):
        raise ValueError("manifest frozen source, case or mode differs")
    if expected_mode != "synthetic" and tuple(manifest["seeds"]) != seeds_for_mode(expected_mode):
        raise ValueError("manifest seeds differ from frozen cohort")
    artifact_data = {}
    for key in ARTIFACT_KEYS:
        descriptor = manifest["artifacts"][key]
        artifact_path = path.parent / descriptor["file"]
        if artifact_path.parent != path.parent:
            raise ValueError(f"artifact path escapes manifest directory: {key}")
        artifact_data[key] = artifact_path.read_bytes()
        if hashlib.sha256(artifact_data[key]).hexdigest() != descriptor["sha256"]:
            raise ValueError(f"artifact checksum differs: {key}")
    metadata = json.loads(artifact_data["summary"])
    if (metadata["mode"] != manifest["mode"]
            or metadata["seeds"] != manifest["seeds"]
            or metadata["summary"] != manifest["summary"]
            or metadata["predictor_model"] != manifest["predictor_model"]
            or metadata["source_sha256"] != manifest["source_sha256"]
            or metadata["case_sha256"] != manifest["case_sha256"]):
        raise ValueError("manifest and summary artifact disagree")
    runs = [json.loads(line) for line in artifact_data["runs"].splitlines()]
    if ([run["seed"] for run in runs] != manifest["seeds"]
            or len(set(manifest["seeds"])) != len(runs)):
        raise ValueError("run artifact seeds differ from manifest")
    grouped: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for key in ARTIFACT_KEYS:
        if key in {"summary", "runs"}:
            continue
        grouped[key] = defaultdict(list)
        for line in artifact_data[key].splitlines():
            item = json.loads(line)
            if item["seed"] not in manifest["seeds"]:
                raise ValueError(f"{key} contains an unknown seed")
            if (isinstance(item["item"], dict)
                    and "seed" in item["item"]
                    and item["item"]["seed"] != item["seed"]):
                raise ValueError(f"{key} row seed differs from its run")
            grouped[key][item["seed"]].append(item["item"])
    predictor_rows = [item for seed in manifest["seeds"]
                      for item in grouped["predictor_rows"][seed]]
    if (_sample_support(predictor_rows)
            != manifest["summary"]["predictor_training_support"]):
        raise ValueError("predictor support differs from saved rows")
    if expected_mode in {"synthetic", "smoke", "explore"}:
        expected_model = (
            fit_q_predictor(predictor_rows)
            if expected_mode == "explore" and predictor_rows else None
        )
        if manifest["predictor_model"] != expected_model:
            raise ValueError("predictor model differs from training rows or split")
    for run in runs:
        seed = run["seed"]
        parity = run["parity"]
        if (parity.get("exact") is not True
                or run.get("strict_replay_exact") is not True
                or run["protocol"] != manifest["protocol"]
                or run["row"]["scheduled_trace_sha256"]
                != parity["scheduled_trace_sha256"]
                or _sha256_json(run["row"]) != parity["full_row_sha256"]
                or _sha256_json(grouped["flows"][seed]) != parity["flow_trace_sha256"]
                or _sha256_json(grouped["actions"][seed]) != parity["action_trace_sha256"]
                or _sha256_json(grouped["transmissions"][seed])
                != parity["full_tx_trace_sha256"]
                or len(grouped["flows"][seed]) != run["row"]["scheduled_unicast_flows"]
                or len(grouped["paths"][seed]) != run["summary"]["valid_path_decodes"]
                or len(grouped["predictor_rows"][seed])
                != run["summary"]["final_hop_predictor_samples"]
                or run["summary"]["scheduled_flows"]
                != run["row"]["scheduled_unicast_flows"]):
            raise ValueError(f"run {seed} parity or artifact counts differ")
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("smoke", "explore", "validation"))
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--smoke-manifest", type=Path)
    parser.add_argument("--explore-manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    prefix = args.output_prefix
    if prefix.exists() or any(path.exists() for path in _artifact_paths(prefix).values()):
        raise FileExistsError(f"diagnostic output prefix already exists: {prefix}")
    report = run_report(
        seeds_for_mode(args.mode), mode=args.mode,
        smoke_manifest_path=args.smoke_manifest,
        explore_manifest_path=args.explore_manifest,
    )
    if _source_hashes() != report["source_sha256"]:
        raise RuntimeError("diagnostic source changed before artifact writing")
    paths = write_report(report, prefix)
    print(json.dumps({"artifacts": {key: str(path) for key, path in paths.items()},
                      "summary": report["summary"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
