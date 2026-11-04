# Reproducing the SECON 2027 research package

Status: P0 foundation verified; pilot and formal evaluation pending. This file will be completed with final immutable plan IDs and commands. Existing ICC/historical result directories are not repaired-protocol evidence.

## Environments

The simulator and evidence runner use Python standard library only. P0 runs and142 frozen tests used `/usr/bin/python3` (Python3.9, pytest8.4.2); analysis uses Python3.14.8, NumPy2.5.3 and Matplotlib3.11.2. The event priority, physical model, common environment generator and all imported local modules are bound by snapshot hashes. `requirements.txt` applies to simulation only; analysis dependencies are stated separately.

## Immutable P0 input and results

`artifacts/secon2027/p0-tested-2.1.27-evidence.tar.gz` contains all21 runs, complete flow/action/request/TX/RX/ACK/identity files, their plan, snapshot, seed registration and audit/test evidence. Its SHA256 is `eebec9050dfd2f31933fe2293275eb827f78e888c8554756ab86df5ab358493d`; its adjacent index covers887 member names, sizes and SHA256 values. The archive includes superseded unexecuted plans as history.

Extract in a new clean directory, preserving relative paths, then use the extracted saved runner to audit its matching plan. Do not overwrite another result tree. Example from the directory holding `results/` and `configs/` after extraction:

```bash
python3 - <<'PYTHON'
import json, sys
from pathlib import Path
root = Path.cwd()
plan_path = root / "results/secon2027/plans/p0-smoke-v3.json"
plan = json.loads(plan_path.read_text())
sys.path.insert(0, str(root / plan["snapshot_path"] / "source"))
from tools.secon2027_experiment import audit_plan
report = audit_plan(plan_path, root)
assert report["status"] == "complete"
assert len(report["completed"]) == 21
print("21 verified completed runs; no simulation executed")
PYTHON
```

The independent supervisor performed this exact style of clean restore audit successfully; member verification and result appear in `docs/research/secon2027_supervisor_archive_restore.json`. Promoted VERSION2.1.28 does not relabel the original tested2.1.27 artifacts.

## Execution and resume semantics

The supported research entry point is `tools/secon2027_experiment.py`: `freeze` binds registered seeds, contract, matrix and complete source; `run` executes only planned keys in a saved-source subprocess; `audit` reads and recomputes the complete evidence. `run` on a completed key verifies and skips it, and tampered packages fail. No implicit new seed is selected.

A crashed process leaves its lock/attempt. `recover --plan ... --run-key ... --reason ...` checks that parent and worker processes are dead, validates their planned identities, preserves failure/lock evidence, and permits an explicit infrastructure retry within the frozen limit. Scientific failure cannot be reclassified to fill a batch. Exposed development seeds are not fresh validation seeds.

## Interpretation

P0 smoke validates mechanics only: all48 CPR/control flows were cold F_INITIAL, so it does not establish repeat/recovery effectiveness. All main performance conclusions require the separately frozen full matrix. Four model names refer to the implementations documented in baseline_fidelity; they do not establish official firmware or RF superiority.
