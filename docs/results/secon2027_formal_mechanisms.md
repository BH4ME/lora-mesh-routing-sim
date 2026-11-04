# Formal v1 mechanism review: complete frozen population

All **760/760** planned runs are included, with 0 failed keys in the completed-plan audit. The review covers **38 case/arm populations ×20 seeds, 30 CPR/comparator cells, 600 paired seed records and 240 deadline-response rows**. Plan `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`, source `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`. No simulation was run by this diagnostic tool and no scientific result was selected by its sign.

The original contract and plan remain immutable. Formal dispatch was administratively paused after 43 completions while a stale opening-status contradiction was documented in `docs/research/secon2027_formal_contract_erratum.md`; the same plan resumed by verifying/skipping completed keys. All 20 seeds remained exposed. This review does not backdate the erratum or relabel them as fresh after exposure.

## Prospective claim gates

These are the frozen contract's interpretation gates, **not filters**. A failed gate limits the corresponding claim while preserving all its seeds, controls and outcome rows. Structural alternatives describe offline topology and do not establish RF success or provide an oracle to a protocol. All per-seed gate evidence is retained in `prospective-criteria-and-comparisons.json`.

| Prospective claim gate | Population | Result | Observable evidence |
|---|---|---|---|
| S1-cached-multihop | S1-default | met | 480 physical routed initials; 526 accepted ACK paths ≥2 hops |
| S1-cached-multihop | S1-matched | met | 480 physical routed initials; 526 accepted ACK paths ≥2 hops |
| S2-cached-route-disruption | S2-default | met | 498 primary-model intended fault-edge TX; 85 CPR initial-path intersections; all structural endpoint alternatives ≤H: True |
| S2-cached-route-disruption | S2-matched | met | 490 primary-model intended fault-edge TX; 85 CPR initial-path intersections; all structural endpoint alternatives ≤H: True |
| S3-load-and-contention | S3-default | met | 80/80 primary arm/seed count increases; 7836 intended collision/half-duplex opportunities |
| S3-load-and-contention | S3-matched | met | 80/80 primary arm/seed count increases; 7820 intended collision/half-duplex opportunities |

The S3 count test pairs each primary model/seed with S1 in the same regime. It does not compare a control with an unplanned S1 control. The S2 physical-edge test includes primary models and requires an independent CPR initial-route intersection; controls cannot manufacture its primary exposure. Deadline10/60 diagnostics are reported in full below, but they are not substituted for a failed main-scene gate.

## Every component comparison, including zero exposure

Reference component activity is reconstructed from physical source DATA marker1, physical source FLOOD marker2, or successful ACK cancellation. These counts differ from requested actions. For each paired seed the resolved pre-attach parameters must differ only in name and the specified true→false toggle. Missing or unexpected parameter differences limit component interpretation. Control disabled-event counts must be zero; any nonzero value is retained and flagged, not silently corrected.

| Case / control | CPR component events | Zero-exposure CPR seeds | Disabled-control events | Other resolved parameters match / intended toggle | Interpretation gate |
|---|---:|---|---:|---|---|
| S2-matched / meshecho-cpr-noackcancel | 204 | none | 0 | True / True | exposed and isolated |
| S2-matched / meshecho-cpr-norepeat | 182 | none | 0 | True / True | exposed and isolated |
| S2-matched / meshecho-cpr-norecovery | 142 | none | 0 | True / True | exposed and isolated |
| S3-matched / meshecho-cpr-noackcancel | 685 | none | 0 | True / True | exposed and isolated |
| S3-matched / meshecho-cpr-norepeat | 1890 | none | 0 | True / True | exposed and isolated |
| S3-matched / meshecho-cpr-norecovery | 1597 | none | 0 | True / True | exposed and isolated |

Zero-exposure reference seeds remain in all 20-seed estimands. Exposure and component isolation alone do not prove a benefit or establish an exclusive flow-level cause; the paired outcomes must also be reported. ACK check denominators include ineligible checks and must not be called eligible cancellation opportunities.

## Full CPR reference populations and fault outcomes

Counts below sum 20 seeds within each separate case; default/matched duplicate effective settings are not pooled as n40. Every scheduled flow enters exactly one of the outcome categories. There are zero timely ACKs without timely DATA in the audited population.

| Case | Scheduled | Timely DATA+ACK / DATA-only / no timely DATA | Initial R / F / other | Repeat / recovery TX | Cancellation success / decoded checks | Relay evictions |
|---|---:|---|---|---|---|---:|
| R-deadline-10-S2-matched | 648 | 372 / 93 / 183 | 318 / 330 / 0 | 126 / 0 | 198 / 6506 | 0 |
| R-deadline-60-S2-matched | 648 | 407 / 98 / 143 | 437 / 211 / 0 | 224 / 188 | 197 / 7349 | 0 |
| S1-default | 648 | 526 / 88 / 34 | 480 / 168 / 0 | 135 / 91 | 205 / 8869 | 0 |
| S1-matched | 648 | 526 / 88 / 34 | 480 / 168 / 0 | 135 / 91 | 205 / 8869 | 0 |
| S2-default | 648 | 415 / 93 / 140 | 392 / 256 / 0 | 182 / 142 | 204 / 7551 | 0 |
| S2-matched | 648 | 415 / 93 / 140 | 392 / 256 / 0 | 182 / 142 | 204 / 7551 | 0 |
| S3-default | 3059 | 1181 / 884 / 994 | 2445 / 608 / 6 | 1890 / 1597 | 685 / 24949 | 0 |
| S3-matched | 3059 | 1181 / 884 / 994 | 2445 / 608 / 6 | 1890 / 1597 | 685 / 24949 | 0 |

Fault attenuation uses each physical TX's start,80≤start<160. DATA/RREP target path[index+1], ACK targets path[index]; broadcast prefixes and FLOOD have no designated routed next hop. Actual target RX rows are joined by TX ID and receiver. A lifetime overlap, a source-carried path intersection and a physical attempt on a failed edge are different observations. The following outcomes include every flow with at least one physically attempted intended DATA edge during an active fault, including starts before the fault where observed.

| Case (CPR reference) | Fault-enqueued / active | Initial-path intersections | Intended fault-edge TX / distinct DATA flows | DATA flows whose initial TX preceded fault | Exposed flows: timely ACK / DATA-only / no timely DATA |
|---|---|---:|---|---:|---|
| R-deadline-10-S2-matched | 193 / 203 | 51 | 102 / 54 | 3 | 0 / 1 / 53 |
| R-deadline-60-S2-matched | 193 / 235 | 125 | 233 / 125 | 3 | 26 / 11 / 88 |
| S2-default | 193 / 218 | 85 | 159 / 86 | 3 | 19 / 6 / 61 |
| S2-matched | 193 / 218 | 85 | 159 / 86 | 3 | 19 / 6 / 61 |

Full fault TX details, RX outcomes, pre-fault logged cache confirmations/invalidation evidence and exposed-flow paths are retained per run. Failure or capture-collision labels are descriptive: multiple stages/hops/interferers can affect a flow, so a fault-window failure is not assigned exclusively to the injected attenuation. A structural 6-hop alternative is not evidence that recovery must succeed.

## High-load pressure and rejection semantics

| Case / arm | Mean seed queue wait s / p95 s | Started / canceled / protocol-no-start | Intended collision / half-duplex / PRR / success | Capacity evictions |
|---|---|---|---|---:|
| S3-default / meshcore | 0.093 / 0.841 | 21658 / 0 / 0 | 1013 / 268 / 178 / 17685 | 0 |
| S3-default / meshecho | 0.094 / 0.796 | 22694 / 0 / 0 | 1040 / 269 / 168 / 18204 | 0 |
| S3-default / meshecho-cpr | 0.345 / 1.034 | 43230 / 3653 / 52 | 3228 / 887 / 141 / 17691 | 0 |
| S3-default / meshtastic | 0.934 / 1.608 | 39597 / 5518 / 0 | 951 / 180 / 41 / 5181 | 0 |
| S3-matched / meshcore-matched | 0.098 / 0.806 | 21854 / 0 / 0 | 1039 / 225 / 194 / 17503 | 0 |
| S3-matched / meshecho-cpr-matched | 0.345 / 1.034 | 43230 / 3653 / 52 | 3228 / 887 / 141 / 17691 | 0 |
| S3-matched / meshecho-cpr-noackcancel | 0.350 / 1.035 | 44661 / 3093 / 36 | 3253 / 886 / 135 / 18197 | 0 |
| S3-matched / meshecho-cpr-norecovery | 0.092 / 0.752 | 27381 / 783 / 5 | 2057 / 513 / 254 / 20969 | 0 |
| S3-matched / meshecho-cpr-norepeat | 0.436 / 1.047 | 40370 / 4490 / 92 | 2064 / 574 / 103 / 12533 | 0 |
| S3-matched / meshecho-matched | 0.094 / 0.796 | 22694 / 0 / 0 | 1040 / 269 / 168 / 18204 | 0 |
| S3-matched / meshtastic-matched | 0.668 / 1.223 | 39622 / 5380 / 0 | 964 / 168 / 36 / 5031 | 0 |

All-population request statuses: `{"canceled": 46960, "protocol-no-start": 371, "started": 574959}`. Non-start reasons: `{"canceled-before-start": 46960, "protocol-hook": 371}`. Correlated intended receiver opportunities are not independent packets/flows. Mean seed p95 values summarize success/wait distributions and must be accompanied by unfinished populations, not interpreted as universal delay bounds. Cancelled requests do not represent transmitted airtime.

Source-state refusals, protocol rejections and relay-ledger capacity evictions are separate. All `(event, action, reason)` counts remain in the full JSON; rejected decision rows are also saved in `decision-rejection-reasons.json`. In particular, `DROP_DEADLINE_INFEASIBLE` with reason `stale-route-generation` is a stale-route rejection and **does not establish insufficient deadline budget**. Exact ledger peak occupancy remains unknown because enrollment/retirement occupancy is not logged. Zero eviction cannot establish that occupancy never reached 8; observed eviction cannot establish optimal capacity. No capacity sweep or memory-benefit claim is added after the freeze.

## All 30 comparisons, without outcome filtering

Positive reliability differences favor CPR; airtime ratios below 1 indicate lower CPR airtime. Values below are equal-seed descriptive paired means: reliability difference and exp(mean log airtime ratio), not pooled ratios. Undefined inputs retain an undefined whole-population ratio. This mechanism inventory does not recompute bootstrap intervals; the frozen main analyzer supplies the complete unadjusted descriptive 95% intervals. No significance, noninferiority or causal claim follows from this table.

| Case | Comparator (reference = CPR in same case) | n | ACK difference pp | Delivery difference pp | Geometric airtime ratio |
|---|---|---:|---:|---:|---:|
| S1-default | meshecho | 20 | 3.99 | 14.86 | 1.157 |
| S1-default | meshtastic | 20 | 22.77 | 6.63 | 0.754 |
| S1-default | meshcore | 20 | 12.20 | 20.39 | 1.293 |
| S1-matched | meshecho-matched | 20 | 3.99 | 14.86 | 1.157 |
| S1-matched | meshtastic-matched | 20 | 25.99 | 5.88 | 0.751 |
| S1-matched | meshcore-matched | 20 | 13.27 | 22.19 | 1.334 |
| S2-default | meshecho | 20 | 9.28 | 21.68 | 1.604 |
| S2-default | meshtastic | 20 | 15.98 | 6.71 | 0.979 |
| S2-default | meshcore | 20 | 18.22 | 29.45 | 1.789 |
| S2-matched | meshecho-matched | 20 | 9.28 | 21.68 | 1.604 |
| S2-matched | meshtastic-matched | 20 | 15.49 | 2.84 | 0.951 |
| S2-matched | meshcore-matched | 20 | 18.41 | 29.72 | 1.813 |
| S2-matched | meshecho-cpr-noackcancel | 20 | 2.20 | 0.42 | 0.968 |
| S2-matched | meshecho-cpr-norepeat | 20 | 4.35 | 0.34 | 1.033 |
| S2-matched | meshecho-cpr-norecovery | 20 | 8.32 | 8.94 | 1.269 |
| S3-default | meshecho | 20 | -9.26 | 14.52 | 2.134 |
| S3-default | meshtastic | 20 | 15.75 | 6.31 | 1.114 |
| S3-default | meshcore | 20 | -9.79 | 14.37 | 2.289 |
| S3-matched | meshecho-matched | 20 | -9.26 | 14.52 | 2.134 |
| S3-matched | meshtastic-matched | 20 | 15.75 | 6.43 | 1.112 |
| S3-matched | meshcore-matched | 20 | -9.04 | 14.42 | 2.290 |
| S3-matched | meshecho-cpr-noackcancel | 20 | -1.29 | -1.71 | 0.968 |
| S3-matched | meshecho-cpr-norepeat | 20 | 5.43 | 3.30 | 1.081 |
| S3-matched | meshecho-cpr-norecovery | 20 | -15.99 | 2.86 | 1.665 |
| R-deadline-10-S2-matched | meshecho-matched | 20 | 2.34 | 14.73 | 1.316 |
| R-deadline-10-S2-matched | meshtastic-matched | 20 | 8.54 | -4.10 | 0.780 |
| R-deadline-10-S2-matched | meshcore-matched | 20 | 11.47 | 22.78 | 1.487 |
| R-deadline-60-S2-matched | meshecho-matched | 20 | 8.06 | 21.26 | 1.619 |
| R-deadline-60-S2-matched | meshtastic-matched | 20 | 14.26 | 2.43 | 0.959 |
| R-deadline-60-S2-matched | meshcore-matched | 20 | 17.19 | 29.30 | 1.830 |

The 240 deadline rows include four models ×20seeds ×10/30/60s, using the actual S2-matched main rows for 30 s. They are not independent additional 30 s runs. Deadline and drain/cutoff change together (250/270/300 s accounting cutoff), so a cost change includes tail-accounting exposure and is not assigned solely to local timing. No unregistered across-deadline inferential contrast is introduced.

## Measured resource cost and evidence

Actual summed worker wall time is **4423.192 s (73.72 min)**; largest single worker duration is 20.901 s. Peak worker RSS is **398,163,968 bytes (379.72 MiB)**. Raw attempt files total **7,098,305,927 bytes (7.098 GB)**, including **7,052,691,761 bytes** of event JSONL. These are observations, not prospective guarantees. Worker wall sum is not four-worker elapsed time; administrative pause, audit, analysis and archive costs are additional. Per-case/arm costs for all 38 cells are in `mechanism-resource-costs.json`.

Immutable diagnostic files under `results/secon2027/gates/formal-v1/`: `mechanism-inspection.json`, `prospective-criteria-and-comparisons.json`, `mechanism-resource-costs.json`, `all-comparison-means.csv`, `deadline-response-rows.json`, `decision-rejection-reasons.json`, the exact `formal-mechanism-inspection.py`, synthetic validation script, and completed-plan `audit.json`. Raw attempts, their manifests and the frozen contract were not changed. Inspector SHA256 `883b52c1695f66824423cf2b9e9f103885b86a3ed05370b039c11f84ea4ceaa7`. The independent full read command was:

```sh
python3 work/formal-mechanism-inspection.py --plan results/secon2027/plans/formal-v1.json --out work/formal-mechanism-inspection-v1.json
```

When relocated, provide `--root` pointing at the restored repository. Hardware/RF, calibrated topology generality, cache-TTL expiry and optimal ledger sizing remain outside this evidence. These measurements evaluate the fixed method, including losses; they do not authorize post-validation tuning, seed replacement or a new claim of universal improvement.
