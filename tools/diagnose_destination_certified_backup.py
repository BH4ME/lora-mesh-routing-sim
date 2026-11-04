#!/usr/bin/env python3
"""Passive physical exposure for a destination-certified backup hypothesis.

These observations are not counterfactual forwarding outcomes. No packet,
protocol state, event, or receive attempt is added to the stock simulation.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from lora_mesh_sim import Packet, RxInfo, Transmission
from tools import run_sr_experiment as sr
from tools.diagnose_delayed_ack_rx import capture_run, require_stock_parity


RecordingSimulator = sr.RecordingSimulator


@dataclass(frozen=True)
class FloodDecode:
    flow_id: int
    repair_index: int | None
    decoded_at_s: float
    tx_id: int
    path: tuple[int, ...]


@dataclass(frozen=True)
class AckDecode:
    flow_id: int
    receiver: int
    decoded_at_s: float
    path: tuple[int, ...]


class PassiveBackupSimulator(RecordingSimulator):
    """Save results from the normal single physical receive attempt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.flood_decodes: list[FloodDecode] = []
        self.initial_r_decodes: dict[int, set[int]] = {}
        self.destination_ack_decodes: list[AckDecode] = []

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        rx = super().try_receive(tx, receiver)
        if rx is None:
            return None
        packet = tx.packet
        flow = self.metrics.flows.get(packet.flow_id)
        if flow is None:
            return rx
        if (packet.kind == "FLOOD" and receiver == flow.dst
                and packet.protocol == self.protocol.name
                and packet.origin == flow.src and packet.final_dst == flow.dst
                and packet.request_id == packet.flow_id
                and packet.repair_index in {None, 2}
                and packet.path and packet.path[0] == flow.src
                and packet.path[-1] == tx.sender
                and receiver not in packet.path
                and len(set(packet.path)) == len(packet.path)
                and 2 <= len(packet.path) + 1 <= self.max_hops + 1):
            self.flood_decodes.append(FloodDecode(
                packet.flow_id, packet.repair_index, tx.end, tx.tx_id,
                packet.path + (receiver,),
            ))
        elif (packet.kind == "DATA" and packet.repair_index is None
              and tx.sender == flow.src and packet.origin == flow.src
              and packet.protocol == self.protocol.name
              and packet.request_id == packet.flow_id
              and packet.final_dst == flow.dst
              and packet.path == (flow.src, flow.dst)
              and self.protocol.flow_actions.get(packet.flow_id) == "R"
              and self.protocol.flow_data_actions.get(packet.flow_id) == "R"):
            self.initial_r_decodes.setdefault(tx.tx_id, set()).add(receiver)
        elif (packet.kind == "ACK" and tx.sender == flow.dst
              and packet.protocol == self.protocol.name
              and packet.origin == flow.dst and packet.final_dst == flow.src
              and packet.request_id == packet.flow_id
              and packet.repair_index is None
              and packet.path == (flow.src, flow.dst)
              and packet.path_index == 0
              and self.protocol.flow_data_actions.get(packet.flow_id) == "R"):
            self.destination_ack_decodes.append(AckDecode(
                packet.flow_id, receiver, tx.end, packet.path,
            ))
        return rx


def _reconstruct_flood_windows(
    sim: PassiveBackupSimulator,
) -> dict[tuple[int, int | None], list[FloodDecode]]:
    windows: dict[tuple[int, int | None], list[FloodDecode]] = {}
    active: dict[tuple[int, int | None], list[FloodDecode]] = {}
    overflowed: set[tuple[int, int | None]] = set()
    for decode in sorted(sim.flood_decodes, key=lambda item: (item.decoded_at_s, item.tx_id)):
        active = {
            key: records for key, records in active.items()
            if decode.decoded_at_s <= records[0].decoded_at_s + 2.0
        }
        key = (decode.flow_id, decode.repair_index)
        if key in overflowed:
            continue
        if key not in windows:
            destination_windows = sum(
                records[0].path[-1] == decode.path[-1]
                for records in active.values()
            )
            if destination_windows >= 8:
                overflowed.add(key)
                continue
            windows[key] = [decode]
            active[key] = windows[key]
            continue
        current = active.get(key)
        if current is None:
            continue
        if decode.path not in (item.path for item in current) and len(current) < 4:
            current.append(decode)
    return windows


def _selected_two_hop_alternate(
    sim: PassiveBackupSimulator, paths: list[FloodDecode],
) -> FloodDecode | None:
    primary = paths[0].path
    alternatives = [item for item in paths[1:]
                    if len(item.path) == 3
                    and item.path[1] != primary[1]
                    and sim.nodes[item.path[1]].can_relay]
    if not alternatives:
        return None
    return min(alternatives, key=lambda item: (
        len(item.path), item.decoded_at_s, item.path[1],
    ))


def analyze_candidate_epochs(sim: PassiveBackupSimulator) -> list[dict[str, Any]]:
    """Account for every physically eligible direct-primary F ACK epoch."""

    commits = [event for event in sim.protocol.action_events
               if event["event"] == "commit"]
    epochs = []
    for (flow_id, marker), paths in _reconstruct_flood_windows(sim).items():
        primary = paths[0].path
        if len(primary) != 2:
            continue
        chosen = _selected_two_hop_alternate(sim, paths)
        if chosen is None:
            continue
        src, dst = primary
        ack_txs = [tx for tx in sim.tx_history
                   if tx.packet.kind == "ACK"
                   and tx.packet.flow_id == flow_id
                   and tx.packet.repair_index == marker
                   and tx.packet.path == primary
                   and tx.packet.origin == dst
                   and tx.packet.final_dst == src
                   and tx.start <= sim.now]
        assessable = bool(ack_txs)
        epochs.append({
            "flow_id": flow_id,
            "repair_index": marker,
            "src": src,
            "dst": dst,
            "first_decode_at_s": paths[0].decoded_at_s,
            "window_close_at_s": paths[0].decoded_at_s + 2.0,
            "alternate_decode_at_s": chosen.decoded_at_s,
            "primary_path": primary,
            "backup_path": chosen.path,
            "source_commit_accepted": any(
                event["flow_id"] == flow_id
                and event["action"] == ("F-recovery" if marker == 2 else "F")
                and tuple(event["path"]) == primary
                for event in commits
            ),
            "f_ack_cost_assessable": assessable,
            "f_ack_actual_tx_hops": len(ack_txs),
            "f_ack_relay_field_min_wire_bytes": (
                2 * len(ack_txs) if assessable else None
            ),
            "f_ack_relay_field_min_extra_toa_s": (
                sum(
                    sim.radio.toa_s_for_bytes(
                        tx.packet.wire_size_bytes(sim.radio.payload_bytes) + 2
                    ) - sim.radio.packet_toa_s(tx.packet)
                    for tx in ack_txs
                ) if assessable else None
            ),
        })
    return epochs


def analyze_backup_exposure(sim: PassiveBackupSimulator) -> list[dict[str, Any]]:
    """Join physical receptions to the latest accepted source F commit."""

    windows = _reconstruct_flood_windows(sim)

    commits = sorted(
        (event for event in sim.protocol.action_events if event["event"] == "commit"),
        key=lambda event: (event["time"], event["flow_id"]),
    )
    decisions = {
        event["flow_id"]: event for event in sim.protocol.action_events
        if event["event"] == "decision"
    }
    rows: list[dict[str, Any]] = []
    seen_initial_r_flows: set[int] = set()
    for tx in sim.tx_history:
        packet = tx.packet
        decision = decisions.get(packet.flow_id)
        if (packet.kind != "DATA" or packet.repair_index is not None
                or tx.sender != packet.origin or len(packet.path) != 2
                or packet.protocol != sim.protocol.name
                or packet.request_id != packet.flow_id
                or decision is None or decision["action"] != "R"
                or sim.protocol.flow_data_actions.get(packet.flow_id) != "R"):
            continue
        if packet.flow_id in seen_initial_r_flows:
            continue
        seen_initial_r_flows.add(packet.flow_id)
        commit = next((event for event in reversed(commits)
                       if event["src"] == packet.origin
                       and event["dst"] == packet.final_dst
                       and event["time"] <= decision["time"]), None)
        if commit is None or commit["action"] not in {"F", "F-recovery"}:
            continue
        if tuple(commit["path"]) != packet.path:
            continue
        marker = 2 if commit["action"] == "F-recovery" else None
        paths = windows.get((commit["flow_id"], marker), [])
        if not paths or paths[0].path != packet.path:
            continue
        chosen = _selected_two_hop_alternate(sim, paths)
        if chosen is None:
            continue
        relay = chosen.path[1]
        ack_times = [item.decoded_at_s for item in sim.destination_ack_decodes
                     if item.flow_id == packet.flow_id and item.receiver == relay
                     and item.path == packet.path
                     and item.decoded_at_s >= tx.end]
        censored = tx.end > sim.now
        def ack_heard_by(wait_s: float) -> bool | None:
            if censored:
                return None
            if any(at <= tx.end + wait_s for at in ack_times):
                return True
            return False if sim.now >= tx.end + wait_s else None

        flow = sim.metrics.flows[packet.flow_id]
        deadline_at = flow.created_at + sim.protocol.app_deadline_s
        def by_deadline(when: float | None) -> bool | None:
            if when is not None and when <= deadline_at:
                return True
            return False if sim.now >= deadline_at else None

        stock_acked = by_deadline(flow.acked_at)
        stock_delivered = by_deadline(flow.delivered_at)
        recovery_txs = [item for item in sim.tx_history
                        if item.packet.flow_id == packet.flow_id
                        and item.packet.kind == "FLOOD"
                        and item.packet.repair_index == 2
                        and item.start <= sim.now]
        recovery_airtime = sum(item.end - item.start for item in recovery_txs)
        source_recovery_started = any(
            item.sender == flow.src and item.start <= deadline_at
            for item in recovery_txs
        )
        relay_decoded = (
            None if censored else relay in sim.initial_r_decodes.get(tx.tx_id, set())
        )
        destination_decoded = (
            None if censored else packet.final_dst in sim.initial_r_decodes.get(tx.tx_id, set())
        )
        ack_by_half = ack_heard_by(0.5)
        ack_by_two = ack_heard_by(2.0)
        age_s = decision["time"] - commit["time"]
        def redundant_start(ack_heard: bool | None) -> bool | None:
            if relay_decoded is False or destination_decoded is False:
                return False
            if ack_heard is None or relay_decoded is None or destination_decoded is None:
                return None
            return not ack_heard

        source_r_extra_toa_s = (
            sim.radio.toa_s_for_bytes(
                packet.wire_size_bytes(sim.radio.payload_bytes) + 6
            ) - sim.radio.packet_toa_s(packet)
        )
        relay_data = Packet(
            kind="DATA", flow_id=packet.flow_id, origin=packet.origin,
            final_dst=packet.final_dst, ttl=packet.ttl,
            created_at=packet.created_at, protocol=packet.protocol,
            request_id=packet.request_id, path=chosen.path, path_index=1,
            repair_index=4,
        )
        reverse_ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=packet.final_dst,
            final_dst=packet.origin, ttl=packet.ttl,
            created_at=packet.created_at, protocol=packet.protocol,
            request_id=packet.request_id, path=chosen.path, path_index=1,
            app_payload=False, repair_index=4,
        )
        relay_data_toa_s = sim.radio.packet_toa_s(relay_data)
        reverse_ack_toa_s = sim.radio.packet_toa_s(reverse_ack)
        f_ack_txs = [item for item in sim.tx_history
                     if item.packet.kind == "ACK"
                     and item.packet.flow_id == commit["flow_id"]
                     and item.packet.repair_index == marker
                     and item.packet.path == packet.path
                     and item.packet.origin == packet.final_dst
                     and item.packet.final_dst == packet.origin
                     and item.start <= sim.now]
        f_ack_extra_toa_s = sum(
            sim.radio.toa_s_for_bytes(
                item.packet.wire_size_bytes(sim.radio.payload_bytes) + 2
            ) - sim.radio.packet_toa_s(item.packet)
            for item in f_ack_txs
        )
        nominal_proxies: dict[str, float] = {}
        for wait_s, suffix in ((0.5, "0_5_s"), (2.0, "2_s")):
            relay_start = tx.end + source_r_extra_toa_s + wait_s
            relay_end = relay_start + relay_data_toa_s
            def link_prr(sender: int, receiver: int, when: float) -> float:
                power = sim.rx_power_dbm(sender, receiver, when=when)
                return sim.prr_from_snr(sim.snr_from_power(power))

            data_prr = link_prr(relay, packet.final_dst, relay_start)
            first_ack_prr = link_prr(packet.final_dst, relay, relay_end)
            second_ack_prr = link_prr(
                relay, packet.origin, relay_end + reverse_ack_toa_s,
            )
            nominal_ack_end = relay_end + 2.0 * reverse_ack_toa_s
            f_guard_at = tx.start + sim.protocol.ack_guard_s
            heard = ack_by_half if wait_s == 0.5 else ack_by_two
            if relay_decoded is False:
                would_start: bool | None = False
            elif relay_decoded is None or heard is None:
                would_start = None
            else:
                would_start = not heard
            redundant = redundant_start(heard)
            nominal_proxies.update({
                f"nominal_source_ack_slack_{suffix}": (
                    deadline_at - nominal_ack_end
                ),
                f"nominal_f_guard_slack_{suffix}": f_guard_at - nominal_ack_end,
                f"nominal_before_f_guard_{suffix}": nominal_ack_end < f_guard_at,
                f"nominal_cost_substitution_eligible_{suffix}": bool(
                    age_s <= 120.0 and stock_acked is True
                    and source_recovery_started
                    and relay_decoded is True
                    and destination_decoded is False
                    and would_start is True
                    and data_prr >= 0.5
                    and nominal_ack_end < min(f_guard_at, deadline_at)
                ),
                f"oracle_collision_free_relay_to_dst_prr_{suffix}": data_prr,
                f"oracle_collision_free_dst_to_relay_ack_prr_{suffix}": first_ack_prr,
                f"oracle_collision_free_relay_to_src_ack_prr_{suffix}": second_ack_prr,
                f"oracle_collision_free_round_trip_prr_{suffix}": (
                    data_prr * first_ack_prr * second_ack_prr
                ),
                f"nominal_relay_would_start_{suffix}": would_start,
                f"nominal_relay_data_airtime_{suffix}": (
                    None if would_start is None else
                    relay_data_toa_s if would_start else 0.0
                ),
                f"nominal_success_reverse_ack_airtime_{suffix}": (
                    None if would_start is None else
                    2.0 * reverse_ack_toa_s if would_start else 0.0
                ),
                f"nominal_redundant_relay_data_airtime_{suffix}": (
                    None if redundant is None else
                    relay_data_toa_s if redundant else 0.0
                ),
            })

        row = {
            "flow_id": packet.flow_id,
            "src": packet.origin,
            "dst": packet.final_dst,
            "r_tx_id": tx.tx_id,
            "r_start_at_s": tx.start,
            "r_end_at_s": tx.end,
            "commit_flow_id": commit["flow_id"],
            "commit_at_s": commit["time"],
            "backup_age_at_r_enqueue_s": age_s,
            "backup_age_at_r_enqueue_le_60_s": age_s <= 60.0,
            "backup_age_at_r_enqueue_le_120_s": age_s <= 120.0,
            "primary_path": packet.path,
            "backup_path": chosen.path,
            "r_receive_censored": censored,
            "relay_decoded_current_r": relay_decoded,
            "destination_decoded_current_r": destination_decoded,
            "relay_decoded_destination_ack_by_0_5_s": ack_by_half,
            "relay_decoded_destination_ack_by_2_s": ack_by_two,
            "nominal_redundant_relay_start_0_5_s": redundant_start(ack_by_half),
            "nominal_redundant_relay_start_2_s": redundant_start(ack_by_two),
            "stock_source_ack_by_deadline": stock_acked,
            "stock_destination_delivered_by_deadline": stock_delivered,
            "stock_f_recovery_tx_airtime_s": recovery_airtime,
            "f_ack_relay_field_min_wire_bytes": 2 * len(f_ack_txs),
            "f_ack_relay_field_min_extra_toa_s": f_ack_extra_toa_s,
            "r_nomination_min_wire_bytes": 6,
            "r_nomination_min_extra_toa_s": source_r_extra_toa_s,
            "relay_data_min_toa_s": relay_data_toa_s,
            "relay_data_min_wire_bytes": relay_data.wire_size_bytes(
                sim.radio.payload_bytes
            ),
            "relay_success_reverse_ack_min_toa_s": 2.0 * reverse_ack_toa_s,
            "relay_success_reverse_ack_min_wire_bytes": (
                2 * reverse_ack.wire_size_bytes(sim.radio.payload_bytes)
            ),
            "stock_source_ack_headroom": (
                None if stock_acked is None else not stock_acked
            ),
            "stock_f_rescue_cost_potential": (
                None if stock_acked is None else
                stock_acked and source_recovery_started
                and relay_decoded is True and destination_decoded is False
            ),
            **nominal_proxies,
        }
        rows.append(row)
    return rows


def summarize_backup_cohort(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate passive opportunity and charged nominal cost, never effect."""

    if not runs:
        raise ValueError("cannot summarize an empty passive cohort")
    seeds = [run["seed"] for run in runs]
    if len(set(seeds)) != len(seeds):
        raise ValueError("passive cohort has a duplicate seed")
    rows = [row for run in runs for row in run["rows"]]
    epochs = [epoch for run in runs for epoch in run["candidate_epochs"]]
    scheduled = sum(len(run["flows"]) for run in runs)
    if scheduled <= 0:
        raise ValueError("passive cohort has no scheduled unicast flows")
    unknown_ack_epochs = sum(not epoch["f_ack_cost_assessable"] for epoch in epochs)
    known_f_ack_bytes = sum(
        epoch["f_ack_relay_field_min_wire_bytes"] for epoch in epochs
        if epoch["f_ack_cost_assessable"]
    )
    known_f_ack_toa = sum(
        epoch["f_ack_relay_field_min_extra_toa_s"] for epoch in epochs
        if epoch["f_ack_cost_assessable"]
    )
    by_wait = {}
    for suffix in ("2_s", "0_5_s"):
        eligible_age = [row for row in rows
                        if row["backup_age_at_r_enqueue_le_120_s"]]
        failed_primary = [row for row in eligible_age
                          if row["relay_decoded_current_r"] is True
                          and row["destination_decoded_current_r"] is False]
        proxy_feasible = [row for row in failed_primary
                          if row[f"oracle_collision_free_relay_to_dst_prr_{suffix}"] >= 0.5
                          and row[f"nominal_source_ack_slack_{suffix}"] >= 0.0]
        headroom = [row for row in proxy_feasible
                    if row["stock_source_ack_by_deadline"] is False]
        cost_candidates = [row for row in eligible_age
                           if row[f"nominal_cost_substitution_eligible_{suffix}"]]
        censored_starts = sum(
            row[f"nominal_relay_would_start_{suffix}"] is None
            for row in eligible_age
        )
        assessable = unknown_ack_epochs == 0 and censored_starts == 0
        r_field_bytes = sum(row["r_nomination_min_wire_bytes"]
                            for row in eligible_age)
        r_field_toa = sum(row["r_nomination_min_extra_toa_s"]
                          for row in eligible_age)
        relay_data_toa = sum(
            row[f"nominal_relay_data_airtime_{suffix}"] or 0.0
            for row in eligible_age
        )
        success_ack_toa = sum(
            row[f"nominal_success_reverse_ack_airtime_{suffix}"] or 0.0
            for row in eligible_age
        )
        credited_ack_toa = sum(
            row["relay_success_reverse_ack_min_toa_s"]
            for row in cost_candidates
        )
        stock_f_airtime = sum(row["stock_f_recovery_tx_airtime_s"]
                              for row in cost_candidates)
        optimistic_added_toa = (
            known_f_ack_toa + r_field_toa + relay_data_toa + credited_ack_toa
            if assessable else None
        )
        all_start_success_added_toa = (
            known_f_ack_toa + r_field_toa + relay_data_toa + success_ack_toa
            if assessable else None
        )
        unknown_source_ack = sum(
            row["stock_source_ack_by_deadline"] is None
            for row in proxy_feasible
        )
        by_wait[suffix] = {
            "failed_primary_relay_decode_le_120_s": len(failed_primary),
            "proxy_prr_ge_0_5_deadline_feasible_count": len(proxy_feasible),
            "source_ack_headroom_proxy_count": len(headroom),
            "source_ack_headroom_ceiling_fraction": (
                len(headroom) / scheduled if unknown_source_ack == 0 else None
            ),
            "source_ack_outcome_unassessable_count": unknown_source_ack,
            "nominal_cost_substitution_eligible_count": len(cost_candidates),
            "stock_f_recovery_airtime_eligible_s": stock_f_airtime,
            "r_nomination_min_wire_bytes": r_field_bytes,
            "r_nomination_min_extra_toa_s": r_field_toa,
            "nominal_relay_starts": sum(
                row[f"nominal_relay_would_start_{suffix}"] is True
                for row in eligible_age
            ),
            "nominal_redundant_relay_starts": sum(
                row[f"nominal_redundant_relay_start_{suffix}"] is True
                for row in eligible_age
            ),
            "nominal_relay_data_airtime_s": relay_data_toa,
            "nominal_credited_reverse_ack_airtime_s": credited_ack_toa,
            "nominal_success_reverse_ack_airtime_s": success_ack_toa,
            "nominal_redundant_relay_data_airtime_s": sum(
                row[f"nominal_redundant_relay_data_airtime_{suffix}"] or 0.0
                for row in eligible_age
            ),
            "nominal_relay_start_unassessable_count": censored_starts,
            "candidate_cost_assessable": assessable,
            "candidate_nominal_optimistic_added_airtime_s": optimistic_added_toa,
            "candidate_nominal_all_start_success_added_airtime_s": (
                all_start_success_added_toa
            ),
            "candidate_nominal_success_added_airtime_s": (
                all_start_success_added_toa
            ),
            "optimistic_cost_substitution_margin_s": (
                stock_f_airtime - optimistic_added_toa
                if optimistic_added_toa is not None else None
            ),
        }
    return {
        "seeds": sorted(seeds),
        "scheduled_unicast_flows": scheduled,
        "candidate_f_epochs": len(epochs),
        "candidate_f_epochs_without_actual_ack_tx": unknown_ack_epochs,
        "f_ack_min_wire_bytes_known": known_f_ack_bytes,
        "f_ack_min_extra_toa_s_known": known_f_ack_toa,
        "nominated_initial_direct_r": len(rows),
        "backup_age_bins": {
            "no_age_limit": len(rows),
            "le_120_s": sum(row["backup_age_at_r_enqueue_le_120_s"] for row in rows),
            "le_60_s": sum(row["backup_age_at_r_enqueue_le_60_s"] for row in rows),
        },
        "by_wait": by_wait,
    }


def run_diagnostic(
    seed: int, case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> dict[str, Any]:
    """Compare one non-reserved passive run with stock, then replay it."""

    if type(seed) is not int or seed >= 35000:
        raise ValueError("research-reserved seeds require a staged authorization")
    stock, _ = capture_run(case, seed, RecordingSimulator, deadline_s)
    observed, sim = capture_run(case, seed, PassiveBackupSimulator, deadline_s)
    parity = require_stock_parity(stock, observed)
    rows = analyze_backup_exposure(sim)
    candidate_epochs = analyze_candidate_epochs(sim)
    replay, replay_sim = capture_run(
        case, seed, PassiveBackupSimulator, deadline_s,
    )
    replay_rows = analyze_backup_exposure(replay_sim)
    replay_epochs = analyze_candidate_epochs(replay_sim)
    if (observed != replay
            or sim.flood_decodes != replay_sim.flood_decodes
            or sim.initial_r_decodes != replay_sim.initial_r_decodes
            or sim.destination_ack_decodes != replay_sim.destination_ack_decodes
            or rows != replay_rows or candidate_epochs != replay_epochs):
        raise AssertionError("passive backup exposure replay differs")
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
    result["summary"] = summarize_backup_cohort([result])
    return result
