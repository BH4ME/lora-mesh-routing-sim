"""Persisted DBR evidence must retain its frozen experiment identity."""

from __future__ import annotations

import hashlib
import json
import pytest

from tools import run_dbr_experiment as dbr
from tools.run_sr_experiment import SrCase


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    case = SrCase(
        key="recurring_fading", nodes=4, area_m=1000.0,
        duration_s=10.0, rate_per_min=6.0, pair_mode="random",
        pair_count=0, max_hops=3,
    )
    monkeypatch.setitem(dbr.sr.SR_CASES, "recurring_fading", case)
    monkeypatch.setitem(dbr.SEEDS_BY_MODE, "smoke", (73,))
    contract = tmp_path / "frozen.md"
    contract.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", contract)
    permit = {
        "mode": "smoke",
        "seeds": [73],
        "protocols": list(dbr.ARMS),
        "case_sha256": dbr._case_hash(case),
        "application_deadline_s": 30.0,
        "input_sha256": dbr.input_hashes(),
        "prerequisite_manifest_sha256": {},
    }
    permit_path = tmp_path / "smoke.authorization.json"
    permit_path.write_text(json.dumps(permit), encoding="utf-8")
    output_dir = tmp_path / "evidence"
    dbr.run_experiment(
        mode="smoke", seeds=(73,), case=case, deadline_s=30.0,
        stage_authorization_path=permit_path, output_dir=output_dir,
    )
    return output_dir, case


def _write_json(path, data):
    path.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")


def _reseal_authorization(output_dir, manifest, authorization):
    path = output_dir / "authorization.json"
    _write_json(path, authorization)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["artifact_sha256"]["authorization.json"] = digest
    manifest["stage_authorization_sha256"] = digest
    _write_json(output_dir / "manifest.json", manifest)


def _reseal_runs(output_dir, runs):
    def records(name):
        return [json.loads(line) for line in
                (output_dir / name).read_text(encoding="utf-8").splitlines()]

    flows = records("flows.jsonl")
    actions = records("actions.jsonl")
    transmissions = records("transmissions.jsonl")
    for run in runs:
        key = (run["seed"], run["protocol"])
        replay = {
            **{name: value for name, value in run.items()
               if name != "strict_replay_sha256"},
            "flows": [flow for flow in flows
                      if (flow["seed"], flow["protocol"]) == key],
            "actions": [action for action in actions
                        if (action["seed"], action["protocol"]) == key],
            "transmissions": [
                {name: value for name, value in tx.items()
                 if name not in {"seed", "protocol"}}
                for tx in transmissions
                if (tx["seed"], tx["protocol"]) == key
            ],
        }
        run["strict_replay_sha256"] = hashlib.sha256(json.dumps(
            replay, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
    path = output_dir / "runs.jsonl"
    path.write_text(
        "".join(json.dumps(run, sort_keys=True) + "\n" for run in runs),
        encoding="utf-8",
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["runs.jsonl"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    _write_json(manifest_path, manifest)


def test_resealed_manifest_cannot_claim_an_unknown_stage(evidence):
    output_dir, _case = evidence
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    authorization = json.loads(
        (output_dir / "authorization.json").read_text(encoding="utf-8")
    )
    manifest["mode"] = authorization["mode"] = "custom"
    _reseal_authorization(output_dir, manifest, authorization)

    with pytest.raises(ValueError, match="mode|stage"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_resealed_manifest_must_preserve_the_frozen_arm_order(evidence):
    output_dir, _case = evidence
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    authorization = json.loads(
        (output_dir / "authorization.json").read_text(encoding="utf-8")
    )
    swapped = list(reversed(dbr.ARMS))
    manifest["protocols"] = authorization["protocols"] = swapped
    _reseal_authorization(output_dir, manifest, authorization)

    with pytest.raises(ValueError, match="protocol|arm"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_resealed_manifest_requires_integer_reserved_seed_identity(evidence):
    output_dir, _case = evidence
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    authorization = json.loads(
        (output_dir / "authorization.json").read_text(encoding="utf-8")
    )
    manifest["seeds"] = authorization["seeds"] = [73.0]
    _reseal_authorization(output_dir, manifest, authorization)

    with pytest.raises(ValueError, match="seed"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_resealed_manifest_cannot_change_the_frozen_case(evidence):
    output_dir, _case = evidence
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    authorization = json.loads(
        (output_dir / "authorization.json").read_text(encoding="utf-8")
    )
    manifest["case"]["area_m"] += 1.0
    authorization["case_sha256"] = dbr._case_hash(SrCase(**manifest["case"]))
    _reseal_authorization(output_dir, manifest, authorization)

    with pytest.raises(ValueError, match="case"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_resealed_manifest_cannot_change_the_frozen_deadline(evidence):
    output_dir, _case = evidence
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    authorization = json.loads(
        (output_dir / "authorization.json").read_text(encoding="utf-8")
    )
    manifest["application_deadline_s"] = 31.0
    authorization["application_deadline_s"] = 31.0
    _reseal_authorization(output_dir, manifest, authorization)

    with pytest.raises(ValueError, match="manifest deadline"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_resealed_row_protocol_must_match_its_run_wrapper(evidence):
    output_dir, _case = evidence
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    runs[0]["row"]["protocol"] = dbr.ARMS[1]
    _reseal_runs(output_dir, runs)

    with pytest.raises(ValueError, match="row.*protocol|wrapper"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_resealed_row_seed_must_match_its_run_wrapper(evidence):
    output_dir, _case = evidence
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    runs[0]["row"]["seed"] = 74
    _reseal_runs(output_dir, runs)

    with pytest.raises(ValueError, match="row.*seed|wrapper"):
        dbr.audit_artifacts(output_dir / "manifest.json")


@pytest.mark.parametrize("field", ("run", "row"))
def test_resealed_run_and_row_seeds_must_remain_integers(evidence, field):
    output_dir, _case = evidence
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    target = runs[0] if field == "run" else runs[0]["row"]
    target["seed"] = 73.0
    _reseal_runs(output_dir, runs)

    with pytest.raises(ValueError, match="seed"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_resealed_row_case_must_match_the_frozen_case(evidence):
    output_dir, _case = evidence
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    runs[0]["row"]["case"] = "other"
    _reseal_runs(output_dir, runs)

    with pytest.raises(ValueError, match="row.*case"):
        dbr.audit_artifacts(output_dir / "manifest.json")


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("case_config_sha256", "0" * 64),
        ("generation_horizon_s", 11.0),
        ("application_deadline_s", 31.0),
        ("drain_until_s", 41.0),
    ],
)
def test_resealed_row_timing_and_case_digest_match_the_manifest(
    evidence, field, forged,
):
    output_dir, _case = evidence
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    runs[0]["row"][field] = forged
    _reseal_runs(output_dir, runs)

    with pytest.raises(ValueError, match="row.*(case|horizon|deadline|drain)"):
        dbr.audit_artifacts(output_dir / "manifest.json")
