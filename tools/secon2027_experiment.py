#!/usr/bin/env python3
"""Freeze, execute and audit registered SECON experiments without replacing evidence."""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX_SCHEMA = "secon2027-matrix-v1"
PLAN_SCHEMA = "secon2027-frozen-plan-v1"
SNAPSHOT_SCHEMA = "secon2027-source-snapshot-v1"
METHOD_FILES = ("lora_mesh_sim.py", "meshecho_cpr.py", "meshecho_drc.py", "meshecho_utility.py",
                "tools/run_cpr_experiment.py", "tools/run_drc_experiment.py", "tools/secon2027_scenarios.py")
EVIDENCE_SUFFIXES = ("runs.csv", "paired.csv", "summary.csv", "flows.jsonl", "actions.jsonl",
                     "requests.jsonl", "transmissions.jsonl", "rx_attempts.jsonl", "acks.jsonl",
                     "identities.json", "manifest.json")
REQUIRED_ATTEMPT_FILES = {"started.json", "worker_runtime.json", "stdout.log", "stderr.log", "worker_audit.json", "evidence.lock"} | {
    "evidence." + suffix for suffix in EVIDENCE_SUFFIXES}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with tmp.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def under(root: Path, rel: str) -> Path:
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError(f"expected safe repository-relative path: {rel}")
    result = (root / rel).resolve()
    if root.resolve() not in result.parents:
        raise ValueError(f"path escapes repository: {rel}")
    return result


def closed_fields(value: dict, allowed: set, required: set, label: str) -> None:
    extra = set(value) - allowed
    missing = required - set(value)
    if extra or missing:
        raise ValueError(f"{label}: unknown={sorted(extra)}, missing={sorted(missing)}")


def validate_matrix(matrix: dict) -> None:
    fields = {"schema", "experiment_id", "stage", "cohort_id", "seeds", "contract_path",
              "cases", "arms", "statistics", "budget", "failure_policy", "development_gate"}
    closed_fields(matrix, fields, fields - {"development_gate"}, "matrix")
    if matrix["schema"] != MATRIX_SCHEMA or matrix["stage"] not in {"development", "validation"}:
        raise ValueError("unsupported schema/stage")
    if not matrix["experiment_id"] or not matrix["cohort_id"]:
        raise ValueError("experiment/cohort ids required")
    seeds = matrix["seeds"]
    if not seeds or len(set(seeds)) != len(seeds) or any(type(x) is not int or x < 0 for x in seeds):
        raise ValueError("seeds must be explicit, unique nonnegative integers")
    if not matrix["cases"] or not matrix["arms"]:
        raise ValueError("cases and arms required")
    if matrix["failure_policy"] != {"max_attempts": 2, "retry": "infrastructure-only-explicit", "missing": "report-incomplete"}:
        raise ValueError("failure policy must preserve failures and forbid silent exclusions")
    for kind in ("cases", "arms"):
        ids = [x["id"] for x in matrix[kind]]
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate {kind} IDs")
    for case in matrix["cases"]:
        closed_fields(case, {"id", "scenario", "configuration", "case", "environment", "deadline_s", "arms"},
                      {"id", "scenario", "configuration", "case", "environment", "deadline_s"}, "case")
        if case["configuration"] not in {"default", "matched", "robustness", "smoke"} or case["deadline_s"] <= 0:
            raise ValueError("invalid configuration/deadline")
        if "arms" in case and (not case["arms"] or set(case["arms"]) - {x["id"] for x in matrix["arms"]}):
            raise ValueError("case arms must be a nonempty subset of declared arms")
    for arm in matrix["arms"]:
        closed_fields(arm, {"id", "protocol", "parameters"}, {"id", "protocol", "parameters"}, "arm")
        if not isinstance(arm["parameters"], dict):
            raise ValueError("arm parameters must be explicit mapping")
    if matrix["statistics"].get("unit") != "seed":
        raise ValueError("statistics unit must be seed")
    if matrix["stage"] == "validation" and not matrix.get("development_gate"):
        raise ValueError("validation requires a completed development gate")


@contextlib.contextmanager
def registry_edit(path: Path):
    # File lock serializes short registry transitions; the run lock covers execution.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        registry = read(path)
        yield registry
        atomic_json(path, registry)


def source_inventory(root: Path, contract_path: str) -> dict:
    paths = list(root.glob("*.py"))
    for directory in ("tools", "tests"):
        paths.extend((root / directory).rglob("*.py"))
    paths.extend(root / x for x in ("VERSION", "requirements.txt", contract_path))
    if (root / "README.md").is_file():
        paths.append(root / "README.md")
    # Keep historical contract dependencies used by the unchanged regression APIs.
    paths.extend((root / "docs/research").glob("*contract*.md"))
    schema = root / "configs/secon2027/matrix.schema.json"
    if schema.exists():
        paths.append(schema)
    result = {}
    for path in sorted(set(paths)):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"source input missing or symlink: {path}")
        result[path.relative_to(root).as_posix()] = {"sha256": sha(path), "bytes": path.stat().st_size}
    return result


def freeze_source(root: Path, destination: Path, contract_path: str) -> dict:
    inventory = source_inventory(root, contract_path)
    snapshot_id = digest(inventory)
    target = destination / snapshot_id
    descriptor = {"schema": SNAPSHOT_SCHEMA, "snapshot_id": snapshot_id, "files": inventory,
                  "tested_version": (root / "VERSION").read_text().strip(), "created_at": now(),
                  "python": sys.version, "platform": platform.platform()}
    if target.exists():
        verify_snapshot(target)
        return read(target / "snapshot.json")
    target.mkdir(parents=True, exist_ok=False)
    for rel in inventory:
        output = under(target / "source", rel)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, output)
    write_new(target / "snapshot.json", descriptor)
    verify_snapshot(target)
    return descriptor


def verify_snapshot(path: Path) -> dict:
    descriptor = read(path / "snapshot.json")
    if descriptor.get("schema") != SNAPSHOT_SCHEMA or digest(descriptor["files"]) != descriptor["snapshot_id"]:
        raise ValueError("invalid source snapshot identity")
    for rel, expected in descriptor["files"].items():
        file = under(path / "source", rel)
        if not file.is_file() or sha(file) != expected["sha256"] or file.stat().st_size != expected["bytes"]:
            raise ValueError(f"source snapshot mismatch: {rel}")
    actual = {p.relative_to(path / "source").as_posix() for p in (path / "source").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts}
    if actual != set(descriptor["files"]):
        raise ValueError("source snapshot has extra/untracked files")
    if descriptor["tested_version"] != (path / "source/VERSION").read_text().strip():
        raise ValueError("snapshot tested_version differs from saved VERSION")
    return descriptor


def generate_runs(matrix: dict, snapshot_id: str) -> list:
    runs = []
    config_sha = digest(matrix)
    for case in matrix["cases"]:
        for arm in matrix["arms"]:
            if "arms" in case and arm["id"] not in case["arms"]:
                continue
            for seed in matrix["seeds"]:
                identity = {"cohort_id": matrix["cohort_id"], "config_sha256": config_sha,
                            "source_snapshot": snapshot_id, "case_id": case["id"], "arm_id": arm["id"], "seed": seed}
                runs.append({"run_key": digest(identity), **identity, "case": case, "arm": arm})
    return runs


def freeze(matrix_path: Path, registry_path: Path, root: Path, output: Path) -> dict:
    matrix = read(matrix_path)
    validate_matrix(matrix)
    if output.exists():
        raise FileExistsError(output)
    sys.path.insert(0, str(root))
    from tools import run_cpr_experiment as cpr
    from tools import secon2027_scenarios as scenarios
    for case in matrix["cases"]:
        # Reject unknown physical/config arguments before any seed can become exposed.
        resolved_case = cpr.CprCase(**case["case"])
        scenarios.resolve_environment(resolved_case, matrix["seeds"][0], case["environment"])
        if case["scenario"] not in {"P0-smoke", "S1", "S2", "S3", "R-deadline", "R-scale"}:
            raise ValueError("unrecognized scenario")
    for arm in matrix["arms"]:
        cpr.validate_parameters(arm["protocol"], arm["parameters"])
    gate = None
    with registry_edit(registry_path) as registry:
        cohort = registry["cohorts"].get(matrix["cohort_id"])
        if not cohort or cohort["purpose"] != matrix["stage"] or set(matrix["seeds"]) != set(cohort["seeds"]):
            raise ValueError("matrix must exactly bind a registered cohort/purpose/seeds")
        if cohort["status"] not in {"reserved", "running", "exposed"}:
            raise ValueError("retired cohort cannot freeze new plans")
        cohort.setdefault("seed_states", {str(seed): cohort["status"] for seed in cohort["seeds"]})
        for seed in matrix["seeds"]:
            if any(x["start"] <= seed <= x["end"] for x in registry["exclusions"]):
                raise ValueError("seed in historical exclusion namespace")
            for other_id, other in registry["cohorts"].items():
                if other_id != matrix["cohort_id"] and seed in other["seeds"]:
                    raise ValueError("seed already belongs to another cohort")
        if matrix["stage"] == "validation":
            if cohort["status"] != "reserved" or cohort.get("plans"):
                raise ValueError("validation can be frozen only once before exposure")
            gate = read(under(root, matrix["development_gate"]))
            if gate.get("status") != "passed" or not gate.get("method_frozen") or not gate.get("pilot_budget"):
                raise ValueError("development gate lacks passed method and measured pilot budget")
            if gate.get("method_source_sha256") != {rel: sha(root / rel) for rel in METHOD_FILES}:
                raise ValueError("method differs from development gate")
            pilot_audit = audit_plan(under(root, gate["pilot_plan_path"]), root)
            if pilot_audit["status"] != "complete" or pilot_audit["plan_sha256"] != gate["pilot_plan_sha256"]:
                raise ValueError("development pilot is incomplete or not the gated plan")
            pilot_plan = verify_plan(under(root, gate["pilot_plan_path"]), root)
            if pilot_plan["matrix"]["stage"] != "development" or not {"S1", "S2", "S3"}.issubset({c["scenario"] for c in pilot_plan["matrix"]["cases"]}):
                raise ValueError("development gate must refer to three-scenario pilot")
            required_coverage = {(scenario, regime, protocol, seed)
                                 for scenario in ("S1", "S2", "S3") for regime in ("default", "matched")
                                 for protocol in ("meshecho-cpr", "meshecho", "meshtastic", "meshcore")
                                 for seed in pilot_plan["matrix"]["seeds"]}
            coverage = {(r["case"]["scenario"], r["case"]["configuration"], r["arm"]["protocol"], r["seed"])
                        for r in pilot_plan["runs"]}
            if not required_coverage.issubset(coverage):
                raise ValueError("development pilot lacks four-model default/matched coverage")
            pilot_source = under(root, pilot_plan["snapshot_path"]) / "source"
            if gate["method_source_sha256"] != {rel: sha(pilot_source / rel) for rel in METHOD_FILES}:
                raise ValueError("development pilot tested a different method")
            measured_seconds = sum(item["wall_seconds"] for item in pilot_audit["completed"])
            budget = gate["pilot_budget"]
            if (gate["method_frozen"] is not True or not isinstance(budget, dict)
                    or budget.get("completed_runs") != len(pilot_audit["completed"])
                    or abs(budget.get("total_wall_seconds", -1) - measured_seconds) > 1e-6):
                raise ValueError("development gate budget is not measured from the pilot")
        snapshot = freeze_source(root, root / "results/secon2027/snapshots", matrix["contract_path"])
        runs = generate_runs(matrix, snapshot["snapshot_id"])
        plan = {"schema": PLAN_SCHEMA, "frozen_at": now(), "matrix": matrix,
                "matrix_sha256": digest(matrix), "source_snapshot": snapshot["snapshot_id"],
                "snapshot_path": f"results/secon2027/snapshots/{snapshot['snapshot_id']}",
                "registry_path": registry_path.relative_to(root).as_posix(),
                "contract_sha256": sha(under(root, matrix["contract_path"])),
                "tested_version": snapshot["tested_version"], "runs": runs,
                "development_gate_evidence": gate}
        plan["plan_sha256"] = digest(plan)
        write_new(output, plan)
        record = {"status": "active", "plan_path": output.relative_to(root).as_posix(), "plan_sha256": plan["plan_sha256"],
                  "config_sha256": plan["matrix_sha256"], "source_snapshot": snapshot["snapshot_id"], "frozen_at": plan["frozen_at"]}
        cohort.setdefault("plans", []).append(record)
        cohort["planned_run_keys"] = list(dict.fromkeys(cohort.get("planned_run_keys", []) + [r["run_key"] for r in runs]))
        cohort["source_snapshot"] = snapshot["snapshot_id"]
        cohort["config_sha256"] = plan["matrix_sha256"]
    return plan


def verify_plan(path: Path, root: Path) -> dict:
    plan = read(path)
    expected = plan.pop("plan_sha256", None)
    if digest(plan) != expected or plan.get("schema") != PLAN_SCHEMA:
        raise ValueError("frozen plan hash/schema mismatch")
    plan["plan_sha256"] = expected
    validate_matrix(plan["matrix"])
    if digest(plan["matrix"]) != plan["matrix_sha256"]:
        raise ValueError("matrix hash mismatch")
    snapshot = verify_snapshot(under(root, plan["snapshot_path"]))
    if snapshot["snapshot_id"] != plan["source_snapshot"] or generate_runs(plan["matrix"], snapshot["snapshot_id"]) != plan["runs"]:
        raise ValueError("run-key plan mismatch")
    contract = under(under(root, plan["snapshot_path"]) / "source", plan["matrix"]["contract_path"])
    if sha(contract) != plan["contract_sha256"]:
        raise ValueError("contract hash mismatch")
    registry = read(under(root, plan["registry_path"]))
    cohort = registry["cohorts"][plan["matrix"]["cohort_id"]]
    if (cohort["purpose"] != plan["matrix"]["stage"] or set(cohort["seeds"]) != set(plan["matrix"]["seeds"])
            or cohort["status"] not in {"reserved", "running", "exposed"}
            or any(cohort.get("seed_states", {}).get(str(seed)) not in {"reserved", "running", "exposed"}
                   for seed in plan["matrix"]["seeds"])):
        raise ValueError("cohort purpose/seeds/status no longer authorizes this plan")
    if not any(x["plan_sha256"] == expected and x.get("status", "active") == "active" for x in cohort.get("plans", [])):
        raise ValueError("unregistered frozen plan")
    if set(r["run_key"] for r in plan["runs"]) - set(cohort["planned_run_keys"]):
        raise ValueError("unregistered planned run keys")
    return plan


@contextlib.contextmanager
def run_lock(root: Path, run_key: str):
    path = root / "results/secon2027/run_state" / (run_key + ".lock")
    write_new(path, {"pid": os.getpid(), "hostname": socket.gethostname(), "started_at": now(), "run_key": run_key})
    try:
        yield
    finally:
        path.unlink()  # only this holder created the file; crash leaves it for explicit inspection


def mark_exposed(root: Path, plan: dict, spec: dict, attempt: Path) -> None:
    with registry_edit(under(root, plan["registry_path"])) as registry:
        cohort = registry["cohorts"][plan["matrix"]["cohort_id"]]
        cohort["status"] = "exposed"
        cohort["first_run_at"] = cohort.get("first_run_at") or now()
        cohort.setdefault("seed_states", {})[str(spec["seed"])] = "exposed"
        cohort.setdefault("artifacts", []).append(attempt.relative_to(root).as_posix())
        cohort.setdefault("execution_history", []).append({"run_key": spec["run_key"], "attempt": attempt.name, "event": "started", "at": now()})


def audit_attempt(path: Path, *, spec: dict = None, plan: dict = None, source_root: Path = None, record: dict = None) -> dict:
    record = read(path / "completion.json") if record is None else record
    if record.get("status") != "completed":
        raise ValueError(f"attempt incomplete: {path}")
    if set(record.get("files", {})) != REQUIRED_ATTEMPT_FILES:
        raise ValueError("completion must bind the exact required evidence file set")
    for rel, expected in record["files"].items():
        if not under(path, rel).is_file() or sha(under(path, rel)) != expected:
            raise ValueError(f"artifact tampered: {path / rel}")
    started = read(path / "started.json")
    saved_spec = started.get("spec")
    if not isinstance(saved_spec, dict) or not saved_spec.get("run_key"):
        raise ValueError("started record has no planned spec")
    spec = saved_spec if spec is None else spec
    if saved_spec != spec or record.get("run_key") != spec["run_key"]:
        raise ValueError("completion/started run identity mismatch")
    if record.get("source_snapshot") != spec["source_snapshot"] or record.get("plan_sha256") != started.get("plan_sha256"):
        raise ValueError("completion source/plan mismatch")
    runtime = read(path / "worker_runtime.json")
    if runtime.get("run_key") != spec["run_key"] or runtime.get("plan_sha256") != started["plan_sha256"]:
        raise ValueError("worker runtime identity mismatch")
    if plan is not None and (spec not in plan["runs"] or record["plan_sha256"] != plan["plan_sha256"]
                             or record["source_snapshot"] != plan["source_snapshot"] or record["tested_version"] != plan["tested_version"]):
        raise ValueError("completion differs from frozen plan")
    manifest = read(path / "evidence.manifest.json")
    if (manifest.get("status") != "completed" or manifest.get("seeds") != [spec["seed"]]
            or manifest.get("protocols") != [spec["arm"]["protocol"]]
            or manifest.get("case", {}).get("key") != spec["case"]["case"]["key"]
            or manifest.get("deadline_s") != spec["case"]["deadline_s"]
            or manifest.get("common_environment") != spec["case"]["environment"]
            or manifest.get("protocol_parameter_overrides") != {spec["arm"]["protocol"]: spec["arm"]["parameters"]}):
        raise ValueError("raw manifest differs from planned run")
    if any(manifest["case"].get(key) != value for key, value in spec["case"]["case"].items()):
        raise ValueError("manifest case parameters differ from planned run")
    if plan is not None and (manifest["contract_sha256"] != plan["contract_sha256"] or manifest["sim_version"] != plan["tested_version"]):
        raise ValueError("manifest contract/version mismatch")
    with (path / "evidence.runs.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    observed = read(path / "worker_audit.json")
    if (len(rows) != 1 or observed.get("status") != "passed" or observed != record.get("audit")
            or int(rows[0]["seed"]) != spec["seed"] or rows[0]["protocol"] != spec["arm"]["protocol"]
            or rows[0]["case"] != spec["case"]["case"]["key"]):
        raise ValueError("raw row or worker audit differs from planned run")
    if {k: str(v) if v is not None else "" for k, v in observed["row"].items()} != rows[0]:
        raise ValueError("worker metric row differs from raw CSV")
    if source_root is not None:
        command = [sys.executable, str(source_root / "tools/secon2027_experiment.py"), "_audit_worker",
                   "--attempt", str(path.resolve())]
        checked = subprocess.run(command, cwd=source_root, capture_output=True, text=True)
        if checked.returncode:
            raise ValueError(f"frozen independent event audit failed: {checked.stderr[-3000:]}")
    return record


def execute_one(plan_path: Path, root: Path, spec: dict, retry: bool = False) -> dict:
    plan = verify_plan(plan_path, root)
    if spec not in plan["runs"]:
        raise ValueError("run is not in frozen plan")
    run_dir = root / "results/secon2027/runs" / spec["run_key"]
    with run_lock(root, spec["run_key"]):
        run_dir.mkdir(parents=True, exist_ok=True)
        attempts = sorted(run_dir.glob("attempt-*"))
        complete = [p for p in attempts if (p / "completion.json").exists()]
        if complete:
            if len(complete) != 1:
                raise ValueError("multiple completed attempts for one run key")
            source = under(root, plan["snapshot_path"]) / "source"
            return {**audit_attempt(complete[0], spec=spec, plan=plan, source_root=source), "status": "verified-existing"}
        if attempts:
            if not retry or len(attempts) >= plan["matrix"]["failure_policy"]["max_attempts"]:
                raise ValueError("failed/pending attempt retained; explicit bounded infrastructure retry required")
            last = read(attempts[-1] / "failure.json")
            if last.get("kind") != "infrastructure":
                raise ValueError("scientific/correctness failure requires a new development round, not retry")
        attempt = run_dir / f"attempt-{len(attempts) + 1:03d}"
        attempt.mkdir(exist_ok=False)
        write_new(attempt / "started.json", {"status": "running", "spec": spec, "plan_sha256": plan["plan_sha256"],
                                           "started_at": now(), "pid": os.getpid(), "python": sys.version})
        mark_exposed(root, plan, spec, attempt)
        source = under(root, plan["snapshot_path"]) / "source"
        command = [sys.executable, str(source / "tools/secon2027_experiment.py"), "_worker", "--plan", str(plan_path.resolve()),
                   "--attempt", str(attempt.resolve()), "--run-key", spec["run_key"]]
        started = time.monotonic()
        try:
            with (attempt / "stdout.log").open("x") as stdout, (attempt / "stderr.log").open("x") as stderr:
                process = subprocess.run(command, cwd=source, stdout=stdout, stderr=stderr, env={**os.environ, "PYTHONHASHSEED": "0"})
            if process.returncode:
                raise RuntimeError(f"frozen worker failed with return code {process.returncode}")
            metrics = read(attempt / "worker_audit.json")
            files = {p.relative_to(attempt).as_posix(): sha(p) for p in sorted(attempt.iterdir()) if p.is_file()}
            record = {"status": "completed", "run_key": spec["run_key"], "source_snapshot": plan["source_snapshot"],
                      "tested_version": plan["tested_version"], "plan_sha256": plan["plan_sha256"],
                      "completed_at": now(), "wall_seconds": time.monotonic() - started, "files": files, "audit": metrics}
            audit_attempt(attempt, spec=spec, plan=plan, source_root=source, record=record)
            write_new(attempt / "completion.json", record)
            with registry_edit(under(root, plan["registry_path"])) as registry:
                registry["cohorts"][plan["matrix"]["cohort_id"]].setdefault("execution_history", []).append(
                    {"run_key": spec["run_key"], "attempt": attempt.name, "event": "completed", "at": now()})
            return record
        except BaseException as error:
            write_new(attempt / "failure.json", {"status": "failed", "kind": "infrastructure" if isinstance(error, OSError) else "scientific-or-worker", "failed_at": now(),
                                               "error": repr(error), "traceback": traceback.format_exc(), "elapsed_s": time.monotonic() - started})
            raise


def process_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def recover_interrupted(plan_path: Path, root: Path, run_key: str, reason: str) -> dict:
    """Retain a dead process's attempt and lock before permitting bounded retry."""
    if not reason.strip():
        raise ValueError("explicit infrastructure recovery reason required")
    plan = verify_plan(plan_path, root)
    spec = next((r for r in plan["runs"] if r["run_key"] == run_key), None)
    if spec is None:
        raise ValueError("unplanned recovery key")
    lock = root / "results/secon2027/run_state" / (run_key + ".lock")
    holder = read(lock)
    if holder.get("run_key") != run_key:
        raise ValueError("recovery lock run identity mismatch")
    if holder["hostname"] != socket.gethostname() or process_alive(holder["pid"]):
        raise ValueError("lock owner is alive or on another host; recovery refused")
    attempts = sorted((root / "results/secon2027/runs" / run_key).glob("attempt-*"))
    if not attempts:
        raise ValueError("lock without attempt requires manual incident inspection")
    attempt = attempts[-1]
    started = read(attempt / "started.json")
    if started.get("spec") != spec or started.get("plan_sha256") != plan["plan_sha256"]:
        raise ValueError("recovery started spec/plan identity mismatch")
    runtime_path = attempt / "worker_runtime.json"
    if runtime_path.exists():
        runtime = read(runtime_path)
        if runtime.get("run_key") != run_key or runtime.get("plan_sha256") != plan["plan_sha256"]:
            raise ValueError("recovery worker runtime identity mismatch")
        if runtime["hostname"] != socket.gethostname() or process_alive(runtime["pid"]):
            raise ValueError("frozen worker is still alive; recovery refused")
    # Also cover parent death between spawning worker and its runtime record.
    processes = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    for line in processes.splitlines():
        if "_worker" in line and "--run-key " + run_key in line and int(line.split(None, 1)[0]) != os.getpid():
            raise ValueError("matching frozen worker process still exists")
    if (attempt / "completion.json").exists():
        audit_attempt(attempt, spec=spec, plan=plan, source_root=under(root, plan["snapshot_path"]) / "source")
    elif not (attempt / "failure.json").exists():
        write_new(attempt / "failure.json", {"status": "failed", "kind": "infrastructure", "failed_at": now(),
                                           "error": "parent/worker process interrupted", "recovery_reason": reason})
    else:
        if read(attempt / "failure.json").get("kind") != "infrastructure":
            raise ValueError("scientific failure cannot be reclassified as infrastructure")
    recovery = {"at": now(), "reason": reason, "run_key": run_key, "prior_lock": holder,
                "completed_preserved": (attempt / "completion.json").exists()}
    archive = root / "results/secon2027/recoveries" / run_key
    archive.mkdir(parents=True, exist_ok=True)
    write_new(archive / (attempt.name + ".json"), recovery)
    os.rename(lock, archive / (attempt.name + ".lock"))
    return recovery


def worker(plan_path: Path, attempt: Path, run_key: str) -> None:
    # This entry point must execute from the saved source tree, never the mutable checkout.
    outer_root = ROOT.parents[4]
    plan = verify_plan(plan_path, outer_root)
    snapshot = verify_snapshot(ROOT.parent)
    if snapshot["snapshot_id"] != plan["source_snapshot"]:
        raise ValueError("worker not running requested frozen source")
    spec = next(x for x in plan["runs"] if x["run_key"] == run_key)
    started = read(attempt / "started.json")
    if started["spec"] != spec or started["plan_sha256"] != plan["plan_sha256"]:
        raise ValueError("worker started spec differs from frozen plan")
    write_new(attempt / "worker_runtime.json", {"pid": os.getpid(), "hostname": socket.gethostname(),
                                              "started_at": now(), "run_key": run_key,
                                              "plan_sha256": plan["plan_sha256"]})
    sys.path.insert(0, str(ROOT))
    from tools import run_cpr_experiment as cpr
    case = cpr.CprCase(**spec["case"]["case"])
    bundle = cpr.run_matrix(case, (spec["arm"]["protocol"],), (spec["seed"],),
                            spec["case"]["deadline_s"], plan["matrix"]["stage"],
                            contract_path=ROOT / plan["matrix"]["contract_path"],
                            registry=cpr.EXTERNAL_REGISTRY, environment=spec["case"]["environment"],
                            protocol_parameters={spec["arm"]["protocol"]: spec["arm"]["parameters"]})
    paths = cpr.write_artifacts(attempt / "evidence", bundle)
    cpr.audit_artifacts(paths["manifest"], source_root=ROOT)
    audit = audit_bundle(bundle, spec)
    try:
        import resource
        audit["peak_rss_native"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        audit["peak_rss_unit"] = "bytes" if sys.platform == "darwin" else "KiB"
    except ImportError:
        pass
    write_new(attempt / "worker_audit.json", audit)


def audit_worker(attempt: Path) -> None:
    verify_snapshot(ROOT.parent)
    sys.path.insert(0, str(ROOT))
    from tools import run_cpr_experiment as cpr
    cpr.audit_artifacts(attempt / "evidence.manifest.json", source_root=ROOT)
    def records(suffix):
        return [json.loads(line) for line in (attempt / ("evidence." + suffix)).read_text().splitlines() if line]
    with (attempt / "evidence.runs.csv").open(newline="") as stream:
        raw = list(csv.DictReader(stream))
    def scalar(value):
        if value == "":
            return None
        if value in {"True", "False"}:
            return value == "True"
        try:
            return json.loads(value)
        except ValueError:
            return value
    bundle = SimpleNamespace(runs=[{k: scalar(v) for k, v in row.items()} for row in raw],
                             flows=records("flows.jsonl"), transmissions=records("transmissions.jsonl"),
                             acks=records("acks.jsonl"), rx_attempts=records("rx_attempts.jsonl"),
                             identities={int(k): v for k, v in read(attempt / "evidence.identities.json").items()})
    audit_bundle(bundle, read(attempt / "started.json")["spec"])


def audit_bundle(bundle: Any, spec: dict) -> dict:
    """Additional contract checks independent of legacy fixed-cohort acceptance gates."""
    flows = bundle.flows
    txs = bundle.transmissions
    acks = bundle.acks
    if len(bundle.runs) != 1:
        raise ValueError("each run key must have exactly one arm and seed")
    row = bundle.runs[0]
    if row["seed"] != spec["seed"] or row["protocol"] != spec["arm"]["protocol"]:
        raise ValueError("run arm/seed differs from planned identity")
    if len({x["flow_id"] for x in flows}) != len(flows):
        raise ValueError("duplicate scheduled flow")
    identity = bundle.identities[spec["seed"]]
    trace = identity["application_trace"]
    if {f["flow_id"] for f in flows} != {f["flow_id"] for f in trace} or len(flows) != len(trace):
        raise ValueError("scheduled denominator differs from application trace")
    if int(row["scheduled_unicast_flows"]) != len(flows):
        raise ValueError("aggregate denominator mismatch")
    by_flow = {f["flow_id"]: f for f in flows}
    by_tx = {tx["tx_id"]: tx for tx in txs}
    delivered_rx = {}
    for rx in bundle.rx_attempts:
        if not rx.get("decoded"):
            continue
        tx = by_tx.get(rx["tx_id"])
        if tx is not None and tx["packet_kind"] in {"DATA", "FLOOD", "FALLBACK"}:
            delivered_rx.setdefault((tx["flow_id"], rx["receiver"]), []).append((tx, rx))
    for item in trace:
        flow = by_flow[item["flow_id"]]
        if (flow["src"], flow["dst"]) != (item["src"], item["dst"]) or abs(flow["enqueued_at"] - item["time"]) > 1e-9:
            raise ValueError("flow identity differs from scheduled trace")
        if abs(flow["deadline_at"] - item["time"] - spec["case"]["deadline_s"]) > 1e-9:
            raise ValueError("flow deadline mismatch")
        if flow["first_delivery_at"] is not None:
            physical = [(tx, rx) for tx, rx in delivered_rx.get((flow["flow_id"], flow["dst"]), [])
                        if tx["origin"] == flow["src"] and tx["final_dst"] == flow["dst"]
                        and abs(rx["end"] - flow["first_delivery_at"]) <= 1e-9]
            eligible = []
            for tx, rx in physical:
                path, index = tx.get("path") or [], int(tx.get("path_index", -1))
                if not path or path[0] != flow["src"]:
                    continue
                if tx["packet_kind"] == "DATA" and path[-1] == flow["dst"]:
                    valid = (0 <= index < len(path) - 1 and index + 1 == len(path) - 1
                             and path[index] == tx["sender"])
                else:
                    valid = (tx["packet_kind"] in {"FLOOD", "FALLBACK"}
                             or tx["packet_kind"] == "DATA" and spec["arm"]["protocol"].startswith("meshtastic"))
                    valid = valid and path[-1] == tx["sender"] and flow["dst"] not in path
                if valid:
                    eligible.append((tx, rx))
            if not eligible:
                raise ValueError("destination delivery has no physical decoded data evidence")
        for time_key, flag in (("accepted_ack_at", "ack_by_deadline"), ("first_delivery_at", "delivery_by_deadline")):
            computed = flow[time_key] is not None and flow[time_key] <= flow["deadline_at"]
            if bool(flow[flag]) != computed:
                raise ValueError("deadline success flag mismatch")
    for flag, metric in (("ack_by_deadline", "ack_pdr_deadline"), ("delivery_by_deadline", "delivery_pdr_deadline")):
        count = sum(bool(f[flag]) for f in flows)
        if int(row[flag]) != count or abs(float(row[metric]) - count / len(flows)) > 1e-10:
            raise ValueError("per-seed success metric mismatch")
    accepted = [a for a in acks if a.get("accepted")]
    for f in flows:
        fid = f["flow_id"]
        confirmations = [a for a in accepted if a["flow_id"] == fid]
        acked = f.get("acked_at", f.get("acknowledged_at", f.get("accepted_ack_at")))
        if bool(acked is not None) != bool(confirmations):
            raise ValueError(f"ACK metric missing physical provenance for flow {fid}")
        if confirmations and abs(confirmations[0]["accepted_at"] - acked) > 1e-9:
            raise ValueError("accepted ACK timestamp differs from flow")
        if len(confirmations) > 1:
            raise ValueError(f"multiple accepted source ACKs for flow {fid}")
    if len({t["tx_id"] for t in txs}) != len(txs):
        raise ValueError("duplicate physical TX")
    if int(row["started_request_count"]) != len(txs):
        raise ValueError("started request/TX count mismatch")
    total = sum(t["end"] - t["start"] for t in txs)
    if abs(total - float(row["tx_ledger_airtime_s"])) > 1e-7:
        raise ValueError("physical airtime sum differs from row")
    if spec["arm"]["protocol"].startswith("meshecho-cpr"):
        for tx in txs:
            if len(tx["path"]) != len(set(tx["path"])):
                raise ValueError("CPR transmission carries looped path")
        source_counts = {}
        stage_counts = {}
        endpoints = {f["flow_id"]: f.get("src", f.get("source")) for f in flows}
        for tx in txs:
            if tx["sender"] == endpoints.get(tx["flow_id"]) and tx.get("packet_kind", tx.get("kind")) in {"DATA", "FLOOD"}:
                source_counts[tx["flow_id"]] = source_counts.get(tx["flow_id"], 0) + 1
                key = (tx["flow_id"], tx.get("repair_index"))
                stage_counts[key] = stage_counts.get(key, 0) + 1
                if (spec["arm"]["protocol"] == "meshecho-cpr-norepeat" and tx.get("repair_index") == 1
                        or spec["arm"]["protocol"] == "meshecho-cpr-norecovery" and tx.get("repair_index") == 2):
                    raise ValueError("disabled CPR stage physically transmitted")
        if any(v > 3 for v in source_counts.values()):
            raise ValueError("CPR source physical DATA/FLOOD budget exceeded")
        if any(v > 1 for v in stage_counts.values()):
            raise ValueError("CPR source transmitted a stage more than once")
        for flow in flows:
            if flow.get("initial_action") == "F_INITIAL" and source_counts.get(flow["flow_id"], 0) > 1:
                raise ValueError("cold CPR flow transmitted beyond its initial flood")
    return {"status": "passed", "scheduled_flows": len(flows), "transmissions": len(txs),
            "accepted_acks": len(accepted), "airtime_s": total, "row": row}


def audit_plan(plan_path: Path, root: Path) -> dict:
    plan = verify_plan(plan_path, root)
    completed, missing, failed = [], [], []
    for spec in plan["runs"]:
        path = root / "results/secon2027/runs" / spec["run_key"]
        attempts = sorted(path.glob("attempt-*"))
        success = [p for p in attempts if (p / "completion.json").exists()]
        if len(success) > 1:
            raise ValueError("multiple successes for same planned run")
        if success:
            record = audit_attempt(success[0], spec=spec, plan=plan, source_root=under(root, plan["snapshot_path"]) / "source")
            if record["source_snapshot"] != plan["source_snapshot"] or record["plan_sha256"] != plan["plan_sha256"]:
                raise ValueError("completion provenance mismatch")
            completed.append({"run_key": spec["run_key"], "attempt_path": success[0].relative_to(root).as_posix(),
                              "completion_sha256": sha(success[0] / "completion.json"), "wall_seconds": record["wall_seconds"]})
        elif attempts:
            failed.append(spec["run_key"])
        else:
            missing.append(spec["run_key"])
    return {"status": "complete" if not failed and not missing else "incomplete", "plan_sha256": plan["plan_sha256"],
            "expected_runs": len(plan["runs"]), "completed": completed, "failed": failed, "missing": missing,
            "audited_at": now()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze", help="validate and bind registered matrix to immutable source and run keys")
    f.add_argument("--matrix", type=Path, required=True)
    f.add_argument("--registry", type=Path, default=Path("configs/secon2027/seed_registry.json"))
    f.add_argument("--out", type=Path, required=True)
    for name in ("run", "audit"):
        p = sub.add_parser(name)
        p.add_argument("--plan", type=Path, required=True)
        if name == "run":
            p.add_argument("--run-key")
            p.add_argument("--retry-infrastructure", action="store_true")
        else:
            p.add_argument("--out", type=Path)
    w = sub.add_parser("_worker", help=argparse.SUPPRESS)
    w.add_argument("--plan", type=Path, required=True)
    w.add_argument("--attempt", type=Path, required=True)
    w.add_argument("--run-key", required=True)
    a = sub.add_parser("_audit_worker", help=argparse.SUPPRESS)
    a.add_argument("--attempt", type=Path, required=True)
    recovery = sub.add_parser("recover", help="preserve a dead worker attempt and release its stale run lock")
    recovery.add_argument("--plan", type=Path, required=True)
    recovery.add_argument("--run-key", required=True)
    recovery.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        plan = freeze(args.matrix.resolve(), args.registry.resolve(), ROOT, args.out.resolve())
        print(json.dumps({"plan_sha256": plan["plan_sha256"], "source_snapshot": plan["source_snapshot"], "runs": len(plan["runs"])}))
    elif args.command == "_worker":
        worker(args.plan, args.attempt, args.run_key)
    elif args.command == "_audit_worker":
        audit_worker(args.attempt)
    elif args.command == "recover":
        print(json.dumps(recover_interrupted(args.plan, ROOT, args.run_key, args.reason), indent=2))
    elif args.command == "run":
        plan = verify_plan(args.plan, ROOT)
        selected = [x for x in plan["runs"] if not args.run_key or x["run_key"] == args.run_key]
        if not selected:
            raise ValueError("unplanned run key")
        for i, spec in enumerate(selected, 1):
            result = execute_one(args.plan, ROOT, spec, retry=args.retry_infrastructure)
            print(json.dumps({"progress": [i, len(selected)], "run_key": spec["run_key"], "status": result["status"], "wall_seconds": result["wall_seconds"]}), flush=True)
    else:
        report = audit_plan(args.plan, ROOT)
        if args.out:
            write_new(args.out, report)
        print(json.dumps(report, indent=2))
        if report["status"] != "complete":
            raise SystemExit(2)


if __name__ == "__main__":
    main()
