"""Standalone source decision core for the MeshEcho-DRC rewrite.

The module intentionally contains no simulator, topology, or PHY dependency.
It models the source-side contract at an immediately committable physical TX
start.  The simulator can use its own packet/ToA implementation to populate
the two conservative bounds in :class:`DrcObservation`.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


MAX_ROUTE_RECORDS = 8
MAX_ACTIVE_FLOWS = 8


class RoutePhase(str, Enum):
    NO_ROUTE = "NO_ROUTE"
    READY = "READY"
    QUARANTINED = "QUARANTINED"


class RecoveryState(str, Enum):
    NOT_DUE = "NOT_DUE"
    PENDING = "PENDING"
    STARTED = "STARTED"
    CANCELED = "CANCELED"
    DONE = "DONE"


class DrcAction(str, Enum):
    R_RESERVED = "R_RESERVED"
    F_INITIAL = "F_INITIAL"
    R_ONLY = "R_ONLY"
    F_RECOVERY = "F_RECOVERY"
    DROP_DEADLINE_INFEASIBLE = "DROP_DEADLINE_INFEASIBLE"


@dataclass(frozen=True)
class DrcObservation:
    """Only source-local values available at a physical TX start.

    ``route_bound_s`` and ``flood_bound_s`` are supplied by the local PHY
    accounting layer.  They are complete charged airtime/scheduling bounds,
    not success probabilities or simulator-derived future knowledge.
    """

    now: float
    deadline: float
    route_path: Tuple[int, ...] = ()
    route_phase: RoutePhase = RoutePhase.NO_ROUTE
    route_generation: Optional[int] = None
    route_expires_at: Optional[float] = None
    route_bound_s: float = 0.0
    flood_bound_s: float = 0.0
    recovery_due: bool = False
    recovery_started: bool = False
    original_route_generation: Optional[int] = None
    flow_acked: bool = False

    def __post_init__(self) -> None:
        if self.now < 0.0:
            raise ValueError("now must be nonnegative")
        if self.route_bound_s < 0.0 or self.flood_bound_s < 0.0:
            raise ValueError("admission bounds must be nonnegative")
        # A late decision is valid input and must produce a no-start result;
        # rejecting it here would hide deadline censoring.


@dataclass(frozen=True)
class DrcDecision:
    action: DrcAction
    reason: str
    guard_at: Optional[float] = None


def _fits(now: float, duration_s: float, deadline: float) -> bool:
    """A nonzero packet must physically start before the deadline."""

    return now < deadline and now + duration_s <= deadline


def _route_ready(observation: DrcObservation) -> bool:
    if observation.route_phase is not RoutePhase.READY:
        return False
    if not observation.route_path or observation.route_generation is None:
        return False
    if observation.route_expires_at is None:
        return False
    return observation.now < observation.route_expires_at


def choose_start_action(observation: DrcObservation) -> DrcDecision:
    """Choose the source action at the current, real TX-start opportunity.

    The ordering is the DRC contract: a pending recovery is considered first;
    otherwise a confirmed route gets a reservation only when both the routed
    attempt and one useful FLOOD fit before the original deadline.  If that
    reservation does not fit, the source prefers one initial FLOOD, then a
    route-only attempt, and finally emits no packet.
    """

    if observation.flow_acked:
        return DrcDecision(DrcAction.DROP_DEADLINE_INFEASIBLE, "already-acked")

    if observation.recovery_due:
        generation_current = (
            observation.route_generation is not None
            and observation.original_route_generation is not None
            and observation.route_generation == observation.original_route_generation
        )
        if observation.recovery_started:
            return DrcDecision(
                DrcAction.DROP_DEADLINE_INFEASIBLE,
                "recovery-already-started",
            )
        if not generation_current:
            return DrcDecision(
                DrcAction.DROP_DEADLINE_INFEASIBLE,
                "stale-route-generation",
            )
        if _fits(observation.now, observation.flood_bound_s, observation.deadline):
            return DrcDecision(DrcAction.F_RECOVERY, "recovery-fits-deadline")
        return DrcDecision(
            DrcAction.DROP_DEADLINE_INFEASIBLE,
            "recovery-deadline-infeasible",
        )

    route_ready = _route_ready(observation)
    if route_ready and _fits(
        observation.now,
        observation.route_bound_s + observation.flood_bound_s,
        observation.deadline,
    ):
        return DrcDecision(
            DrcAction.R_RESERVED,
            "route-and-recovery-fit",
            guard_at=observation.now + observation.route_bound_s,
        )

    if _fits(observation.now, observation.flood_bound_s, observation.deadline):
        return DrcDecision(DrcAction.F_INITIAL, "initial-flood-fits")

    if route_ready and _fits(
        observation.now, observation.route_bound_s, observation.deadline
    ):
        return DrcDecision(DrcAction.R_ONLY, "route-only-fits")

    return DrcDecision(
        DrcAction.DROP_DEADLINE_INFEASIBLE,
        "deadline-infeasible",
    )


@dataclass
class DrcRouteRecord:
    destination: int
    path: Tuple[int, ...]
    generation: int
    expires_at: float
    phase: RoutePhase = RoutePhase.READY
    last_accepted_ack_at: Optional[float] = None
    miss_streak: int = 0
    last_used_lru: int = 0


@dataclass
class DrcFlowRecord:
    flow_id: int
    source: int
    destination: int
    enqueue_at: float
    deadline: float
    initial_action: Optional[DrcAction] = None
    initial_path: Tuple[int, ...] = ()
    route_generation: Optional[int] = None
    physical_start: Optional[float] = None
    guard_at: Optional[float] = None
    recovery_state: RecoveryState = RecoveryState.NOT_DUE
    recovery_start: Optional[float] = None
    acked_at: Optional[float] = None


@dataclass(frozen=True)
class DrcRegistration:
    accepted: bool
    reason: str
    flow: Optional[DrcFlowRecord] = None


class DrcSourceState:
    """Bounded source-local route and active-flow state.

    Diagnostic traces may retain more history outside this class, but policy
    decisions can be reproduced from at most eight LRU route records and eight
    active flow records.
    """

    def __init__(
        self,
        *,
        max_route_records: int = MAX_ROUTE_RECORDS,
        max_active_flows: int = MAX_ACTIVE_FLOWS,
    ) -> None:
        if max_route_records <= 0 or max_active_flows <= 0:
            raise ValueError("state capacities must be positive")
        self.max_route_records = max_route_records
        self.max_active_flows = max_active_flows
        self.routes: "OrderedDict[int, DrcRouteRecord]" = OrderedDict()
        self.active_flows: "OrderedDict[int, DrcFlowRecord]" = OrderedDict()
        self._destination_epochs: "OrderedDict[int, int]" = OrderedDict()
        self._lru_counter = 0
        self._generation_counter = 0

    @property
    def route_count(self) -> int:
        return len(self.routes)

    @property
    def active_flow_count(self) -> int:
        return len(self.active_flows)

    def _touch(self, records: "OrderedDict[int, object]", key: int) -> None:
        self._lru_counter += 1
        value = records.pop(key)
        if hasattr(value, "last_used_lru"):
            value.last_used_lru = self._lru_counter
        records[key] = value

    def install_route(
        self,
        destination: int,
        path: Tuple[int, ...],
        *,
        now: float,
        ttl_s: float,
    ) -> DrcRouteRecord:
        """Install an ACK-confirmed path, evicting the least-recent record."""

        if len(path) < 2 or len(set(path)) != len(path):
            raise ValueError("route path must be loop-free and have at least two nodes")
        if ttl_s <= 0.0:
            raise ValueError("route TTL must be positive")
        self._generation_counter += 1
        generation = self._generation_counter
        self._destination_epochs.pop(destination, None)
        self._destination_epochs[destination] = generation
        self._prune_destination_epochs()
        if destination in self.routes:
            self.routes.pop(destination)
        elif len(self.routes) >= self.max_route_records:
            self.routes.popitem(last=False)
        record = DrcRouteRecord(
            destination=destination,
            path=tuple(path),
            generation=generation,
            expires_at=now + ttl_s,
            last_accepted_ack_at=now,
        )
        self._touch_insert(self.routes, destination, record)
        return record

    def _prune_destination_epochs(self) -> None:
        """Keep generation tombstones bounded while protecting live flows."""

        capacity = self.max_route_records + self.max_active_flows
        if len(self._destination_epochs) <= capacity:
            return
        protected = set(self.routes)
        protected.update(flow.destination for flow in self.active_flows.values())
        attempts = len(self._destination_epochs)
        while len(self._destination_epochs) > capacity and attempts:
            destination, _ = next(iter(self._destination_epochs.items()))
            self._destination_epochs.move_to_end(destination)
            attempts -= 1
            if destination in protected:
                continue
            self._destination_epochs.pop(destination, None)

    def route_generation_for(self, destination: int) -> int:
        """Return the latest destination-specific route epoch, including tombstones."""

        return self._destination_epochs.get(destination, 0)

    def _touch_insert(
        self,
        records: "OrderedDict[int, object]",
        key: int,
        value: object,
    ) -> None:
        self._lru_counter += 1
        if hasattr(value, "last_used_lru"):
            value.last_used_lru = self._lru_counter
        records[key] = value

    def get_route(self, destination: int, *, now: Optional[float] = None) -> Optional[DrcRouteRecord]:
        record = self.routes.get(destination)
        if record is None:
            return None
        if now is not None and now >= record.expires_at:
            record.phase = RoutePhase.NO_ROUTE
            return None
        self._touch(self.routes, destination)
        return record

    def record_in_deadline_miss(self, destination: int, generation: int) -> bool:
        """Quarantine a generation and evict it after its second miss.

        Returns ``True`` only when the route record is evicted.  A stale
        generation cannot mutate a newer ACK-confirmed route.
        """

        record = self.routes.get(destination)
        if record is None or record.generation != generation:
            return False
        record.phase = RoutePhase.QUARANTINED
        record.miss_streak = min(2, record.miss_streak + 1)
        if record.miss_streak >= 2:
            record.phase = RoutePhase.NO_ROUTE
            self.routes.pop(destination, None)
            return True
        self._touch(self.routes, destination)
        return False

    def register_flow(
        self,
        flow_id: int,
        *,
        source: int,
        destination: int,
        enqueue_at: float,
        deadline_s: float,
    ) -> DrcRegistration:
        if deadline_s <= 0.0:
            raise ValueError("flow deadline must be positive")
        if flow_id in self.active_flows:
            return DrcRegistration(False, "duplicate-flow")
        if len(self.active_flows) >= self.max_active_flows:
            return DrcRegistration(False, "state-capacity-drop")
        flow = DrcFlowRecord(
            flow_id=flow_id,
            source=source,
            destination=destination,
            enqueue_at=enqueue_at,
            deadline=enqueue_at + deadline_s,
        )
        self._touch_insert(self.active_flows, flow_id, flow)
        self._prune_destination_epochs()
        return DrcRegistration(True, "registered", flow)

    def observation_for(
        self,
        flow_id: int,
        *,
        now: float,
        route_bound_s: float,
        flood_bound_s: float,
    ) -> DrcObservation:
        flow = self.active_flows[flow_id]
        route = self.get_route(flow.destination, now=now)
        recovery_due = flow.recovery_state is RecoveryState.PENDING
        return DrcObservation(
            now=now,
            deadline=flow.deadline,
            route_path=route.path if route is not None else (),
            route_phase=route.phase if route is not None else RoutePhase.NO_ROUTE,
            route_generation=route.generation if route is not None else None,
            route_expires_at=route.expires_at if route is not None else None,
            route_bound_s=route_bound_s,
            flood_bound_s=flood_bound_s,
            recovery_due=recovery_due,
            original_route_generation=flow.route_generation,
            recovery_started=flow.recovery_state is RecoveryState.STARTED,
            flow_acked=flow.acked_at is not None,
        )

    def start_initial(
        self,
        flow_id: int,
        decision: DrcDecision,
        *,
        now: float,
    ) -> DrcFlowRecord:
        flow = self.active_flows[flow_id]
        if decision.action in {
            DrcAction.DROP_DEADLINE_INFEASIBLE,
            DrcAction.F_RECOVERY,
        }:
            raise ValueError("decision is not an initial action")
        flow.initial_action = decision.action
        flow.physical_start = now
        flow.guard_at = decision.guard_at
        route = self.routes.get(flow.destination)
        if decision.action in {DrcAction.R_RESERVED, DrcAction.R_ONLY} and route:
            flow.initial_path = route.path
            flow.route_generation = route.generation
        return flow

    def arm_recovery(self, flow_id: int, *, now: float) -> bool:
        flow = self.active_flows[flow_id]
        if flow.acked_at is not None or flow.initial_action is not DrcAction.R_RESERVED:
            return False
        if flow.guard_at is None or now < flow.guard_at:
            return False
        route = self.get_route(flow.destination, now=now)
        if route is None or route.generation != flow.route_generation:
            return False
        route.phase = RoutePhase.QUARANTINED
        flow.recovery_state = RecoveryState.PENDING
        return True

    def start_recovery(
        self,
        flow_id: int,
        decision: DrcDecision,
        *,
        now: float,
    ) -> DrcFlowRecord:
        flow = self.active_flows[flow_id]
        if decision.action is not DrcAction.F_RECOVERY:
            raise ValueError("decision is not a recovery action")
        if flow.recovery_state is not RecoveryState.PENDING:
            raise ValueError("recovery is not pending")
        flow.recovery_state = RecoveryState.STARTED
        flow.recovery_start = now
        return flow

    def accept_valid_ack(
        self,
        flow_id: int,
        path: Tuple[int, ...],
        *,
        now: float,
        marker: Optional[int] = None,
        route_ttl_s: float = 600.0,
    ) -> bool:
        """Commit an ACK after the simulator has checked physical provenance.

        The caller must invoke this only for a source-decoded ACK whose actual
        radio sender, endpoint order, path index, and deadline have already
        passed the wire/PHY validation.  This method only applies source-local
        generation and recovery-marker checks; it never inspects topology or a
        destination-delivery oracle.
        """

        flow = self.active_flows[flow_id]
        candidate = tuple(path)
        if flow.acked_at is not None or flow.physical_start is None:
            return False
        if now < flow.physical_start or now > flow.deadline:
            return False
        if len(candidate) < 2 or len(set(candidate)) != len(candidate):
            return False
        if candidate[0] != flow.source or candidate[-1] != flow.destination:
            return False
        if marker not in (None, 2):
            return False
        if marker == 2 and flow.recovery_state is not RecoveryState.STARTED:
            return False
        if marker is None and flow.initial_action in {
            DrcAction.R_RESERVED,
            DrcAction.R_ONLY,
        }:
            if candidate != flow.initial_path:
                return False
        elif marker is None and flow.initial_action is not DrcAction.F_INITIAL:
            return False

        route = self.routes.get(flow.destination)
        if marker == 2:
            if route is None or route.generation != flow.route_generation:
                return False
        if marker is None and flow.initial_action in {
            DrcAction.R_RESERVED,
            DrcAction.R_ONLY,
        }:
            if route is None or route.generation != flow.route_generation:
                return False

        flow.acked_at = now
        flow.recovery_state = (
            RecoveryState.CANCELED
            if flow.recovery_state is RecoveryState.PENDING
            else RecoveryState.DONE
        )
        if route is not None and marker is None and flow.initial_action in {
            DrcAction.R_RESERVED,
            DrcAction.R_ONLY,
        }:
            route.phase = RoutePhase.READY
            route.last_accepted_ack_at = now
            route.miss_streak = 0
            self._touch(self.routes, flow.destination)
        else:
            if route_ttl_s <= 0.0:
                raise ValueError("route TTL must be positive")
            committed = self.install_route(
                flow.destination,
                candidate,
                now=now,
                ttl_s=route_ttl_s,
            )
            flow.route_generation = committed.generation
            flow.initial_path = candidate
        return True

    def cancel_recovery(self, flow_id: int) -> bool:
        flow = self.active_flows[flow_id]
        if flow.recovery_state is not RecoveryState.PENDING:
            return False
        flow.recovery_state = RecoveryState.CANCELED
        return True
