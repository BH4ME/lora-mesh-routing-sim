# Reproducing the SECON 2027 research package

P0, the corrected 72-run development pilot, and all 760 frozen formal runs are complete. The complete formal source/event audit and raw-only statistical analysis passed. This guide distinguishes original raw evidence, subsequent analysis, and manuscript artifacts. Historical ICC results are not evidence for the corrected protocol. Final PDF and publication verification are recorded separately in the closeout evidence.

All commands below use paths relative to the repository or restored archive root. They preserve saved source and raw evidence. Choose a new output directory for every reproduction attempt; existing analysis directories and audit output files are not overwritten.

## Recorded environments

The simulator and evidence auditor require the Python standard library, including the Unix `fcntl` module. The recorded simulator and saved-source test environment is Python **3.9.6**. P0 used 142 frozen tests; the corrected pilot and formal freeze each used 161 frozen tests. The recorded test dependency is pytest **8.4.2**.

The corrected pilot's `results/secon2027/analysis/development-pilot-v2/analysis.json` records Python **3.9.6**, NumPy **1.26.4** and Matplotlib **3.7.5**. The completed formal analysis records the same observed versions in `results/secon2027/analysis/formal-v1/analysis.json`. Earlier analysis records that used Python 3.14.8, NumPy 2.5.3 and Matplotlib 3.11.2 retain their own provenance; they do not describe the corrected pilot.

`requirements.txt` covers simulation. Statistical analysis and plotting use the separately recorded dependencies. With `python3` resolving to Python 3.9.6, an isolated analysis environment can be prepared as follows:

```bash
python3 -m venv work/secon2027-repro-env
work/secon2027-repro-env/bin/python -m pip install \
  numpy==1.26.4 matplotlib==3.7.5 pytest==8.4.2
```

Do not install into a saved source tree or edit old artifacts to update dependencies. Event ordering, the physical model, the common environment generator and imported local modules are bound by source snapshot hashes.

## Evidence packages and source identities

| Stage | Preserved package | What is established |
| --- | --- | --- |
| P0 | `artifacts/secon2027/p0-tested-2.1.27-evidence.tar.gz` and its adjacent `.index.json` | All 21 mechanical runs, their saved source, plans, registry, raw events and audit/test evidence; 887 indexed files. |
| Failed pilot v1 | `artifacts/secon2027/pilot-v1-implementation-failure.tar.gz` and its adjacent `.index.json` | Original source and failed attempt; 48 completed, 1 implementation failure and 23 unstarted keys. This is not a complete paired result. |
| Corrected pilot v2 | `artifacts/secon2027/pilot-v2-tested-2.1.28-evidence.tar.gz` and its adjacent `.index.json` | All 72 corrected development runs, raw evidence, source, tests, analysis and diagnostics; 1,517 indexed files. |
| Formal registration | `artifacts/secon2027/formal-v1-before-exposure.tar.gz` and its adjacent `.index.json` | The 166 source inputs, prospective contract, 760 planned keys, 20 reserved seeds and saved test evidence before formal exposure; 177 indexed files, with no formal run results. |
| Completed formal evaluation | `artifacts/secon2027/formal-v1-raw-evidence.transport4m.tar.gz.part-001` through `114`, `.transport4m.parts.index.json`, and `.index.json` | All 760 original runs, 166 frozen source inputs, registry, plan, tests, dispatch and administrative records; 14,667 verified archive members. Later analysis and manuscript artifacts are distributed separately. |

The whole-file archive SHA-256 values are:

- P0: `eebec9050dfd2f31933fe2293275eb827f78e888c8554756ab86df5ab358493d`.
- Failed pilot v1: `2aaaf790ca67b05090a00aaeb3595f1f62a26cc663dabca5be4f20e492abdd1d`.
- Corrected pilot v2: `81e7222145e1689dc7dfeeff96264e57d33f250b5fb05a436fd2ec9e0a6df2b4`.
- Formal registration before exposure: `192abcf1f8119db3f9ac9b07b06f5761d0a0783f0c174e0e5897e62c27827742`.
- Complete formal raw archive: `81776e12501e56945dd8aad6a37bb68e5f6e4b41d66c88ae041e7689e490d067` (475,828,160 bytes).

The corrected pilot archive is 48,442,357 compressed bytes and restores 714,132,393 file bytes. An independent supervisor checked its exact member set and every member hash, then audited all 72 runs from a new directory using only its saved source. The audit returned `complete`, with zero failed or missing runs; all 72 saved audit workers exited successfully. The restored file inventory remained unchanged after audit. See `docs/research/secon2027_supervisor_pilot_archive_review.md` and its JSON evidence. The report also retains an earlier wrapper failure caused by the equivalent macOS `/var` and `/private/var` path spellings; the final successful attempt used a separate clean directory. The earlier local archive named `pilot-v2-evidence-before-report-closeout` is not the promoted pilot package.

P0 has a separate successful supervisor clean restore record at `docs/research/secon2027_supervisor_archive_restore.json`. Its superseded, unexecuted plans remain historical members of the archive. Promoting VERSION to 2.1.28 did not relabel P0's tested version 2.1.27.

## Restore an indexed archive

The standalone helper `artifacts/secon2027/reproduction_helpers/restore_evidence.py` requires only the standard library. It checks the whole archive hash and size, verifies every member against the index, rejects unsafe or duplicate paths, and creates a new destination directory. From the repository root, this example restores the verified corrected pilot:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  artifacts/secon2027/reproduction_helpers/restore_evidence.py \
  --archive artifacts/secon2027/pilot-v2-tested-2.1.28-evidence.tar.gz \
  --index artifacts/secon2027/pilot-v2-tested-2.1.28-evidence.index.json \
  --out work/restored-pilot-v2
```

The destination must not already exist. The same helper accepts the P0 or formal-before-exposure archive with its matching index. Restoring the formal-before-exposure package cannot produce completed formal results because that package deliberately contains no formal attempts.

Other standalone helpers in the same directory support evidence packaging, archive splitting, registered dispatch and formal mechanism inspection. They are separate reproduction utilities, not changes to the frozen simulation method. If a final archive is distributed as parts, concatenate them in the index's listed order and verify the whole hash before restoration. The current transport index `formal-v1-raw-evidence.transport4m.parts.index.json` lists 114 parts of at most 4 MiB and their hashes. The historical 11-part index remains available for the original restoration record; those larger parts are retained locally. From the repository root, reconstruct the original archive without overwriting an existing file:

```bash
mkdir -p work
set -C
cat artifacts/secon2027/formal-v1-raw-evidence.transport4m.tar.gz.part-* > work/formal-v1-raw-evidence.tar.gz
shasum -a 256 work/formal-v1-raw-evidence.tar.gz
PYTHONDONTWRITEBYTECODE=1 python3 \
  artifacts/secon2027/reproduction_helpers/restore_evidence.py \
  --archive work/formal-v1-raw-evidence.tar.gz \
  --index artifacts/secon2027/formal-v1-raw-evidence.index.json \
  --out work/restored-formal-v1
```

Use a new `work/` destination for reconstruction; the expected whole hash is above, and the restore helper enforces it before extraction. The zero-padded names have the same order as the parts index. The pre-exposure archive contains no formal outcomes and cannot substitute for these parts.

## Audit restored evidence with its saved source

Use the saved runner's Python API with an explicit evidence root. A saved script's default CLI root points at `snapshot/source`, which is not the restored archive root. This supported API avoids that path ambiguity and does not execute a simulator.

After restoring the pilot, run the following from `work/restored-pilot-v2`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PYTHON'
import json
import sys
from pathlib import Path

root = Path.cwd().resolve()
plan_path = root / "results/secon2027/plans/development-pilot-v2.json"
plan = json.loads(plan_path.read_text())
sys.path.insert(0, str(root / plan["snapshot_path"] / "source"))
from tools.secon2027_experiment import audit_plan

report = audit_plan(plan_path, root)
assert report["status"] == "complete"
assert len(report["completed"]) == 72
assert not report["failed"] and not report["missing"]
print("72 verified runs; no simulation executed")
PYTHON
```

For P0, use `results/secon2027/plans/p0-smoke-v3.json` and require 21 completed runs. Keep any wrapper or generated report outside `snapshot/source`; `PYTHONDONTWRITEBYTECODE=1` also prevents audit subprocesses from adding bytecode files to restored source.

The following complete-plan audit can be run from the full repository or a complete formal restore. It writes a new report outside the evidence tree:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PYTHON'
import json
import sys
from pathlib import Path

root = Path.cwd().resolve()
plan_path = root / "results/secon2027/plans/formal-v1.json"
plan = json.loads(plan_path.read_text())
sys.path.insert(0, str(root / plan["snapshot_path"] / "source"))
from tools.secon2027_experiment import audit_plan

report = audit_plan(plan_path, root)
output = root / "work/reproduction/formal-v1-audit.json"
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("x") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
assert report["status"] == "complete"
assert len(report["completed"]) == 760
assert not report["failed"] and not report["missing"]
print("760 verified runs; no simulation executed")
PYTHON
```

The original complete formal audit passed 760/760 with zero failed or missing keys; `analysis.json` embeds that audit. This command reproduces the check. A partial package yields an incomplete report and fails the completion assertions. The audit verifies saved source and reconstructs evidence through saved audit workers; it does not generate replacement runs.

## Recompute statistics and standard figures

From the full repository or complete formal restore, the saved analyzer below rebuilds raw-event statistics and its standard PDF/SVG figures in one operation. It first audits the complete plan. A partial plan produces an inventory and an incomplete status, without a selective performance summary.

```bash
PYTHONDONTWRITEBYTECODE=1 work/secon2027-repro-env/bin/python \
  results/secon2027/snapshots/63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee/source/tools/analyze_secon2027.py \
  --root . \
  --plan results/secon2027/plans/formal-v1.json \
  --out-dir work/reproduction/formal-v1-analysis
```

Create the analysis environment relative to the chosen root first. The output directory must be new. `analysis.json` records the analyzer hash, plan/source identities, actual environment, audit result and output hashes. CSV outputs include `planned_runs`, `runs`, `summary`, paired effects, flow diagnostics, packet-kind-by-stage costs, RX outcomes, request statuses, action counts and ACK outcomes. The plotting stage creates `main_results`, `paired_effects`, `ablation_effects`, `latency`, `cost_decomposition` and `load_curve` as PDF and SVG where the corresponding data exist. Deadline cases remain identified separately in the tables and main-results panels. The manuscript grids are produced by `paper/secon2027/build_figures.py`; `paper/secon2027/FIGURES.md` describes all four grids. Its exclusive output directory contains PDF/SVG/PNG, exact source-row CSVs, and a manifest binding the builder, complete analysis, input tables and all exports.

For the corrected pilot, use its saved analyzer under snapshot `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`, plan `results/secon2027/plans/development-pilot-v2.json`, and a different new output directory. Reproducing either stage does not add independent samples.

The supplemental formal mechanism helper also requires complete coverage and performs a full plan audit before inspecting events. Its supported command is:

```bash
mkdir -p work/reproduction
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=results/secon2027/snapshots/63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee/source \
python3 \
  artifacts/secon2027/reproduction_helpers/inspect_formal_mechanisms.py \
  --root . \
  --plan results/secon2027/plans/formal-v1.json \
  --out work/reproduction/formal-v1-mechanisms.json
```

The explicit Python path makes the saved audit module available in a standalone restore even when the archive has no top-level `tools/` directory. This new output records the helper hash, physical action exposure, intended-hop losses, clean control identities and prospective scenario criteria. It supplements the frozen analysis without changing seeds, scientific settings or interpretation rules.

## Execution, failure and resume semantics

The research entry point is `tools/secon2027_experiment.py`. `freeze` binds registered seeds, the contract, matrix and complete source; `run` executes only registered keys in a saved-source subprocess. Calling `run` for a completed key verifies and skips it. Tampered evidence is rejected, and no implicit new seed is selected. Reproduction of existing results normally requires the audit and analysis procedures above, not new simulation.

A crashed process retains its lock and attempt. The supported recovery command is `recover --plan PLAN --run-key KEY --reason REASON`. It checks that parent and worker processes are dead, validates their planned identities and preserves failure/lock evidence. A permitted infrastructure retry is explicit through `run --retry-infrastructure` and remains bounded by the frozen failure policy. An implementation failure cannot be reclassified as infrastructure failure to fill a batch. Exposed development or formal seeds are never relabeled as fresh validation seeds.

Pilot v1 failed because `CprDecision` was missing from an invalid-route recovery rejection branch. Pilot v2 ran all 72 declared development keys on the corrected source and the same already-exposed development seeds. Its frozen 161 tests and all raw run audits passed. Promotion to 2.1.29 used 58 fixture tests, without rerunning research seeds.

## Formal chronology and administrative erratum

The formal identities are:

- Plan: `results/secon2027/plans/formal-v1.json`, canonical SHA-256 `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`.
- Source snapshot: `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`, tested VERSION **2.1.29**.
- Contract SHA-256: `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`.
- Matrix SHA-256: `3cc6bab3de7c7767c3fbf845deb156f945db13d98361f0dc5b7bf7e769cc6ea3`.

The seven method files match the corrected pilot. VERSION and the prospective contract are separately represented in the new snapshot. The matrix contains 480 primary runs, 120 clean-control runs and 160 additional deadline/drain runs, using 20 predeclared seeds per case and arm.

The development gate was registered at **2026-11-04T09:01:06.320060Z**, the formal plan froze at **09:01:52.961637Z**, and the first formal run started at **09:06:36.647153Z**. The frozen contract retained contradictory development-stage opening wording. This was clarified administratively after execution had begun, without changing its original bytes. New dispatch stopped while four in-flight workers completed normally, leaving **43 completed, zero failed and 717 unstarted keys**. All 20 formal seeds were already exposed.

The erratum was recorded at **09:09:21.850292Z**. See `docs/research/secon2027_formal_contract_erratum.md` and `results/secon2027/gates/formal-v1/administrative-pause.json` for the original hashes, timeline and 43 completion hashes. Continuation used the same plan, verified and skipped completed keys, and ran only the remaining keys. No completed key received a new scientific attempt; no seed or result was excluded or replaced. No partial performance selection or parameter change was performed during the pause. The final package and manuscript must preserve this chronology rather than describe the clarification as preceding first exposure.

## Release, interpretation and final closeout

Release 2.1.29 was pushed to `codex/meshecho-secon2027` over GitHub SSH on port 443 after recorded HTTPS connection failures. The authenticated GitHub REST ref endpoint returned the same full commit SHA, **`95eee87e7757bcd8316088fee2517bc6a796801d`**, at 2026-11-04T09:17:48.936341Z. Evidence is in `results/secon2027/gates/pilot-v2/publication-verified.json`; failed and successful transport logs remain preserved. The stored origin and global network configuration were unchanged. No tag or merge was performed. This release does not by itself complete the later formal evidence package.

P0 validates mechanics only: all 48 CPR/control flows were cold `F_INITIAL` flows, so it cannot establish repeat/recovery effectiveness. The three-seed pilot supports development diagnosis. Formal interpretation must retain adverse, zero and undefined results and the frozen prospective claim gates. The four model names refer to the implementations in `docs/research/secon2027_baseline_fidelity.md`; they do not establish official firmware or RF superiority. Rejection reason `stale-route-generation` does not establish deadline shortage merely because its action enum is `DROP_DEADLINE_INFEASIBLE`.

Complete formal audit, analysis environment, output hashes, mechanisms, resource totals and raw archive identities are now recorded below. Clean restoration, final paper QA and publication records are separately bound at closeout. Paper export is a separate artifact check. An internal build used bundled Tectonic after local TinyTeX lacked the Courier metric `pcrr8t`; the successful final compiler/version, source/PDF hashes, page count, fonts, metadata and visual review must be recorded for the same final exported PDF.

## Observed formal completion and costs

`results/secon2027/analysis/formal-v1/analysis.json` reports `complete`, 760 completed runs and no failures. All 38 case/arm cells contain the same 20 registered seeds (2027100–2027119); 480 runs cover primary default/matched comparisons, 120 cover the three clean controls, and 160 add the 10/60-second deadline cases. The 30-second deadline point reuses the prespecified S2 primary case. The bootstrap uses 10,000 resamples, analysis seed 20271104 and seed-level pairing; its unadjusted 95% percentile intervals remain descriptive.

The analyzer SHA-256 is `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54`. Its report binds every output file by bytes and SHA-256. The separate independent raw review verified all 760 runs and 166 source inputs in 77 check categories. Its initial checker incorrectly compared accepted manifest ACKs to all ACK events; the initial evidence and corrected checker/report are both retained. The verified totals distinguish 23,836 accepted from 78 rejected ACK events; this was a checker correction, not a simulator change.

Measured summed worker wall time is **4,423.191694785 seconds**; it is not elapsed batch time. Maximum observed single-worker RSS is **398,163,968 bytes**. Raw attempt files total **7,098,305,927 bytes**, including **7,052,691,761 bytes** of event JSONL. The verified gzip archive is 475,828,160 bytes. Allow space for both the archive and restored evidence, plus analysis outputs (about 32 MB); the frozen 18 GiB raw storage envelope was not exceeded. Resource and mechanism details are in `results/secon2027/gates/formal-v1/mechanism-resource-costs.json` and `docs/results/secon2027_formal_mechanisms.md`.

For manuscript grids, use a fresh destination:

```bash
/usr/bin/python3 paper/secon2027/build_figures.py --validate-only
/usr/bin/python3 paper/secon2027/build_figures.py \
  --out-dir work/reproduction/formal-v1-paper-figures
```

These commands verify saved complete tables and render existing estimates; they do not rerun simulations or change the bootstrap. `docs/results/secon2027_evaluation.md` and `docs/research/secon2027_claim_evidence.md` provide the numerical interpretation and table-to-run-to-manifest-to-source trace.

## Independent clean restoration of formal raw evidence

`docs/research/secon2027_supervisor_formal_archive_review.md` and its JSON record a successful independent restoration from the11published-part candidates. All11part hashes, the475828160-byte whole archive, all14667members and the exact path inventory passed. The restored files total7,104,348,257bytes. From a new empty directory, the saved-source `audit_plan` completed760/760 with zero failed/missing keys; all760audit workers returned0. The audit took570.836seconds. Every restored file remained unchanged after audit, and all760completion hashes also matched the independent verified raw review. No simulation was executed. The temporary7.58GB restore/reassembly tree was then removed; the wrapper source and full evidence remain in the reviewJSON (SHA256 `8730d7a9f389e33e1031b8d087cac9465443fbc3a6a933980ed8c39631cd9275`).

## Final manuscript export

`paper/secon2027/meshecho-secon2027-anonymous.pdf` is the final **9-page**,186064-byte candidate (SHA-256 `e477617e417a5c089bfeac3f4725e40e54e39e666071a1711c5c0e0f749eb1fd`). The source uses standard IEEEconference10pt without manual margin/line-spacing compression. It compiled with **Tectonic0.17.0**; all26fonts are embedded,27citations resolve, metadata/text/links are anonymous, and all9pages passed visual inspection. The source/PDF hashes and compiler diagnostics are bound by `paper/secon2027/manuscript_manifest.json`, `paper/secon2027/PDF_QA.md` and the independent finalPDFreview. The manuscript uses `figures/formal-v2`; formal-v1figure exports are retained as a superseded rendering revision.

From `paper/secon2027`, a standard Tectonic installation can rebuild the manuscript:

```bash
tectonic --keep-logs --outdir ../../work/reproduction/paper main.tex
```

Create that new output directory before compiling. The recorded build used the bundled compiler; its exact command and version are in the manuscriptQA. Compiler timestamps/toolchain differences may change PDFbytes; rendered content, page/font checks, source hashes and fixed figure inputs provide the reproduction comparison. No research simulation is needed to compile the manuscript.

The anonymous PDF is separate from the complete reproducibility materials, which intentionally retain internal source paths, release identities and audit provenance. Do not treat the full research package as an anonymous review attachment. Publication receipts identify the exact verified Git commits separately from the tested scientific snapshot.

## Verified raw publication and transport repackaging

The complete raw evidence was published at **`30e7bd42ecee5ff3d538601df8146934eca680fa`**, independently confirmed through the authenticated GitHub ref endpoint. The remote branch advanced without force from `95eee87e7757bcd8316088fee2517bc6a796801d`. All 123 added Git blobs, the exact tree and commit were verified before the branch update. The receipt is `results/secon2027/gates/formal-v1/publication-transport4m-006/publication-verified.json`.

Large HTTPS pushes and 45 MiB part requests failed; the successful transport uses **114 parts of at most 4 MiB**. Their independent streaming reconstruction retains exactly 475,828,160 bytes and SHA-256 `81776e12501e56945dd8aad6a37bb68e5f6e4b41d66c88ae041e7689e490d067`. This is transport repackaging, with no recompression, event changes, source changes, or simulation reruns. The member index is unchanged. The new transport index SHA-256 is `56db675d6aae15c8b38c33d9ad1f36b48e1779a775503dd76519313c7bc7ef71`.

The original unpublished local commit `1e487d2327d27ae21fc000449a5f254c1621d92c` and its eleven larger parts remain preserved locally, with the commit protected by `archive/meshecho-secon2027-raw-45m`. `artifacts/secon2027/formal-v1-raw-evidence.transport-history.json` records its original commit bytes, exact blob mapping and reconstruction instructions. Historical failure and restoration reports are not rewritten. The temporary upload branch contains only seven small files and is removed after final publication verification; it is not the authoritative delivery branch.

## Final analysis/paper package and clean re-render

The separate package `formal-v1-analysis-paper-2.1.30.tar.gz` is **9,978,264 bytes**, SHA-256 `d60a67eb549905af087968b3c1ab496851ef78ebf38f8e9be6c26c29584e66e9`, with **1,230 verified members**. Three transport parts are at most 4 MiB each; the adjacent `.parts.index.json` lists their order and hashes. This package holds complete statistical outputs, manuscript source/PDF/figures, exact source bindings and independent reviews. Large diagnostic JSONs and CSVs are supplied through this package. Live acceptance, submission, checkpoint and publication documents remain separate ordinary repository files.

The package was restored into a new empty directory with the same standard-library restore helper. From that restored root, `/usr/bin/python3 paper/secon2027/build_figures.py --analysis-dir results/secon2027/analysis/formal-v1 --out-dir work/reproduced-paper-figures` succeeded. All four exact source CSVs and all four PNG exports were byte-identical to the supplied formal-v2 figures. All 1,230 original restored members retained their hashes after rendering. No simulator or bootstrap was rerun. The independent restoration record is `docs/research/secon2027_final_package_restore_review.json`.

Final artifact publication was verified at `e653315803c46abf80fb6d3476eee3b5f7fd34a4`; the receipt is `docs/project-management/secon2027_publication_receipt.json`. Subsequent metadata-only closeout is verified in the user-facing publication receipt. Scientific source, data, figures, PDF and both archive hashes remain unchanged.
