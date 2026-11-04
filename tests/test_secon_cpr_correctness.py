"""Deterministic lifecycle regressions, without performance/holdout runs."""

from dataclasses import replace

import pytest

from lora_mesh_sim import MeshEchoCPR, Node, Packet, PendingSend, RadioConfig, RxInfo, Simulator, build_protocol
from meshecho_cpr import CprAction, CprObservation, choose_recovery_action


def fixture_protocol(**options):
    protocol = MeshEchoCPR(**options)
    sim = Simulator(
        [Node(i, float(i), 0.0) for i in range(5)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=23, max_hops=4, independent_random_streams=True,
    )
    return protocol, sim


def rx(sender):
    return RxInfo(sender=sender, rx_power_dbm=-60.0, snr_db=30.0,
                  sinr_db=30.0, collided=False)


def start_flow(protocol, sim, flow_id, *, now=1.0):
    sim.now = now
    protocol.send_app(0, 4, flow_id)
    handle = protocol.cpr_initial_pending[flow_id]
    placeholder = protocol._cpr_placeholder(protocol.cpr_flows[flow_id], "CPR_REQUEST")
    sim.begin_transmission(0, placeholder, handle)
    return protocol.cpr_flows[flow_id]


def ack(protocol, flow_id, *, path=(0, 4), marker=None):
    return Packet(kind="ACK", flow_id=flow_id, request_id=flow_id,
                  origin=4, final_dst=0, ttl=4, created_at=1.0,
                  protocol=protocol.name, path=path, path_index=0,
                  repair_index=marker, app_payload=False)


@pytest.mark.parametrize("routed", [False, True])
def test_concurrent_valid_acks_confirm_both_flows_and_refresh_without_new_epoch(routed):
    protocol, sim = fixture_protocol()
    state = protocol._state(0)
    if routed:
        state.install_route(4, (0, 4), now=0.0, ttl_s=100.0)
    first = start_flow(protocol, sim, 1)
    second = start_flow(protocol, sim, 2)
    sim.now = 2.0
    protocol.on_receive(0, ack(protocol, 1), rx(4))
    epoch = state.route_generation_for(4)
    sim.now = 3.0
    protocol.on_receive(0, ack(protocol, 2), rx(4))
    assert first.acked_at == 2.0
    assert second.acked_at == 3.0
    assert sim.metrics.flows[2].acked_at == 3.0
    assert state.route_generation_for(4) == epoch
    assert state.routes[4].last_accepted_ack_at == 3.0


@pytest.mark.parametrize("marker", [None, 1, 2])
def test_valid_old_flow_ack_confirms_without_overwriting_newer_different_route(marker):
    protocol, sim = fixture_protocol()
    state = protocol._state(0)
    route = state.install_route(4, (0, 4), now=0.0, ttl_s=100.0)
    flow = start_flow(protocol, sim, 1)
    if marker == 1:
        flow.repeat_started_at = 1.5
    elif marker == 2:
        flow.repeat_started_at = 1.5
        flow.recovery_started_at = 1.8
        flow.recovery_route_epoch = route.generation
    new = state.install_route(4, (0, 2, 4), now=2.0, ttl_s=100.0)
    sim.now = 3.0
    protocol.on_receive(0, ack(protocol, 1, marker=marker), rx(4))
    assert flow.acked_at == 3.0
    assert sim.metrics.flows[1].acked_at == 3.0
    assert state.routes[4] is new
    assert state.routes[4].path == (0, 2, 4)
    assert state.routes[4].last_accepted_ack_at == 2.0
    assert protocol.action_events[-1]["cache_update"] == "preserved-newer-route"


@pytest.mark.parametrize("marker", [None, 2])
def test_source_return_is_rejected_even_after_seen_entry_expires(marker):
    protocol, sim = fixture_protocol()
    packet = Packet(kind="FLOOD", flow_id=1, request_id=1,
                    origin=0, final_dst=4, ttl=3, created_at=1.0,
                    protocol=protocol.name, path=(0, 1), path_index=1,
                    repair_index=marker)
    protocol.seen_floods[0].add(protocol._seen_key(packet), 0.0)
    sim.now = 31.0
    assert not protocol.seen_floods[0].contains(protocol._seen_key(packet), sim.now)
    before = len(sim.tx_requests)
    protocol.on_receive(0, packet, rx(1))
    assert len(sim.tx_requests) == before
    assert not protocol.pending_fallback


@pytest.mark.parametrize("path,sender,index", [((0, 1, 1), 1, 2), ((2, 1), 1, 1),
                                             ((0, 1), 2, 1), ((0, 1), 1, 0)])
def test_malformed_flood_has_no_delivery_or_forwarding_side_effect(path, sender, index):
    protocol, sim = fixture_protocol()
    sim.metrics.register_flow(1, 0, 4, 1.0)
    packet = Packet(kind="FLOOD", flow_id=1, request_id=1, origin=0,
                    final_dst=4, ttl=3, created_at=1.0, protocol=protocol.name,
                    path=path, path_index=index)
    protocol.on_receive(4, packet, rx(sender))
    assert sim.metrics.flows[1].delivered_at is None
    assert not sim.tx_requests


def test_initial_source_injection_records_seen_identity():
    protocol, sim = fixture_protocol()
    start_flow(protocol, sim, 1)
    packet = sim.transmissions[-1].packet
    assert packet.kind == "FLOOD"
    assert protocol.seen_floods[0].contains(protocol._seen_key(packet), sim.now)


def test_valid_final_hop_delivers_and_acks_at_maximum_path_length():
    protocol, sim = fixture_protocol()
    sim.metrics.register_flow(1, 0, 4, 1.0)
    packet = Packet(kind="FLOOD", flow_id=1, request_id=1, origin=0,
                    final_dst=4, ttl=1, created_at=1.0, protocol=protocol.name,
                    path=(0, 1, 2, 3), path_index=3)
    protocol.on_receive(4, packet, rx(3))
    assert sim.metrics.flows[1].delivered_at is not None
    assert len(sim.tx_requests) == 1
    assert sim.tx_requests[0]["packet_kind"] == "ACK"


@pytest.mark.parametrize("change,reason", [
    ({"flow_id": 99}, "flow-request-mismatch"),
    ({"request_id": 99}, "flow-request-mismatch"),
    ({"origin": 3}, "endpoint-mismatch"),
    ({"path": (0, 1, 1, 4)}, "looped-path"),
    ({"repair_index": 1}, "repeat-not-started"),
    ({"repair_index": 2}, "recovery-not-started"),
    ({"repair_index": 3}, "marker-mismatch"),
])
def test_ack_identity_and_stage_checks_survive_decoupled_cache(change, reason):
    protocol, sim = fixture_protocol()
    flow = start_flow(protocol, sim, 1)
    packet = replace(ack(protocol, 1), **change)
    sim.now = 2.0
    assert protocol._cpr_ack_rejection_reason(flow, packet, rx(packet.path[1])) == reason


def test_ack_after_deadline_and_replay_cannot_finish_a_flow_twice():
    protocol, sim = fixture_protocol()
    flow = start_flow(protocol, sim, 1)
    sim.now = flow.deadline + 0.01
    protocol.on_receive(0, ack(protocol, 1), rx(4))
    assert flow.acked_at is None
    sim.now = 2.0
    protocol.on_receive(0, ack(protocol, 1), rx(4))
    count = len([e for e in protocol.action_events if e["event"] == "ack-accept"])
    sim.now = 3.0
    protocol.on_receive(0, ack(protocol, 1), rx(4))
    assert count == 1
    assert len([e for e in protocol.action_events if e["event"] == "ack-accept"]) == 1
    assert sim.metrics.flows[1].acked_at == 2.0


def test_source_physical_stage_bound_and_recovery_seen_key():
    protocol, sim = fixture_protocol()
    protocol._state(0).install_route(4, (0, 4), now=0.0, ttl_s=100.0)
    flow = start_flow(protocol, sim, 1)
    sim.now = 2.0
    protocol._cpr_arm_repeat(1)
    repeat = protocol._cpr_placeholder(flow, "CPR_REPEAT_REQUEST")
    sim.begin_transmission(0, repeat, protocol.cpr_repeat_pending[1])
    sim.now = 3.0
    protocol._cpr_arm_recovery(1)
    recovery = protocol._cpr_placeholder(flow, "CPR_RECOVERY_REQUEST")
    sim.begin_transmission(0, recovery, protocol.cpr_recovery_pending[1])
    flood = sim.transmissions[-1].packet
    assert protocol.seen_floods[0].contains(protocol._seen_key(flood), sim.now)
    protocol.on_receive(0, replace(flood, path=(0, 1), path_index=1), rx(1))
    for kind in ("CPR_REQUEST", "CPR_REPEAT_REQUEST", "CPR_RECOVERY_REQUEST"):
        sim.begin_transmission(0, protocol._cpr_placeholder(flow, kind), PendingSend())
    assert [(tx.packet.kind, tx.packet.repair_index) for tx in sim.transmissions] == [
        ("DATA", None), ("DATA", 1), ("FLOOD", 2),
    ]
    assert all(len(set(tx.packet.path)) == len(tx.packet.path) for tx in sim.transmissions)


def test_noackcancel_preserves_capacity_cancellation_and_only_disables_ack_cancellation():
    for cancel_on_ack in (True, False):
        protocol, sim = fixture_protocol(
            cancel_on_ack=cancel_on_ack, relay_ledger_enabled=True,
            evict_pending_on_capacity=True, relay_capacity=1,
        )
        pending = []
        for flow_id in (1, 2):
            packet = Packet(kind="FLOOD", flow_id=flow_id, request_id=flow_id,
                            origin=0, final_dst=4, ttl=4, created_at=0.0,
                            protocol=protocol.name, path=(0,), path_index=0)
            protocol.on_receive(1, packet, rx(0))
            pending.append(protocol.pending_fallback[(1, protocol._seen_key(packet))])
        assert pending[0].canceled
        assert not pending[1].canceled
        assert len([e for e in protocol.action_events if e["event"] == "state-eviction"]) == 1
        protocol.on_receive(1, ack(protocol, 2), rx(4))
        assert pending[1].canceled is cancel_on_ack
    legacy, _ = fixture_protocol(cancel_on_ack=False)
    assert not legacy.relay_ledger_enabled
    assert not legacy.evict_pending_on_capacity


def test_no_repeat_reserves_observation_slot_without_inventing_physical_repeat():
    protocol, sim = fixture_protocol(enable_repeat=False)
    protocol._state(0).install_route(4, (0, 4), now=0.0, ttl_s=100.0)
    flow = start_flow(protocol, sim, 1)
    bound = protocol._cpr_route_bound_s(0, 4, 1, (0, 4), repair_index=1)
    assert flow.skipped_repeat_slot_ends_at == 1.0 + 2.0 * bound
    sim.now = flow.skipped_repeat_slot_ends_at - 0.01
    protocol._cpr_arm_repeat(1)
    protocol._cpr_arm_recovery(1)
    assert not protocol.cpr_repeat_pending and not protocol.cpr_recovery_pending
    sim.now = flow.skipped_repeat_slot_ends_at
    protocol._cpr_arm_recovery(1)
    sim.begin_transmission(0, protocol._cpr_placeholder(flow, "CPR_RECOVERY_REQUEST"),
                           protocol.cpr_recovery_pending[1])
    assert flow.repeat_started_at is None
    assert [(tx.packet.kind, tx.packet.repair_index) for tx in sim.transmissions] == [
        ("DATA", None), ("FLOOD", 2),
    ]
    sim.now += 1.0
    protocol.on_receive(0, ack(protocol, 1, marker=2), rx(4))
    assert flow.acked_at == sim.now


def test_no_recovery_retains_repeat_and_never_requests_or_starts_recovery():
    protocol, sim = fixture_protocol(enable_recovery=False)
    protocol._state(0).install_route(4, (0, 4), now=0.0, ttl_s=100.0)
    flow = start_flow(protocol, sim, 1)
    sim.now = 2.0
    protocol._cpr_arm_repeat(1)
    sim.begin_transmission(0, protocol._cpr_placeholder(flow, "CPR_REPEAT_REQUEST"),
                           protocol.cpr_repeat_pending[1])
    sim.now = 3.0
    protocol._cpr_arm_recovery(1)
    assert not flow.recovery_requested and not protocol.cpr_recovery_pending
    assert protocol._cpr_start_recovery(0, 1, 3.0, PendingSend()) is None
    assert [(tx.packet.kind, tx.packet.repair_index) for tx in sim.transmissions] == [
        ("DATA", None), ("DATA", 1),
    ]


@pytest.mark.parametrize("name", ["meshecho-cpr", "meshecho-cpr-nocancel",
                                 "meshecho-cpr-noackcancel", "meshecho-cpr-norepeat",
                                 "meshecho-cpr-norecovery"])
def test_protocol_controls_have_distinct_and_explicit_identities(name):
    protocol = build_protocol(name)
    assert protocol.name == name
    assert protocol.enable_repeat is (name != "meshecho-cpr-norepeat")
    assert protocol.enable_recovery is (name != "meshecho-cpr-norecovery")
    assert protocol.relay_ledger_enabled is (name != "meshecho-cpr-nocancel")
    assert protocol.cancel_on_ack is (name not in {"meshecho-cpr-nocancel", "meshecho-cpr-noackcancel"})


def test_pure_recovery_controller_obeys_disabled_actions_and_slot_boundary():
    observation = CprObservation(now=4.0, deadline=30.0, route_bound_s=2.0,
                                flood_bound_s=8.0, repeat_started=False,
                                enable_repeat=False)
    assert choose_recovery_action(observation).reason == "repeat-slot-not-elapsed"
    observation = replace(observation, repeat_slot_elapsed=True)
    assert choose_recovery_action(observation).action is CprAction.F_RECOVERY
    observation = replace(observation, enable_recovery=False)
    assert choose_recovery_action(observation).reason == "recovery-disabled"


def test_exact_deadline_ack_precedes_expiration_independent_of_enqueue_order():
    protocol, sim = fixture_protocol()
    flow = start_flow(protocol, sim, 1)
    sim.events.clear()
    sim.handle_tx_end = lambda _: protocol.on_receive(0, ack(protocol, 1), rx(4))
    sim.schedule(flow.deadline, "protocol_timer", lambda: protocol._cpr_expire_deadline(1))
    sim.schedule(flow.deadline, "tx_end", None)
    sim.run(flow.deadline)
    assert flow.acked_at == flow.deadline
    assert sim.metrics.flows[1].acked_at == flow.deadline
    assert not any(event["event"] == "timeout" for event in protocol.action_events)


def test_expiration_never_relabels_a_committed_source_request_as_canceled():
    protocol, sim = fixture_protocol()
    flow = start_flow(protocol, sim, 1)
    pending = protocol.cpr_initial_pending[1]
    assert pending.committed
    sim.now = flow.deadline
    protocol._cpr_expire_deadline(1)
    assert not pending.canceled
    assert sim.metrics.tx_count == 1


def test_duplicate_flood_does_not_count_cancellation_after_relay_commit():
    protocol, sim = fixture_protocol()
    packet = Packet(kind="FLOOD", flow_id=1, request_id=1, origin=0,
                    final_dst=4, ttl=4, created_at=0.0, protocol=protocol.name,
                    path=(0,), path_index=0)
    protocol.on_receive(1, packet, rx(0))
    pending = protocol.pending_fallback[(1, protocol._seen_key(packet))]
    forwarded = replace(packet, path=(0, 1), path_index=1, ttl=3)
    sim.begin_transmission(1, forwarded, pending)
    assert pending.committed
    protocol.on_receive(1, packet, rx(0))
    assert not pending.canceled
    assert sim.metrics.suppressed_forwards == 0
    assert sim.metrics.duplicate_rx == 1
    assert sim.metrics.tx_count == 1


def test_duplicate_flood_cancels_only_the_same_uncommitted_stage():
    protocol, sim = fixture_protocol()
    packet = Packet(kind="FLOOD", flow_id=1, request_id=1, origin=0,
                    final_dst=4, ttl=4, created_at=0.0, protocol=protocol.name,
                    path=(0,), path_index=0)
    recovery = replace(packet, repair_index=2)
    protocol.on_receive(1, packet, rx(0))
    initial_pending = protocol.pending_fallback[(1, protocol._seen_key(packet))]
    protocol.on_receive(1, recovery, rx(0))
    recovery_pending = protocol.pending_fallback[(1, protocol._seen_key(recovery))]
    protocol.on_receive(1, packet, rx(0))
    assert initial_pending.canceled and not recovery_pending.canceled
    assert sim.metrics.suppressed_forwards == 1


def test_older_flow_timeout_cannot_quarantine_a_newer_same_path_confirmation():
    protocol, sim = fixture_protocol()
    state = protocol._state(0)
    route = state.install_route(4, (0, 4), now=0.0, ttl_s=100.0)
    old = start_flow(protocol, sim, 1, now=1.0)
    start_flow(protocol, sim, 2, now=2.0)
    sim.now = 3.0
    protocol.on_receive(0, ack(protocol, 2), rx(4))
    assert state.routes[4].generation == route.generation
    sim.now = old.deadline
    protocol._cpr_expire_deadline(1)
    assert state.routes[4].phase.value == "READY"
    assert state.routes[4].miss_streak == 0
    following = start_flow(protocol, sim, 3, now=old.deadline + 0.1)
    assert following.initial_action == "R"


def test_timeout_after_same_timestamp_ack_refresh_uses_revision_not_float_time():
    protocol, sim = fixture_protocol()
    state = protocol._state(0)
    state.install_route(4, (0, 4), now=1.0, ttl_s=100.0)
    old = start_flow(protocol, sim, 1, now=1.0)
    # A second confirmation at the same timestamp is newer evidence even
    # though comparison of last_accepted_ack_at alone cannot distinguish it.
    state.refresh_same_ready_route(4, (0, 4), now=1.0, ttl_s=100.0)
    sim.now = old.deadline
    protocol._cpr_expire_deadline(1)
    assert state.routes[4].phase.value == "READY"


def test_a_flow_started_after_latest_confirmation_can_still_quarantine_on_timeout():
    protocol, sim = fixture_protocol()
    state = protocol._state(0)
    state.install_route(4, (0, 4), now=0.0, ttl_s=100.0)
    state.refresh_same_ready_route(4, (0, 4), now=1.0, ttl_s=100.0)
    current = start_flow(protocol, sim, 1, now=2.0)
    sim.now = current.deadline
    protocol._cpr_expire_deadline(1)
    assert state.routes[4].phase.value == "QUARANTINED"


@pytest.mark.parametrize("pending_state", ["absent", "committed", "cancelable"])
def test_decoded_ack_cancellation_checks_and_successes_are_observed_separately(pending_state):
    protocol, sim = fixture_protocol()
    if pending_state != "absent":
        packet = Packet(kind="FLOOD", flow_id=1, request_id=1, origin=0,
                        final_dst=4, ttl=4, created_at=0.0, protocol=protocol.name,
                        path=(0,), path_index=0)
        protocol.on_receive(1, packet, rx(0))
        pending = protocol.pending_fallback[(1, protocol._seen_key(packet))]
        if pending_state == "committed":
            pending.committed = True
    protocol.on_receive(1, ack(protocol, 1), rx(4))
    checks = [e for e in protocol.action_events if e["event"] == "cpr-cancel-check"]
    successes = [e for e in protocol.action_events if e["event"] == "cpr-cancel"]
    assert len(checks) == 1
    assert checks[0]["node"] == 1 and checks[0]["flow_id"] == 1
    assert checks[0]["canceled"] is (pending_state == "cancelable")
    assert len(successes) == int(pending_state == "cancelable")


def test_disabled_ack_cancellation_emits_no_cancellation_check():
    protocol, sim = fixture_protocol(cancel_on_ack=False, relay_ledger_enabled=True)
    protocol.on_receive(1, ack(protocol, 1), rx(4))
    assert not any(e["event"] in {"cpr-cancel-check", "cpr-cancel"} for e in protocol.action_events)
