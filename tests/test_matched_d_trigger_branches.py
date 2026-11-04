"""Public tests for the matched D-trigger D/R/F diagnostic."""

from __future__ import annotations

import copy

from lora_mesh_sim import Node
from tools.run_sr_experiment import SrCase
from tools.diagnose_matched_d_trigger import MatchedSimulator


def _case() -> SrCase:
    return SrCase(
        key="synthetic", nodes=4, area_m=40.0, duration_s=240.0,
        rate_per_min=1.0, pair_mode="random", pair_count=0,
        shadow_sigma_db=0.0, temporal_fading_sigma_db=0.0,
    )


def test_reference_d_trigger_opens_d_r_f_branches_from_one_prefix():
    from tools.diagnose_matched_d_trigger import run_trace

    result = run_trace(
        _case(), 17,
        [Node(i, i * 10.0, 0.0) for i in range(4)],
        [(1.0, 0, 3, 1), (3.0, 0, 3, 2), (200.0, 0, 3, 3)],
    )

    assert [target["flow_id"] for target in result["eligible_targets"]] == [3]
    rows = {row["arm"]: row for row in result["branches"]}
    assert set(rows) == {"D", "R", "F"}
    assert all(row["prefix_match"] for row in rows.values())
    assert rows["D"]["initial_source_kind"] == "DATA"
    assert rows["R"]["initial_source_kind"] == "DATA"
    assert rows["F"]["initial_source_kind"] == "FLOOD"
    assert all(row["discovery_ledger_equalized"] for row in rows.values())


def test_cold_d_has_no_fabricated_r_branch():
    from tools.diagnose_matched_d_trigger import run_trace

    class DropEarlyAcks(MatchedSimulator):
        def try_receive(self, tx, receiver):
            if (tx.packet.flow_id in {1, 2} and tx.packet.kind == "ACK"
                    and receiver == 0):
                return None
            return super().try_receive(tx, receiver)

    result = run_trace(
        _case(), 17,
        [Node(i, i * 10.0, 0.0) for i in range(4)],
        [(1.0, 0, 3, 1), (3.0, 0, 3, 2), (200.0, 0, 3, 3)],
        cold_target=True,
        simulator_cls=DropEarlyAcks,
    )

    target = result["eligible_targets"][0]
    assert target["d_trigger_kind"] == "cold"
    assert {row["arm"] for row in result["branches"]} == {"D", "F"}


def test_cli_declares_new_matched_d_cohorts():
    from tools.diagnose_matched_d_trigger import (
        EXPLORATORY_SEEDS, SMOKE_SEEDS, parse_args,
    )

    assert parse_args(["--split", "smoke", "--out-prefix", "x"]).seeds == SMOKE_SEEDS
    assert parse_args(["--split", "exploratory", "--out-prefix", "x"]).seeds == EXPLORATORY_SEEDS


def test_validation_requires_raw_flow_and_action_evidence():
    from tools.diagnose_matched_d_trigger import _validate_result, run_trace

    result = run_trace(
        _case(), 17,
        [Node(i, i * 10.0, 0.0) for i in range(4)],
        [(1.0, 0, 3, 1), (3.0, 0, 3, 2), (200.0, 0, 3, 3)],
    )
    _validate_result(result)
    broken = copy.deepcopy(result)
    broken["branches"][0]["raw_physical_tx"] = None
    try:
        _validate_result(broken)
    except ValueError as error:
        assert "raw physical TX" in str(error)
    else:
        raise AssertionError("missing raw physical evidence was accepted")


def test_d_arm_validation_allows_a_discovery_timeout_fallback_flood():
    from tools.diagnose_matched_d_trigger import _validate_result, run_trace

    result = run_trace(
        _case(), 17,
        [Node(i, i * 10.0, 0.0) for i in range(4)],
        [(1.0, 0, 3, 1), (3.0, 0, 3, 2), (200.0, 0, 3, 3)],
    )
    fallback = copy.deepcopy(result)
    d_row = next(row for row in fallback["branches"] if row["arm"] == "D")
    d_row["initial_source_kind"] = "FLOOD"
    _validate_result(fallback)
