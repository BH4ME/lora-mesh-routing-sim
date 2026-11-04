"""Contract tests for the independent CPR smoke artifact runner."""

import json
from pathlib import Path

import pytest

from tools import run_cpr_experiment as cpr


def _refresh_artifact_hash(paths, manifest_path, key):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][key]["sha256"] = cpr._file_sha256(paths[key])
    manifest["artifacts"][key]["records"] = sum(
        1 for line in paths[key].read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def test_cpr_smoke_matrix_pairs_fresh_arms_and_audits_artifacts(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_test",
        nodes=4,
        area_m=80.0,
        duration_s=20.0,
        pair_count=2,
        pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92000,), deadline_s=30.0, split="smoke")

    assert bundle.protocols == cpr.CPR_PROTOCOLS
    assert len(bundle.runs) == len(cpr.CPR_PROTOCOLS)
    assert len(bundle.flows) == 2 * len(cpr.CPR_PROTOCOLS)
    assert all(
        row["scheduled_trace_sha256"] == bundle.runs[0]["scheduled_trace_sha256"]
        for row in bundle.runs
    )

    paths = cpr.write_artifacts(tmp_path / "cpr_smoke", bundle)
    manifest = cpr.audit_artifacts(paths["manifest"])
    assert manifest["schema"] == cpr.SCHEMA
    assert manifest["counts"]["rx_attempts"] > 0
    assert manifest["contract_path"] == "docs/research/meshecho_cpr_smoke_contract_20261006.md"
    assert manifest["sim_version"] == (cpr.VERSION_PATH).read_text(encoding="utf-8").strip()
    assert all(row["seed_split"] == "smoke" for row in bundle.runs)


def test_cpr_artifacts_bind_to_explicit_contract_path(tmp_path: Path):
    contract = tmp_path / "exploratory_contract.md"
    contract.write_text("exploratory contract v1\n", encoding="utf-8")
    case = cpr.CprCase(
        key="cpr_contract_path", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(
        case, seeds=(92004,), deadline_s=30.0, split="custom",
        contract_path=contract,
    )
    assert bundle.contract_path == contract
    paths = cpr.write_artifacts(tmp_path / "contract_bound", bundle)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["contract_sha256"] == cpr._file_sha256(contract)
    assert cpr.audit_artifacts(paths["manifest"])["contract_path"] == str(contract)


def test_cpr_audit_accepts_multihop_reverse_path_ack(tmp_path: Path):
    bundle = cpr.run_matrix(cpr.CprCase(), seeds=(92024,), deadline_s=30.0)
    paths = cpr.write_artifacts(tmp_path / "multihop_ack", bundle)
    assert cpr.audit_artifacts(paths["manifest"])["counts"]["accepted_acks"] > 0


def test_cpr_exposure_profile_is_repeated_and_fading():
    case = cpr.CASE_PROFILES["exposure"]
    assert case.pair_schedule == "poisson"
    assert case.rate_per_min == 8.0
    assert case.duration_s == 240.0
    assert case.temporal_fading_sigma_db == 6.0
    assert case.temporal_fading_interval_s == 60.0
    assert case.pair_count == 4


def test_cpr_runner_preserves_confirmatory_split_metadata(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_split", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92005,), split="development")
    assert bundle.split == "development"
    paths = cpr.write_artifacts(tmp_path / "development_stage", bundle)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["experiment_stage"] == "development"
    assert manifest["seed_split"] == "development"
    assert all(row["seed_split"] == "development" for row in bundle.runs)
    assert manifest["gates"] == {
        "mechanical_smoke": False, "development": False, "holdout": False,
    }


def test_cpr_source_hashes_cover_runtime_dependency_and_version():
    hashes = cpr._source_hashes()
    assert "meshecho_utility.py" in hashes
    assert "VERSION" in hashes


def test_cpr_audit_rejects_duplicate_accepted_ack_attempt(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_duplicate_ack", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92001,), deadline_s=30.0, split="smoke")
    paths = cpr.write_artifacts(tmp_path / "duplicate_ack", bundle)
    rows = [
        json.loads(line) for line in paths["acks"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    accepted = next(row for row in rows if row.get("accepted"))
    rows.append(dict(accepted))
    paths["acks"].write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = paths["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["accepted_acks"] += 1
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _refresh_artifact_hash(paths, manifest_path, "acks")

    with pytest.raises(ValueError, match="duplicate accepted CPR ACK"):
        cpr.audit_artifacts(manifest_path)


def test_cpr_audit_rejects_ack_marker_without_started_matching_packet(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_marker_join", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92002,), deadline_s=30.0, split="smoke")
    paths = cpr.write_artifacts(tmp_path / "marker_join", bundle)
    rows = [
        json.loads(line) for line in paths["acks"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    accepted = next(row for row in rows if row.get("accepted"))
    accepted["repair_index"] = 1 if accepted.get("repair_index") != 1 else 2
    paths["acks"].write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = paths["manifest"]
    _refresh_artifact_hash(paths, manifest_path, "acks")

    with pytest.raises(ValueError, match="accepted CPR ACK marker/TX mismatch"):
        cpr.audit_artifacts(manifest_path)


def test_cpr_audit_rejects_started_action_without_matching_decision(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_action_join", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92003,), deadline_s=30.0, split="smoke")
    paths = cpr.write_artifacts(tmp_path / "action_join", bundle)
    rows = [
        json.loads(line) for line in paths["actions"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    target = next(
        row for row in rows
        if row.get("protocol") == "meshecho-cpr"
        and row.get("event") == "decision"
        and row.get("action") in {"R_INITIAL", "F_INITIAL"}
    )
    rows.remove(target)
    paths["actions"].write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = paths["manifest"]
    _refresh_artifact_hash(paths, manifest_path, "actions")

    with pytest.raises(ValueError, match="CPR started request lacks action decision"):
        cpr.audit_artifacts(manifest_path)


def test_runner_requires_explicit_seeds():
    with pytest.raises(ValueError, match="explicit seeds"):
        cpr.run_matrix(cpr.CprCase())


def test_failed_export_retains_partial_evidence_and_prevents_overwrite(tmp_path, monkeypatch):
    bundle = cpr.run_matrix(cpr.CprCase(nodes=4, area_m=80, duration_s=20, pair_count=2), seeds=(92000,))
    original = cpr._write_jsonl
    def fail_after_first(path, rows):
        if str(path).endswith(".actions.jsonl"):
            raise OSError("injected writer failure")
        return original(path, rows)
    monkeypatch.setattr(cpr, "_write_jsonl", fail_after_first)
    prefix = tmp_path / "failed"
    with pytest.raises(OSError, match="injected"):
        cpr.write_artifacts(prefix, bundle)
    assert Path(f"{prefix}.flows.jsonl").exists()
    manifest = json.loads(Path(f"{prefix}.manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert "flows" in manifest["partial_artifacts"]
    with pytest.raises(FileExistsError):
        cpr.write_artifacts(prefix, bundle)
    with pytest.raises(ValueError, match="not completed"):
        cpr.audit_artifacts(Path(f"{prefix}.manifest.json"))


def test_source_root_audit_checks_runtime_helper_closure(tmp_path):
    import shutil
    bundle = cpr.run_matrix(cpr.CprCase(nodes=4, area_m=80, duration_s=20, pair_count=2), seeds=(92000,))
    paths = cpr.write_artifacts(tmp_path / "snapshot", bundle)
    frozen = tmp_path / "frozen"
    for name in bundle.source_sha256:
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cpr.ROOT / name, target)
    assert "tools/run_drc_experiment.py" in bundle.source_sha256
    assert cpr.audit_artifacts(paths["manifest"], source_root=frozen)["status"] == "completed"
    with (frozen / "tools/run_drc_experiment.py").open("a") as handle:
        handle.write("\n# changed helper\n")
    with pytest.raises(ValueError, match="source hash"):
        cpr.audit_artifacts(paths["manifest"], source_root=frozen)


def test_audit_detects_ack_provenance_removed_even_when_hashes_updated(tmp_path):
    bundle = cpr.run_matrix(cpr.CprCase(nodes=4, area_m=80, duration_s=20, pair_count=2),
                            protocols=("meshtastic",), seeds=(92000,), registry=cpr.EXTERNAL_REGISTRY)
    paths = cpr.write_artifacts(tmp_path / "missing_ack", bundle)
    assert bundle.acks
    paths["acks"].write_text("")
    _refresh_artifact_hash(paths, paths["manifest"], "acks")
    manifest = json.loads(paths["manifest"].read_text())
    manifest["counts"]["accepted_acks"] = 0
    paths["manifest"].write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="flow ACK lacks"):
        cpr.audit_artifacts(paths["manifest"])


def test_cutoff_preserves_future_queue_reservations_without_phantom_tx(tmp_path, monkeypatch):
    from lora_mesh_sim import RoutingProtocol, Packet
    class Burst(RoutingProtocol):
        name = "fixture-burst"
        def send_app(self, src, dst, flow_id):
            self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
            for _ in range(20):
                self.sim.transmit_later(src, Packet(kind="DATA", flow_id=flow_id,
                    origin=src, final_dst=dst, ttl=2, created_at=self.sim.now,
                    protocol=self.name, path=(src, dst)), 0)
        def on_receive(self, receiver, packet, rx):
            pass
    monkeypatch.setattr(cpr, "build_protocol", lambda *args: Burst())
    case = cpr.CprCase(nodes=2, area_m=80, duration_s=2, pair_count=1, sf=12)
    bundle = cpr.run_matrix(case, protocols=("fixture-burst",), seeds=(92000,), deadline_s=0.1,
                            registry={"fixture-burst": cpr.ProtocolSpec("fixture-burst")})
    row = bundle.runs[0]
    assert row["committed_future_start_count"] > 0
    assert row["in_flight_at_cutoff_count"] == 1
    assert len(bundle.transmissions) == row["started_request_count"] == 1
    assert row["tx_ledger_airtime_s"] == bundle.transmissions[0]["toa_s"]
    assert all(r["tx_id"] is None for r in bundle.requests if r["status"] == "committed_future_start")
    paths = cpr.write_artifacts(tmp_path / "cutoff", bundle)
    assert cpr.audit_artifacts(paths["manifest"])["status"] == "completed"


def test_parallel_exporters_cannot_share_output_prefix(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    bundle = cpr.run_matrix(cpr.CprCase(nodes=2, area_m=80, duration_s=20, pair_count=1), seeds=(92000,))
    prefix = tmp_path / "concurrent"
    def export():
        try:
            cpr.write_artifacts(prefix, bundle)
            return "completed"
        except FileExistsError:
            return "refused"
    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(lambda _: export(), range(2)))
    assert sorted(outcomes) == ["completed", "refused"]
    assert cpr.audit_artifacts(Path(f"{prefix}.manifest.json"))["status"] == "completed"


def test_audit_rejects_impossible_delivery_with_consistent_summary_and_hashes(tmp_path):
    import csv
    bundle = cpr.run_matrix(cpr.CprCase(nodes=4, area_m=80, duration_s=20, pair_count=2),
                            protocols=("meshtastic",), seeds=(92000,), registry=cpr.EXTERNAL_REGISTRY)
    paths = cpr.write_artifacts(tmp_path / "impossible_delivery", bundle)
    flows = [json.loads(line) for line in paths["flows"].read_text().splitlines()]
    target = flows[0]
    target["first_delivery_at"] = target["enqueued_at"] + 0.0001
    target["delivery_by_deadline"] = True
    target["late_delivery"] = False
    paths["flows"].write_text("".join(json.dumps(row) + "\n" for row in flows))
    with paths["runs"].open(newline="") as handle:
        reader = csv.DictReader(handle)
        runs, fields = list(reader), reader.fieldnames
    total = sum(bool(row["delivery_by_deadline"]) for row in flows)
    runs[0]["delivery_by_deadline"] = total
    runs[0]["delivery_pdr_deadline"] = total / len(flows)
    with paths["runs"].open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(runs)
    manifest = json.loads(paths["manifest"].read_text())
    for key in ("flows", "runs"):
        manifest["artifacts"][key]["sha256"] = cpr._file_sha256(paths[key])
    paths["manifest"].write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="delivery lacks matching physical"):
        cpr.audit_artifacts(paths["manifest"])


def test_t9_queue_reserved_until_t20_has_zero_physical_cost_at_t10(tmp_path, monkeypatch):
    from lora_mesh_sim import RoutingProtocol, Packet
    class QueuedPair(RoutingProtocol):
        name = "fixture-queued-pair"
        def send_app(self, src, dst, flow_id):
            self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
            self.sim.nodes[src].tx_available_at = 20.0
            for kind in ("DATA", "ACK"):
                self.sim.transmit_later(src, Packet(kind=kind, flow_id=flow_id,
                    origin=src, final_dst=dst, ttl=2, created_at=self.sim.now,
                    protocol=self.name, path=(src, dst), app_payload=kind == "DATA"), 0)
        def on_receive(self, receiver, packet, rx):
            pass
    monkeypatch.setattr(cpr, "build_protocol", lambda *args: QueuedPair())
    monkeypatch.setattr(cpr, "_schedule_traffic", lambda sim, case, pairs, seed:
                        sim.schedule(9.0, "app_send", (pairs[0][0], pairs[0][1], 1)))
    case = cpr.CprCase(nodes=2, area_m=80, duration_s=9.5, pair_count=1, sf=7)
    bundle = cpr.run_matrix(case, protocols=("fixture-queued-pair",), seeds=(92000,), deadline_s=0.5,
                            registry={"fixture-queued-pair": cpr.ProtocolSpec("fixture-queued-pair")})
    row = bundle.runs[0]
    assert row["drain_until_s"] == 10.0
    assert row["committed_future_start_count"] == 2
    assert row["legacy_reserved_tx_count"] == 2
    assert row["legacy_reserved_ack_tx"] == 1
    assert row["legacy_reserved_total_airtime_s"] > 0
    for name in ("tx_count", "data_tx", "control_tx", "ack_tx", "total_airtime_s", "tx_energy_j",
                 "rx_energy_j", "total_energy_j", "started_request_count", "tx_ledger_airtime_s",
                 "channel_busy_time_s", "channel_busy_ratio"):
        assert row[name] == 0, name
    assert row["airtime_per_deadline_delivery_s"] is None
    assert bundle.transmissions == bundle.rx_attempts == []
    paths = cpr.write_artifacts(tmp_path / "t9_t10_t20", bundle)
    assert cpr.audit_artifacts(paths["manifest"])["status"] == "completed"
