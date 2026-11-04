# SECON 2027 analysis specification

Implementation: `tools/analyze_secon2027.py`. Validation uses synthetic arrays and event rows in `tests/test_secon_analysis.py`; it never runs a simulation. This document specifies analysis and does not report performance results.

## Inputs and integrity boundary

The CLI accepts repeatable `--plan` paths, an exclusive new `--out-dir`, and optional `--root`. It first calls `tools.secon2027_experiment.audit_plan(plan_path, root)` for every supplied frozen plan. That audit checks immutable source/contract/config identities, expected runs and attempt evidence. Any missing, failed or pending planned key yields `analysis.json` with status `incomplete` and `planned_runs.csv`, exit status 2, and **no performance aggregate**. An integrity exception yields a failed report and nonzero exit. Existing output directories are rejected without overwriting their contents.

Multiple plans are reported together but never pooled across plan/case/source identities. All declared seeds must occur exactly once per included case/arm. CPR-versus-control pairs additionally require identical topology, radio, pair-pool, scheduled-trace and common-environment hashes. Prior failed attempts remain listed even when an allowed later attempt completed. The analysis never changes a registry, source snapshot, result manifest or run status.

Component comparisons use each run's resolved pre-attach `identity.protocol_parameters_by_arm[protocol]`, not only requested overrides. For every paired seed, a clean `noackcancel`, `norepeat`, or `norecovery` ablation permits only `name` plus the respective `cancel_on_ack`, `enable_repeat`, or `enable_recovery` field to differ, and requires that component to change from true to false. All other captured fields, including timers, TTL, wire/ledger flags and capacity, must match. Missing resolved parameters, a missing intended toggle, or unexpected differences produce `mixed-policy`, retaining per-seed differing field names/values and reasons in effect tables. Such comparisons are excluded from the clean ablation panel. Legacy `nocancel` is always a `component-policy` comparison because it removes the whole ledger policy; it is never a clean ACK-cancellation ablation.

Raw inputs per completed attempt are `evidence.runs.csv`, `evidence.identities.json`, and the flow, action, request, transmission, RX and ACK JSONL files. Airtime and transmission counts are reconstructed from the transmission ledger and checked against `tx_ledger_airtime_s`/`started_request_count`. Historical `legacy_reserved_*` counters and aggregate aliases do not define physical sends. Future reservations are rejected if present as physical transmissions. Full ToA is charged for each frame starting inside the fixed accounting window, including a frame still in flight at cutoff.

## Frozen statistical fields

Formal matrices should state:

```json
{
  "unit": "seed",
  "analysis_seed": 20271104,
  "bootstrap_resamples": 10000,
  "interval": "paired-percentile-bootstrap-95-unadjusted-descriptive"
}
```

The analysis seed is used only by NumPy resampling and is never passed to a simulator. Development plans without these fields use the same documented defaults. All supplied plans must agree on the resampling settings. Each plan/case receives a deterministic RNG seed derived from SHA-256 of `[analysis_seed, [plan_sha256, case_id]]`; NumPy `default_rng` draws 10,000 seed-index samples with replacement, each of size n. The same case resamples are used across metrics and arms. NumPy/Python/Matplotlib versions and the analyzer's source SHA are recorded.

Each arm summary is an equal-weight seed mean with descriptive, unadjusted 95% percentile intervals (linear 2.5/97.5 percentiles). Paired reliability effects are CPR minus control per seed. The airtime effect is the mean of per-seed `log(A_CPR/A_control)`; exponentiating yields the geometric mean ratio and corresponding interval, not a ratio of pooled means. All intervals are descriptive, with no multiplicity-controlled, noninferiority or confirmatory significance claim. n<10 is explicitly flagged unstable; a single seed has no interval. The pilot's n=3 receives this warning regardless of how many packets it contains.

Zero timely deliveries make `A/timely_deliveries` undefined. Any undefined per-seed quantity makes its all-seed mean/interval undefined and records `undefined_n`; no seed is silently removed. A zero or negative airtime input makes a log ratio undefined, records the reason, and prevents a selected-subset paired interval. Undefined values serialize as JSON null and blank CSV fields, never NaN or fabricated zero.

## Metrics and mechanisms

All scheduled flows remain in the denominator. Timely ACK and timely destination delivery are reconstructed from event timestamps. Success latency p50/p95 is computed within each seed; empty success sets remain undefined. The successful-flow CDF pools timely successes descriptively and prints the unfinished fraction from the full scheduled population. It does not use packets as independent inferential units.

Actual source repeat and recovery counts come from physical transmissions whose sender equals the scheduled source, with CPR DATA marker 1 or FLOOD marker 2. Action requests are counted separately. Initial routed/flood choices use the exported `R_INITIAL`/`F_INITIAL` action labels, not the simulator's internal `R`/`F` state labels. These decision counts need not equal physical starts when a request never starts. ACK path lengths use accepted physical ACK provenance (`reverse_path`), and flow diagnostics retain all accepted hops, timely flags and latency. Cache lookup counters are disclosed separately from CPR initial R/F choices; zero lookup counters do not prove a policy has no cache activity.

ACK cancellation uses successful `cpr-cancel` events. Where supported by the frozen source, `cpr-cancel-check` counts decoded ACK checks, including checks with no matching pending relay, committed state or path exclusion. The success/check fraction is **not** an eligible-opportunity success probability. A zero check count gives an undefined fraction; old source snapshots without these events have an unknown check count. Check successes must reconcile to success events. Capacity `state-eviction` events and their `pending_canceled` flag remain distinct from total canceled requests; totals are not subtracted to invent unobserved causes.

RX outcome tables distinguish packet kind, designated next hop versus other/broadcast listeners, self reception, reason and decode flag. DATA and RREP designate `path[path_index + 1]`, following the packet's stored path order in either geographical direction; ACK designates `path[path_index]` under its reverse traversal convention. These are receiver opportunities, not independent packets. `delivery_without_timely_ack` means destination evidence without timely source confirmation; it is not automatically a causal diagnosis of ACK channel loss. Request-status and ACK rejection tables retain queue/no-start/failure evidence.

The complete cost partition is **packet kind × repair stage**. RREQ/RREP use discovery, CPR markers map to initial/repeat/recovery, and legacy FALLBACK uses fallback. Every TX appears in exactly one cell; each run's cells sum to its complete physical airtime. Cost means divide by all seeds, including zero occurrence of a cell.

Offline structural analysis removes declared grid faults of at least 60 dB, computes shortest paths at enqueue and initial source TX, and records whether a source's carried path crosses an active fault. It distinguishes any structural alternative from an alternative within the configured hop budget. This analysis is descriptive, retains unreachable flows and provides no oracle to a protocol; it does not prove successful delivery under fading/collision.

Fault-period enqueued flows have enqueue timestamps inside a declared fault's half-open interval. Fault-period active flows have a positive duration overlap between that interval and the flow's lifetime from enqueue to the earliest accepted ACK, fixed deadline or drain cutoff. A separate count retains active flows whose initial physical source transmission preceded an overlapping fault window. These populations count each flow once even with multiple faults, retain flows with no source TX, and do not imply attempted transmission over a fault edge. The narrower initial carried-path fault exposure count remains explicit, including zero.

## Outputs

- `analysis.json`: input/source/attempt provenance, completeness, failures, statistical settings, dependency versions, limitations, output hashes and plot inventory.
- `planned_runs.csv`, `runs.csv`, `summary.csv`: exact planned population, reconstructed per-run metrics, equal-seed summaries.
- `paired_effects.csv`, `paired_seed_effects.csv`: case-specific CPR/control effects and the underlying paired seed values.
- `flow_diagnostics.csv`, `rx_outcomes.csv`, `ack_outcomes.csv`, `request_statuses.csv`, `action_counts.csv`: mechanisms and retained failures.
- `cost_kind_stage.csv`, `cost_summary.csv`: additive per-run and seed-mean cost partitions.
- Standalone vector PDF/SVG figures: `main_results`, `paired_effects`, `ablation_effects` when declared, `latency`, `cost_decomposition`, and `load_curve` only when at least two S1/S3 load points share all other declared configuration/environment fields and the same actual resolved protocol parameters for every seed. Missing parameter evidence cannot establish a load line. Explicit defaults and omitted overrides compare by their resolved values, with integral floats and integers normalized equivalently. Points select exact case/arm/metric identities, never the first row for a protocol. Distinct arms present at the same load remain distinct lines even when they share a protocol or effective parameters; different arm IDs at different loads may connect only when their effective identities match unambiguously. Labels retain participating arm IDs. Undefined means break lines. No line is drawn through unmatched workloads just to create a curve.

Example command shape (replace with actual frozen plan paths; this is not an executed-results claim):

```bash
python3 tools/analyze_secon2027.py \
  --plan results/secon2027/plans/FROZEN_PLAN.json \
  --out-dir results/secon2027/analysis/NEW_ANALYSIS_ID
```

Analysis requires NumPy and Matplotlib in addition to the simulator's standard-library environment. The current interpreter provided NumPy/Matplotlib; no package installation or simulator run was needed for development. Synthetic checks cover constant paired effects, deterministic resampling, zero/undefined values, full seed pairing, exogenous-identity mismatch, actual versus reserved sends, cost additivity, ACK/capacity cancellation separation, incomplete-plan rejection, output exclusivity and real PDF/SVG generation. A macOS `/var` versus `/private/var` symlink mismatch found in the first synthetic path test was fixed by canonicalizing API roots and paths.
