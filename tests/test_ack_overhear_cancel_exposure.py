"""Tests for passive terminal-ACK FLOOD-cancellation exposure."""

import random
from dataclasses import replace

import pytest

from lora_mesh_sim import build_protocol, generate_nodes
from lora_mesh_sim import Packet, PendingSend, Transmission
from tools.diagnose_ack_overhear_cancel_exposure import (
    AckOverhearSimulator, build_report, cancelable_flood_forward, run_diagnostic,
)
from tools.run_fair_multihop_probe import make_args, make_radio
from tools.run_sr_experiment import SR_CASES, SrCase


def test_off_path_destination_ack_can_nominate_uncommitted_flood_relay():
    flood = Packet(
        kind="FLOOD", flow_id=7, origin=1, final_dst=9, ttl=3,
        created_at=1.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 4), path_index=1, repair_index=2,
    )
    ack = Packet(
        kind="ACK", flow_id=7, origin=9, final_dst=1, ttl=6,
        created_at=2.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 5, 9), path_index=1, app_payload=False, repair_index=2,
    )
    handle = PendingSend()
    on_air_ack = Transmission(1, 9, ack, 2.0, 2.2)

    assert cancelable_flood_forward(
        on_air_ack, receiver=4, flood=flood, pending=handle,
        protocol_pending=handle, max_hops=6,
    )


def test_observer_nominates_only_live_local_flood_handles():
    case = SrCase(key="ack-overhear-unit", nodes=10)
    config = make_args(case)
    sim = AckOverhearSimulator(
        generate_nodes(10, case.area_m, random.Random(4)), make_radio(config),
        build_protocol("meshecho-dhr-flood", config), seed=4,
        max_hops=case.max_hops, independent_random_streams=True,
    )
    flood = Packet(
        kind="FLOOD", flow_id=7, origin=1, final_dst=9, ttl=3,
        created_at=1.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 4), path_index=1, repair_index=2,
    )
    ack = Packet(
        kind="ACK", flow_id=7, origin=9, final_dst=1, ttl=6,
        created_at=2.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 5, 9), path_index=1, app_payload=False, repair_index=2,
    )
    handle = sim.transmit_later(4, flood, delay_s=10.0)
    sim.protocol.pending_fallback[(4, flood.flood_key)] = handle

    sim.now = 2.2
    sim.observe_ack_decode(Transmission(1, 9, ack, 2.0, 2.2), 4)
    assert len(sim.opportunities) == 1
    assert sim.opportunities[0]["relay"] == 4

    sim.now = 2.3
    sim.observe_ack_decode(Transmission(2, 9, ack, 2.1, 2.3), 4)
    assert len(sim.opportunities) == 1
    assert sim.strict_candidate_ack_decode_events == 2
    assert sim.strict_candidate_pairs == 2


def test_committed_future_start_is_only_an_optional_upper_bound():
    case = SrCase(key="ack-overhear-unit", nodes=10)
    config = make_args(case)
    sim = AckOverhearSimulator(
        generate_nodes(10, case.area_m, random.Random(4)), make_radio(config),
        build_protocol("meshecho-dhr-flood", config), seed=4,
        max_hops=case.max_hops, independent_random_streams=True,
    )
    flood = Packet(
        kind="FLOOD", flow_id=7, origin=1, final_dst=9, ttl=3,
        created_at=1.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 4), path_index=1, repair_index=2,
    )
    ack = Packet(
        kind="ACK", flow_id=7, origin=9, final_dst=1, ttl=6,
        created_at=2.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 5, 9), path_index=1, app_payload=False, repair_index=2,
    )
    handle = sim.transmit_later(4, flood, delay_s=0.0)
    sim.protocol.pending_fallback[(4, flood.flood_key)] = handle
    sim.nodes[4].tx_available_at = 9.0
    sim.now = 1.0
    sim.begin_transmission(4, flood, handle)
    assert handle.committed
    assert sim.tx_history[-1].start == 9.0

    sim.now = 2.2
    sim.observe_ack_decode(Transmission(1, 9, ack, 2.0, 2.2), 4)
    assert sim.opportunities == []
    assert len(sim.committed_future_opportunities) == 1
    assert sim.committed_future_opportunities[0]["baseline_relay_tx_id"] == sim.tx_history[-1].tx_id


def test_exploratory_replay_preserves_baseline_flow_action_and_tx_traces():
    report = run_diagnostic(22001, case=SR_CASES["recurring_fading"])

    assert report["parity"]["per_flow_exact_timestamps"]
    assert report["parity"]["action_events_exact"]
    assert report["parity"]["full_tx_trace_exact"]
    assert report["parity"]["plain_full_tx_trace_sha256"] == report["parity"]["observed_full_tx_trace_sha256"]
    assert report["summary"]["strict_potential_avoidable_airtime_s"] <= report["summary"]["post_delivery_flood_relay_airtime_s"]
    epochs = report["summary"]["by_flood_epoch"]
    assert sum(epoch["strict_unique_pending_handles"] for epoch in epochs.values()) == report["summary"]["strict_cancelable_pending_relays"]
    assert sum(epoch["strict_potential_avoidable_airtime_s"] for epoch in epochs.values()) == report["summary"]["strict_potential_avoidable_airtime_s"]


def test_pending_flood_path_and_ack_epoch_must_be_locally_consistent():
    flood = Packet(
        kind="FLOOD", flow_id=7, origin=1, final_dst=9, ttl=3,
        created_at=1.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 4), path_index=1, repair_index=2,
    )
    ack = Packet(
        kind="ACK", flow_id=7, origin=9, final_dst=1, ttl=6,
        created_at=2.0, protocol="meshecho-dhr-flood", request_id=7,
        path=(1, 5, 9), path_index=1, app_payload=False, repair_index=2,
    )
    handle = PendingSend()
    on_air_ack = Transmission(1, 9, ack, 2.0, 2.2)

    assert not cancelable_flood_forward(
        on_air_ack, 4, replace(flood, path=(4, 1)), handle, handle, 6,
    )
    assert not cancelable_flood_forward(
        on_air_ack, 4, replace(flood, path_index=0), handle, handle, 6,
    )
    assert not cancelable_flood_forward(
        on_air_ack, 4, replace(flood, repair_index=None), handle, handle, 6,
    )
    assert not cancelable_flood_forward(
        on_air_ack, 4, flood, handle, PendingSend(), 6,
    )
    handle.committed = True
    assert not cancelable_flood_forward(on_air_ack, 4, flood, handle, handle, 6)


def test_report_refuses_duplicate_or_reserved_seeds_before_replay():
    with pytest.raises(ValueError, match="unique"):
        build_report(seeds=(22001, 22001))
    with pytest.raises(ValueError, match="reserved"):
        build_report(seeds=(17001,))
