from __future__ import annotations

from meshecho_utility import Action, UtilityObservation, choose_action


def observation(**overrides):
    values = dict(
        route_available=True,
        route_age_s=30.0,
        route_hops=2,
        route_ttl_s=600.0,
        remaining_deadline_s=25.0,
        token_available=True,
        recent_demand=True,
        r_attempts=10,
        r_acks=9,
        f_attempts=10,
        f_acks=6,
        d_attempts=2,
        d_acks=1,
        latest_margin_q=20,
        previous_margin_q=20,
        consecutive_r_misses=0,
        route_cost_s=0.8,
        flood_cost_s=2.0,
        discovery_cost_s=1.5,
    )
    values.update(overrides)
    return UtilityObservation(**values)


def test_healthy_confirmed_route_reuses_route():
    decision = choose_action(observation())

    assert decision.action is Action.ROUTE
    assert decision.reason == "route-utility-dominates"


def test_flood_is_selected_when_route_posterior_is_worse_than_flood():
    decision = choose_action(
        observation(
            r_attempts=12,
            r_acks=3,
            f_attempts=12,
            f_acks=11,
            latest_margin_q=-4,
            previous_margin_q=12,
            route_age_s=420.0,
        )
    )

    assert decision.action is Action.FLOOD
    assert decision.reason == "flood-utility-dominates"


def test_discovery_requires_token_demand_and_deadline_budget():
    decision = choose_action(
        observation(
            r_attempts=10,
            r_acks=2,
            f_attempts=10,
            f_acks=8,
            d_attempts=8,
            d_acks=8,
            latest_margin_q=-5,
            previous_margin_q=8,
            route_age_s=480.0,
            flood_cost_s=3.0,
            discovery_cost_s=2.0,
        )
    )

    assert decision.action is Action.DISCOVER
    assert decision.reason == "discovery-utility-dominates"


def test_discovery_is_rejected_when_it_cannot_fit_deadline():
    decision = choose_action(
        observation(
            r_attempts=10,
            r_acks=2,
            f_attempts=10,
            f_acks=8,
            d_attempts=8,
            d_acks=8,
            latest_margin_q=-5,
            previous_margin_q=8,
            route_age_s=480.0,
            remaining_deadline_s=1.0,
            flood_cost_s=3.0,
            discovery_cost_s=2.0,
        )
    )

    assert decision.action is Action.FLOOD
    assert decision.reason == "discovery-deadline-rejected"
