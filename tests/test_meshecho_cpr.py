from __future__ import annotations

from meshecho_cpr import (
    CprAction,
    CprAckObservation,
    CprDecision,
    CprObservation,
    CprPendingRelay,
    CprRelayLedger,
    choose_recovery_action,
)


def test_cpr_uses_a_same_path_repeat_before_flood_recovery():
    decision = choose_recovery_action(
        CprObservation(
            now=10.0,
            deadline=30.0,
            route_bound_s=2.0,
            flood_bound_s=8.0,
            repeat_started=False,
        )
    )

    assert decision.action is CprAction.R_REPEAT
    assert decision.reason == "repeat-fits-before-flood"


def test_cpr_allows_one_flood_only_after_repeat_has_physically_started():
    decision = choose_recovery_action(
        CprObservation(
            now=20.0,
            deadline=30.0,
            route_bound_s=2.0,
            flood_bound_s=8.0,
            repeat_started=True,
        )
    )

    assert decision.action is CprAction.F_RECOVERY
    assert decision.reason == "recovery-fits-after-repeat"


class _Pending:
    def __init__(self, *, committed=False):
        self.canceled = False
        self.committed = committed


def test_cpr_cancels_only_a_matching_uncommitted_relay_after_physical_ack():
    pending = _Pending()
    ledger = CprRelayLedger(max_records=8)
    ledger.enroll(
        CprPendingRelay(
            relay=1,
            origin=0,
            final_dst=3,
            flow_id=7,
            request_id=7,
            repair_index=2,
            path=(0,),
            pending=pending,
        )
    )

    canceled = ledger.cancel_for_ack(
        relay=1,
        ack=CprAckObservation(
            receiver=1,
            sender=3,
            flow_id=7,
            request_id=7,
            origin=3,
            final_dst=0,
            path=(0, 3),
            path_index=0,
            repair_index=2,
        ),
    )

    assert canceled
    assert pending.canceled


def test_cpr_does_not_cancel_a_committed_or_mismatched_relay():
    pending = _Pending(committed=True)
    ledger = CprRelayLedger(max_records=8)
    ledger.enroll(
        CprPendingRelay(
            relay=1,
            origin=0,
            final_dst=3,
            flow_id=7,
            request_id=7,
            repair_index=2,
            path=(0,),
            pending=pending,
        )
    )

    wrong_flow = ledger.cancel_for_ack(
        relay=1,
        ack=CprAckObservation(
            receiver=1, sender=3, flow_id=8, request_id=8,
            origin=3, final_dst=0, path=(0, 3), path_index=0,
            repair_index=2,
        ),
    )
    committed = ledger.cancel_for_ack(
        relay=1,
        ack=CprAckObservation(
            receiver=1, sender=3, flow_id=7, request_id=7,
            origin=3, final_dst=0, path=(0, 3), path_index=0,
            repair_index=2,
        ),
    )

    assert not wrong_flow
    assert not committed
    assert not pending.canceled


def test_cpr_relay_ledger_can_evict_without_canceling_for_no_cancel_shadow():
    first = _Pending()
    second = _Pending()
    ledger = CprRelayLedger(max_records=1, evict_pending=False)
    ledger.enroll(
        CprPendingRelay(
            relay=1, origin=0, final_dst=3, flow_id=1, request_id=1,
            repair_index=2, path=(0,), pending=first,
        )
    )
    evicted = ledger.enroll(
        CprPendingRelay(
            relay=1, origin=0, final_dst=3, flow_id=2, request_id=2,
            repair_index=2, path=(0,), pending=second,
        )
    )

    assert len(evicted) == 1
    assert evicted[0].flow_id == 1
    assert not first.canceled
