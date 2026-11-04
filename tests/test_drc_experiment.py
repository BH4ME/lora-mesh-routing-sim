from __future__ import annotations

import json

import pytest

from tools import run_drc_experiment as drc


def _smoke_case() -> drc.DrcCase:
    return drc.DrcCase(
        key="line-smoke",
        nodes=2,
        area_m=10.0,
        duration_s=8.0,
        pair_count=1,
        pair_schedule="fixed-once",
        payload_bytes=8,
        shadow_sigma_db=0.0,
        temporal_fading_sigma_db=0.0,
        tx_power_dbm=20.0,
        path_loss_exp=2.0,
        max_hops=3,
    )


def test_drc_smoke_emits_all_evidence_tables_and_physical_joins(tmp_path):
    case = _smoke_case()
    bundle = drc.run_matrix(
        case,
        drc.DRC_PROTOCOLS,
        (91001,),
        deadline_s=30.0,
        split="smoke",
    )

    assert len(bundle.runs) == len(drc.DRC_PROTOCOLS)
    assert bundle.protocols == drc.DRC_PROTOCOLS
    assert bundle.flows
    assert bundle.requests
    assert bundle.transmissions
    assert bundle.rx_attempts
    assert bundle.acks

    paths = drc.write_artifacts(tmp_path / "drc-smoke", bundle)
    expected = {"runs", "paired", "flows", "actions", "requests", "tx",
                "rx_attempts", "acks", "manifest"}
    assert set(paths) == expected
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["schema"] == "meshecho-drc-evidence-v1"
    assert manifest["gates"]["mechanical_smoke"] is True
    assert manifest["event_priority"] == {
        "tx_end": 0,
        "app_send": 1,
        "protocol_timer": 1,
        "flow_timeout": 1,
        "tx_request": 2,
    }
    assert manifest["counts"]["invalid_records"] == 0
    assert manifest["counts"]["spillover_tx"] == 0
    assert manifest["counts"]["incomplete_rx_tx"] == 0
    drc.audit_artifacts(paths["manifest"])

    for arm in drc.DRC_PROTOCOLS:
        tx_ids = {
            row["tx_id"] for row in bundle.transmissions
            if row["protocol"] == arm
        }
        started = [
            row for row in bundle.requests
            if row["protocol"] == arm and row["status"] == "started"
        ]
        assert started
        assert len(started) == len(tx_ids)
        assert {row["tx_id"] for row in started} == tx_ids
        assert all(row["cutoff_class"] == "before_cutoff" for row in bundle.transmissions if row["protocol"] == arm)
    assert all(row["tx_request_id"] is not None for row in started)
    assert all(row["toa_s"] == pytest.approx(row["end"] - row["start"])
               for row in bundle.transmissions)
    accepted = [row for row in bundle.acks if row["accepted"]]
    assert accepted
    assert all(row["ack_rx_at"] == row["accepted_at"] for row in accepted)
    assert all(row["deadline_at"] is not None for row in accepted)
    assert all(row["route_generation_after"] is not None for row in accepted)
    success = {
        row["rx_attempt_id"]: row
        for row in bundle.rx_attempts
        if row["reason"] == "success" and row["decoded"]
    }
    assert all(row["ack_rx_attempt_id"] in success for row in accepted)


def test_drc_audit_fails_closed_when_request_artifact_is_tampered(tmp_path):
    bundle = drc.run_matrix(_smoke_case(), drc.DRC_PROTOCOLS, (91002,), split="smoke")
    paths = drc.write_artifacts(tmp_path / "drc-tamper", bundle)
    lines = paths["requests"].read_text(encoding="utf-8").splitlines()
    changed = json.loads(lines[0])
    changed["status"] = "started" if changed["status"] != "started" else "canceled"
    lines[0] = json.dumps(changed, sort_keys=True, separators=(",", ":"))
    paths["requests"].write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact hash|request|join"):
        drc.audit_artifacts(paths["manifest"])


def test_stream_matrix_writes_and_audits_without_in_memory_bundle(tmp_path):
    case = _smoke_case()
    paths_prefix = tmp_path / "drc-stream"
    streamed = drc.write_artifacts_stream(
        paths_prefix,
        case,
        drc.DRC_PROTOCOLS,
        (91004,),
        30.0,
        "custom",
        drc.iter_matrix(case, drc.DRC_PROTOCOLS, (91004,), 30.0, "custom"),
    )

    assert len(streamed.runs) == len(drc.DRC_PROTOCOLS)
    assert len(streamed.paired) == len(drc.DRC_PROTOCOLS) - 1
    assert streamed.paths["rx_attempts"].exists()
    manifest = json.loads(streamed.paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["seed_split"] == "custom"
    assert manifest["counts"]["runs"] == len(drc.DRC_PROTOCOLS)
    drc.audit_artifacts(streamed.paths["manifest"])


def test_stream_writer_removes_partial_artifacts_on_matrix_failure(tmp_path):
    case = _smoke_case()

    def broken_results():
        yield from drc.iter_matrix(case, drc.DRC_PROTOCOLS, (91005,), 30.0, "custom")
        yield from drc.iter_matrix(case, drc.DRC_PROTOCOLS, (91005,), 30.0, "custom")

    prefix = tmp_path / "drc-broken-stream"
    with pytest.raises(ValueError, match="duplicate|matrix"):
        drc.write_artifacts_stream(
            prefix, case, drc.DRC_PROTOCOLS, (91005,), 30.0, "custom", broken_results()
        )
    assert not any(path.exists() for path in drc.artifact_paths(prefix).values())


def test_drc_matrix_rejects_duplicate_seed_and_unknown_arm():
    case = _smoke_case()
    with pytest.raises(ValueError, match="duplicates"):
        drc.run_matrix(case, drc.DRC_PROTOCOLS, (91003, 91003), split="smoke")
    with pytest.raises(ValueError, match="unknown DRC arm"):
        drc.run_matrix(case, ("meshecho-drc-unknown",), (91003,), split="smoke")
