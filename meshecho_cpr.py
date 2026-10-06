"""Source-side decision core for the MeshEcho-CPR successor.

CPR is intentionally independent from the simulator and PHY.  The simulator
supplies conservative, locally computable duration bounds; this module only
decides which recovery action is eligible at a real transmission opportunity.
The first recovery attempt is always a same-path repeat.  A FLOOD recovery is
eligible only after that repeat has physically started and only when its full
bound still fits before the flow deadline.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Tuple


class CprAction(str, Enum):
    """Actions exposed by the CPR recovery controller."""

    R_REPEAT = "R_REPEAT"
    F_RECOVERY = "F_RECOVERY"
    DROP_DEADLINE_INFEASIBLE = "DROP_DEADLINE_INFEASIBLE"


@dataclass(frozen=True)
class CprObservation:
    """Source-local state available at a recovery decision point.

    ``repeat_started`` is a physical event, not a queued-request flag.  The
    caller must set it only after the repeat TX actually starts.
    """

    now: float
    deadline: float
    route_bound_s: float
    flood_bound_s: float
    repeat_started: bool
    flow_acked: bool = False
    recovery_started: bool = False

    def __post_init__(self) -> None:
        if self.now < 0.0:
            raise ValueError("now must be nonnegative")
        if self.route_bound_s < 0.0 or self.flood_bound_s < 0.0:
            raise ValueError("recovery bounds must be nonnegative")


@dataclass(frozen=True)
class CprDecision:
    action: CprAction
    reason: str


@dataclass(frozen=True)
class CprAckObservation:
    """Fields copied from one physically decoded ACK at an overhearing relay."""

    receiver: int
    sender: int
    flow_id: int
    request_id: int
    origin: int
    final_dst: int
    path: Tuple[int, ...]
    path_index: int
    repair_index: Optional[int]
    app_payload: bool = False


@dataclass(frozen=True)
class CprPendingRelay:
    """A relay's exact pending FLOOD request and its wire identity."""

    relay: int
    origin: int
    final_dst: int
    flow_id: int
    request_id: int
    repair_index: Optional[int]
    path: Tuple[int, ...]
    pending: Any


@dataclass
class CprFlowRecord:
    """Bounded source-local lifecycle for one CPR application flow."""

    flow_id: int
    source: int
    destination: int
    enqueue_at: float
    deadline: float
    initial_action: Optional[str] = None
    initial_path: Tuple[int, ...] = ()
    route_generation: Optional[int] = None
    initial_route_epoch: int = 0
    recovery_route_epoch: Optional[int] = None
    initial_started_at: Optional[float] = None
    repeat_requested: bool = False
    repeat_started_at: Optional[float] = None
    recovery_requested: bool = False
    recovery_started_at: Optional[float] = None
    acked_at: Optional[float] = None


class CprRelayLedger:
    """Bounded local ledger for ACK-terminated pending FLOOD relays."""

    def __init__(
        self, *, max_records: int = 8, max_hops: int = 8,
        evict_pending: bool = True,
    ) -> None:
        if max_records <= 0 or max_hops <= 0:
            raise ValueError("relay ledger bounds must be positive")
        self.max_records = max_records
        self.max_hops = max_hops
        self.evict_pending = bool(evict_pending)
        self._records: "OrderedDict[Tuple[int, int, int, int, Optional[int]], CprPendingRelay]" = OrderedDict()

    @staticmethod
    def _key(record: CprPendingRelay) -> Tuple[int, int, int, int, Optional[int]]:
        return (
            record.relay,
            record.origin,
            record.flow_id,
            record.request_id,
            record.repair_index,
        )

    def enroll(self, record: CprPendingRelay) -> Tuple[CprPendingRelay, ...]:
        key = self._key(record)
        self._records.pop(key, None)
        self._records[key] = record
        relay_keys = [key for key in self._records if key[0] == record.relay]
        evicted_records = []
        while len(relay_keys) > self.max_records:
            evicted_key = relay_keys.pop(0)
            evicted = self._records.pop(evicted_key)
            if self.evict_pending and not evicted.pending.committed:
                evicted.pending.canceled = True
            evicted_records.append(evicted)
        return tuple(evicted_records)

    def cancel_for_ack(self, *, relay: int, ack: CprAckObservation) -> bool:
        """Cancel only a matching, still-uncommitted pending request."""

        if ack.app_payload or ack.flow_id <= 0:
            return False
        if ack.request_id != ack.flow_id:
            return False
        if ack.repair_index not in {None, 1, 2}:
            return False
        path = tuple(ack.path)
        if not 2 <= len(path) <= self.max_hops + 1:
            return False
        if len(set(path)) != len(path):
            return False
        if path[0] != ack.final_dst or path[-1] != ack.origin:
            return False
        if not 0 <= ack.path_index < len(path) - 1:
            return False
        if path[ack.path_index + 1] != ack.sender:
            return False
        if relay in path:
            return False

        key = (relay, ack.final_dst, ack.flow_id, ack.request_id, ack.repair_index)
        record = self._records.get(key)
        if record is None:
            return False
        if (
            record.origin != ack.final_dst
            or record.final_dst != ack.origin
            or record.repair_index != ack.repair_index
            or record.pending.canceled
            or record.pending.committed
        ):
            return False
        record.pending.canceled = True
        del self._records[key]
        return True

    def retire(self) -> None:
        """Drop handles that can no longer be canceled."""

        for key, record in tuple(self._records.items()):
            if record.pending.canceled or record.pending.committed:
                del self._records[key]


def _fits(now: float, duration_s: float, deadline: float) -> bool:
    """Return whether a nonzero action can finish by the original deadline."""

    return now < deadline and now + duration_s <= deadline


def choose_recovery_action(observation: CprObservation) -> CprDecision:
    """Choose the next CPR recovery action from local physical state.

    The ordering is deliberately strict: a repeat gets the first opportunity;
    one flood is permitted only after a started repeat remains unacknowledged.
    """

    if observation.flow_acked:
        return CprDecision(CprAction.DROP_DEADLINE_INFEASIBLE, "already-acked")
    if observation.recovery_started:
        return CprDecision(
            CprAction.DROP_DEADLINE_INFEASIBLE,
            "recovery-already-started",
        )
    if not observation.repeat_started:
        if _fits(observation.now, observation.route_bound_s, observation.deadline):
            return CprDecision(CprAction.R_REPEAT, "repeat-fits-before-flood")
        return CprDecision(
            CprAction.DROP_DEADLINE_INFEASIBLE,
            "repeat-deadline-infeasible",
        )
    if _fits(observation.now, observation.flood_bound_s, observation.deadline):
        return CprDecision(CprAction.F_RECOVERY, "recovery-fits-after-repeat")
    return CprDecision(
        CprAction.DROP_DEADLINE_INFEASIBLE,
        "recovery-deadline-infeasible",
    )
