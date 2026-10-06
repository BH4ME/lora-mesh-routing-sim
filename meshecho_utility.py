"""Device-local utility controller used by the rewritten MeshEcho core.

The controller deliberately has no simulator or topology dependency.  It only
consumes observations that a source can maintain from its own transmissions,
accepted ACKs, carried forward-margin feedback and local timing budget.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Action(str, Enum):
    ROUTE = "R"
    FLOOD = "F"
    DISCOVER = "D"


@dataclass(frozen=True)
class UtilityObservation:
    route_available: bool
    route_age_s: float
    route_hops: int
    route_ttl_s: float
    remaining_deadline_s: float
    token_available: bool
    recent_demand: bool
    r_attempts: int
    r_acks: int
    f_attempts: int
    f_acks: int
    d_attempts: int
    d_acks: int
    latest_margin_q: Optional[int]
    previous_margin_q: Optional[int]
    consecutive_r_misses: int
    route_cost_s: float
    flood_cost_s: float
    discovery_cost_s: float


@dataclass(frozen=True)
class UtilityDecision:
    action: Action
    reason: str
    route_success: float
    flood_success: float
    discovery_success: float
    route_utility: float
    flood_utility: float
    discovery_utility: float


def _beta_mean(acks: int, attempts: int) -> float:
    attempts = max(0, int(attempts))
    acks = min(max(0, int(acks)), attempts)
    return (acks + 1.0) / (attempts + 2.0)


def _margin_probability(margin_q: Optional[int]) -> float:
    if margin_q is None or margin_q == 127:
        return 0.5
    margin_q = max(-126, min(126, int(margin_q)))
    return 1.0 / (1.0 + math.exp(-margin_q / 6.0))


def _bounded_cost(cost_s: float, deadline_s: float) -> float:
    if cost_s < 0.0 or deadline_s <= 0.0:
        return 1.0
    return min(1.0, cost_s / max(deadline_s, 1e-9))


def choose_action(observation: UtilityObservation) -> UtilityDecision:
    """Choose one source action from local reliability/cost posteriors.

    Reliability is a Laplace-smoothed Beta posterior.  The routed posterior is
    blended with the latest ACK-carried minimum forward margin and discounted
    by route age.  Cost is normalized by the remaining application deadline;
    a fixed coefficient keeps action selection deterministic and auditable.
    """

    route_success = _beta_mean(observation.r_acks, observation.r_attempts)
    flood_success = _beta_mean(observation.f_acks, observation.f_attempts)
    discovery_success = _beta_mean(observation.d_acks, observation.d_attempts)

    margin = _margin_probability(observation.latest_margin_q)
    # The ACK history is conservative when a route has just been learned from
    # a useful flood.  Give the physically observed margin enough weight to
    # recognize that a freshly ACKed, high-margin route is already evidence.
    route_feedback = 0.45 * route_success + 0.55 * margin
    age_ratio = min(
        1.0,
        max(0.0, observation.route_age_s)
        / max(observation.route_ttl_s, 1e-9),
    )
    age_discount = 1.0 - 0.35 * age_ratio
    route_success = max(0.0, min(1.0, route_feedback * age_discount))

    route_utility = route_success - 0.18 * _bounded_cost(
        observation.route_cost_s, observation.remaining_deadline_s
    )
    flood_utility = flood_success - 0.18 * _bounded_cost(
        observation.flood_cost_s, observation.remaining_deadline_s
    )
    discovery_utility = discovery_success - 0.18 * _bounded_cost(
        observation.discovery_cost_s, observation.remaining_deadline_s
    )

    if not observation.route_available:
        return UtilityDecision(
            Action.FLOOD,
            "no-confirmed-route",
            route_success,
            flood_success,
            discovery_success,
            route_utility,
            flood_utility,
            discovery_utility,
        )

    route_risk = (
        observation.consecutive_r_misses >= 2
        or route_success + 0.02 < flood_success
        or observation.latest_margin_q is not None
        and observation.latest_margin_q != 127
        and observation.latest_margin_q <= 0
        or observation.previous_margin_q is not None
        and observation.latest_margin_q is not None
        and observation.latest_margin_q != 127
        and observation.previous_margin_q - observation.latest_margin_q >= 6
    )
    discovery_budget_ok = (
        observation.remaining_deadline_s > 0.0
        and observation.discovery_cost_s <= observation.remaining_deadline_s
    )
    discovery_eligible = (
        route_risk
        and observation.token_available
        and observation.recent_demand
        and discovery_budget_ok
        and observation.discovery_cost_s <= 1.10 * max(
            observation.flood_cost_s, 1e-9
        )
        and discovery_utility > max(route_utility, flood_utility) + 0.02
    )
    if discovery_eligible:
        return UtilityDecision(
            Action.DISCOVER,
            "discovery-utility-dominates",
            route_success,
            flood_success,
            discovery_success,
            route_utility,
            flood_utility,
            discovery_utility,
        )
    if route_risk and not discovery_budget_ok:
        return UtilityDecision(
            Action.FLOOD,
            "discovery-deadline-rejected",
            route_success,
            flood_success,
            discovery_success,
            route_utility,
            flood_utility,
            discovery_utility,
        )
    if route_utility >= flood_utility:
        return UtilityDecision(
            Action.ROUTE,
            "route-utility-dominates",
            route_success,
            flood_success,
            discovery_success,
            route_utility,
            flood_utility,
            discovery_utility,
        )
    return UtilityDecision(
        Action.FLOOD,
        "flood-utility-dominates",
        route_success,
        flood_success,
        discovery_success,
        route_utility,
        flood_utility,
        discovery_utility,
    )
