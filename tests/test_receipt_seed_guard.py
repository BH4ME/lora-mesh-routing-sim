"""Reserved receipt-screen seeds cannot bypass the staged diagnostic."""

import hashlib
import json
from dataclasses import asdict

import pytest

from tools import run_sr_experiment as sr
from tools import diagnose_first_hop_receipt_screen as receipt


@pytest.mark.parametrize("seed", (45000, 45001, 45020))
@pytest.mark.parametrize("protocol", (
    "meshecho-dhr-flood-ack-delay", "meshtastic-like",
))
def test_generic_runner_blocks_receipt_screen_seeds_before_topology(
    monkeypatch, seed, protocol,
):
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )

    with pytest.raises(ValueError, match="receipt.*reserved seed"):
        sr.run_one_sr(sr.SR_CASES["recurring_fading"], protocol, seed, 30.0)


@pytest.mark.parametrize("seed", (45000, 45001, 45020))
def test_imported_token_alone_cannot_start_reserved_receipt_seed(
    monkeypatch, seed,
):
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )

    with pytest.raises(ValueError, match="authorization"):
        sr.run_one_sr(
            sr.SR_CASES["recurring_fading"], receipt.PROTOCOL, seed, 30.0,
            research_authorization=receipt._RUNNER_AUTHORIZATION,
        )
    with pytest.raises(ValueError, match="authorization"):
        receipt.run_diagnostic(
            seed, research_authorization=receipt._RUNNER_AUTHORIZATION,
        )


@pytest.mark.parametrize("seed", (45000, 45001))
def test_invalid_stage_file_cannot_start_reserved_receipt_seed(
    tmp_path, monkeypatch, seed,
):
    stage_file = tmp_path / "receipt.authorization.json"
    stage_file.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )

    with pytest.raises(ValueError, match="authorization"):
        sr.run_one_sr(
            sr.SR_CASES["recurring_fading"], receipt.PROTOCOL, seed, 30.0,
            research_authorization=receipt._RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_file,
        )
    with pytest.raises(ValueError, match="authorization"):
        receipt.run_diagnostic(
            seed, research_authorization=receipt._RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_file,
        )


def test_changed_frozen_input_in_permit_fails_before_topology(
    tmp_path, monkeypatch,
):
    case = sr.SR_CASES["recurring_fading"]
    input_sha256 = receipt._source_hashes()
    input_sha256["tools/run_sr_experiment.py"] = "0" * 64
    permit = {
        "mode": "smoke",
        "seeds": list(receipt.SMOKE_SEEDS),
        "protocol": receipt.PROTOCOL,
        "case_sha256": receipt._sha256_json(asdict(case)),
        "application_deadline_s": 30.0,
        "input_sha256": input_sha256,
        "prerequisite_manifest_sha256": {},
    }
    stage_file = tmp_path / "smoke.authorization.json"
    stage_file.write_text(json.dumps(permit), encoding="utf-8")
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )

    with pytest.raises(ValueError, match="authorization differs from frozen"):
        sr.run_one_sr(
            case, receipt.PROTOCOL, 45000, 30.0,
            research_authorization=receipt._RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_file,
        )
    with pytest.raises(ValueError, match="authorization differs from frozen"):
        receipt.run_diagnostic(
            45000, research_authorization=receipt._RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_file,
        )


def test_direct_explore_runner_audits_predecessor_before_topology(
    tmp_path, monkeypatch,
):
    smoke_manifest = tmp_path / "smoke.manifest.json"
    smoke_manifest.write_text("{}\n", encoding="utf-8")
    (tmp_path / "smoke.manifest.sha256").write_text(
        "invalid sidecar\n", encoding="ascii",
    )
    case = sr.SR_CASES["recurring_fading"]
    permit = {
        "mode": "explore",
        "seeds": list(receipt.EXPLORATORY_SEEDS),
        "protocol": receipt.PROTOCOL,
        "case_sha256": receipt._sha256_json(asdict(case)),
        "application_deadline_s": 30.0,
        "input_sha256": receipt._source_hashes(),
        "prerequisite_manifest_sha256": {
            "smoke_manifest": hashlib.sha256(smoke_manifest.read_bytes()).hexdigest(),
        },
    }
    stage_file = tmp_path / "explore.authorization.json"
    stage_file.write_text(json.dumps(permit), encoding="utf-8")
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )

    with pytest.raises(ValueError, match="manifest SHA-256 sidecar"):
        sr.run_one_sr(
            case, receipt.PROTOCOL, 45001, 30.0,
            research_authorization=receipt._RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_file,
            smoke_manifest_path=smoke_manifest,
        )
    with pytest.raises(ValueError, match="manifest SHA-256 sidecar"):
        receipt.run_diagnostic(
            45001, research_authorization=receipt._RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_file,
            smoke_manifest_path=smoke_manifest,
        )


def test_float_alias_cannot_select_a_reserved_seed(monkeypatch):
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )
    with pytest.raises(ValueError, match="authorization"):
        sr.run_one_sr(
            sr.SR_CASES["recurring_fading"], receipt.PROTOCOL, 45000.0, 30.0,
            research_authorization=receipt._RUNNER_AUTHORIZATION,
        )
