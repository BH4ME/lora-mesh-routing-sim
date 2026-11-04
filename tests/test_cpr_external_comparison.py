from __future__ import annotations

from tools.run_cpr_external_comparison import run_comparison


def test_external_comparison_preserves_paired_trace_and_reports_both_baselines() -> None:
    result = run_comparison(
        case_profile="exposure",
        protocols=("meshecho-cpr", "meshtastic", "meshcore"),
        seeds=(92300,),
        split="custom",
    )

    assert [row["protocol"] for row in result.runs] == [
        "meshecho-cpr",
        "meshtastic",
        "meshcore",
    ]
    assert all(
        item["trace_match"] and item["topology_match"] and item["pair_pool_match"]
        for item in result.paired
    )
    assert {row["protocol"] for row in result.summary} == {
        "meshecho-cpr",
        "meshtastic",
        "meshcore",
    }


def test_external_comparison_defaults_to_four_protocol_family_matrix() -> None:
    result = run_comparison(case_profile="exposure", seeds=(92300,), split="custom")

    assert [row["protocol"] for row in result.runs] == [
        "meshecho-cpr",
        "meshecho",
        "meshtastic",
        "meshcore",
    ]
