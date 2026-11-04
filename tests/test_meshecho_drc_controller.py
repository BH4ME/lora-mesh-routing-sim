"""Behavioral contract tests for the standalone MeshEcho-DRC source controller."""

from meshecho_drc import (
    DrcAction,
    DrcObservation,
    DrcSourceState,
    RoutePhase,
    choose_start_action,
)


def test_confirmed_route_reserves_time_for_one_flood_recovery():
    decision = choose_start_action(
        DrcObservation(
            now=4.0,
            deadline=30.0,
            route_path=(0, 2, 1),
            route_phase=RoutePhase.READY,
            route_generation=7,
            route_expires_at=100.0,
            route_bound_s=3.0,
            flood_bound_s=8.0,
        )
    )

    assert decision.action is DrcAction.R_RESERVED
    assert decision.guard_at == 7.0
    assert decision.reason == "route-and-recovery-fit"


def test_without_a_confirmed_route_drc_uses_one_initial_flood():
    decision = choose_start_action(
        DrcObservation(
            now=4.0,
            deadline=30.0,
            route_phase=RoutePhase.NO_ROUTE,
            route_bound_s=3.0,
            flood_bound_s=8.0,
        )
    )

    assert decision.action is DrcAction.F_INITIAL
    assert decision.guard_at is None
    assert decision.reason == "initial-flood-fits"


def test_drc_emits_no_packet_when_neither_action_fits_the_original_deadline():
    decision = choose_start_action(
        DrcObservation(
            now=24.0,
            deadline=30.0,
            route_phase=RoutePhase.NO_ROUTE,
            flood_bound_s=8.0,
        )
    )

    assert decision.action is DrcAction.DROP_DEADLINE_INFEASIBLE
    assert decision.reason == "deadline-infeasible"


def test_route_only_is_used_when_recovery_reservation_no_longer_fits():
    decision = choose_start_action(
        DrcObservation(
            now=24.0,
            deadline=30.0,
            route_path=(0, 2, 1),
            route_phase=RoutePhase.READY,
            route_generation=3,
            route_expires_at=100.0,
            route_bound_s=4.0,
            flood_bound_s=8.0,
        )
    )

    assert decision.action is DrcAction.R_ONLY
    assert decision.reason == "route-only-fits"


def test_pending_recovery_uses_flood_only_when_same_generation_and_deadline_fit():
    decision = choose_start_action(
        DrcObservation(
            now=18.0,
            deadline=30.0,
            route_path=(0, 2, 1),
            route_phase=RoutePhase.QUARANTINED,
            route_generation=3,
            route_expires_at=100.0,
            route_bound_s=4.0,
            flood_bound_s=8.0,
            recovery_due=True,
            original_route_generation=3,
        )
    )

    assert decision.action is DrcAction.F_RECOVERY
    assert decision.reason == "recovery-fits-deadline"


def test_source_state_has_bounded_routes_and_active_flows():
    state = DrcSourceState()
    for destination in range(8):
        state.install_route(
            destination,
            (0, destination + 1),
            now=float(destination),
            ttl_s=100.0,
        )
    state.install_route(99, (0, 100), now=8.0, ttl_s=100.0)

    assert state.route_count == 8
    assert state.get_route(0) is None
    assert state.get_route(99) is not None

    for flow_id in range(8):
        result = state.register_flow(
            flow_id,
            source=0,
            destination=1,
            enqueue_at=0.0,
            deadline_s=30.0,
        )
        assert result.accepted
    overflow = state.register_flow(
        8,
        source=0,
        destination=1,
        enqueue_at=0.0,
        deadline_s=30.0,
    )

    assert state.active_flow_count == 8
    assert not overflow.accepted
    assert overflow.reason == "state-capacity-drop"


def test_state_tracks_reserved_route_then_one_recovery_flood():
    state = DrcSourceState()
    route = state.install_route(1, (0, 2, 1), now=0.0, ttl_s=100.0)
    registration = state.register_flow(
        10,
        source=0,
        destination=1,
        enqueue_at=0.0,
        deadline_s=30.0,
    )
    assert registration.accepted

    initial = choose_start_action(
        state.observation_for(
            10,
            now=4.0,
            route_bound_s=3.0,
            flood_bound_s=8.0,
        )
    )
    state.start_initial(10, initial, now=4.0)
    assert initial.action is DrcAction.R_RESERVED
    assert state.arm_recovery(10, now=7.0)

    recovery = choose_start_action(
        state.observation_for(
            10,
            now=8.0,
            route_bound_s=3.0,
            flood_bound_s=8.0,
        )
    )
    state.start_recovery(10, recovery, now=8.0)

    assert route.generation == 1
    assert recovery.action is DrcAction.F_RECOVERY
    assert state.active_flows[10].recovery_start == 8.0


def test_expired_route_is_not_used_for_a_reserved_attempt():
    decision = choose_start_action(
        DrcObservation(
            now=10.0,
            deadline=30.0,
            route_path=(0, 2, 1),
            route_phase=RoutePhase.READY,
            route_generation=4,
            route_expires_at=10.0,
            route_bound_s=3.0,
            flood_bound_s=8.0,
        )
    )

    assert decision.action is DrcAction.F_INITIAL
    assert decision.reason == "initial-flood-fits"


def test_recovery_cannot_use_a_newer_route_generation():
    decision = choose_start_action(
        DrcObservation(
            now=18.0,
            deadline=30.0,
            route_path=(0, 3, 1),
            route_phase=RoutePhase.QUARANTINED,
            route_generation=9,
            route_expires_at=100.0,
            flood_bound_s=8.0,
            recovery_due=True,
            original_route_generation=8,
        )
    )

    assert decision.action is DrcAction.DROP_DEADLINE_INFEASIBLE
    assert decision.reason == "stale-route-generation"


def test_late_physical_start_is_censored_without_a_transmission():
    decision = choose_start_action(
        DrcObservation(
            now=31.0,
            deadline=30.0,
            route_phase=RoutePhase.NO_ROUTE,
            flood_bound_s=0.1,
        )
    )

    assert decision.action is DrcAction.DROP_DEADLINE_INFEASIBLE
    assert decision.reason == "deadline-infeasible"


def test_valid_initial_ack_cancels_unstarted_recovery():
    state = DrcSourceState()
    state.install_route(1, (0, 2, 1), now=0.0, ttl_s=100.0)
    assert state.register_flow(
        10,
        source=0,
        destination=1,
        enqueue_at=0.0,
        deadline_s=30.0,
    ).accepted
    initial = choose_start_action(
        state.observation_for(
            10,
            now=4.0,
            route_bound_s=3.0,
            flood_bound_s=8.0,
        )
    )
    state.start_initial(10, initial, now=4.0)
    assert state.arm_recovery(10, now=7.0)

    assert state.accept_valid_ack(10, (0, 2, 1), now=7.5)
    assert not state.arm_recovery(10, now=8.0)
    after_ack = choose_start_action(
        state.observation_for(
            10,
            now=8.0,
            route_bound_s=3.0,
            flood_bound_s=8.0,
        )
    )
    assert after_ack.action is DrcAction.DROP_DEADLINE_INFEASIBLE
    assert after_ack.reason == "already-acked"


def test_two_in_deadline_misses_evict_the_confirmed_route():
    state = DrcSourceState()
    route = state.install_route(1, (0, 2, 1), now=0.0, ttl_s=100.0)

    assert not state.record_in_deadline_miss(1, route.generation)
    quarantined = state.routes[1]
    assert quarantined.phase is RoutePhase.QUARANTINED
    assert quarantined.miss_streak == 1

    assert state.record_in_deadline_miss(1, route.generation)
    assert state.get_route(1, now=10.0) is None
    assert state.route_count == 0
