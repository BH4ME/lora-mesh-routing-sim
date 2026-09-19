# ICC 2027 Experiment Plan

This repository provides a reproducible comparison plan for a LoRa mesh paper
targeting the IoT and sensor-network communication scope.

## Protocol Matrix

The `--protocol icc` group runs the following six MeshEcho-facing
configurations on the same
topology, traffic trace, PHY parameters, and random seed:

| Configuration | Role in the paper |
| --- | --- |
| `meshtastic` | Managed-flooding baseline |
| `meshcore` | Route-discovery and source-route baseline |
| `etx` | Standard expected-transmission-count path metric |
| `ett` | Airtime-weighted expected-transmission-time path metric |
| `minhop` | Matched-discovery shortest-path baseline |
| `meshecho` | MeshEcho confidence-aware admission and bounded recovery |

The ETX/ETT rows are the mechanism-relevant external baselines: they test
whether MeshEcho adds value beyond standard PRR and airtime-weighted routing
metrics under the same discovery and route-cache budgets.

MeshEcho component controls are selected explicitly with the
`meshecho-*` protocol names. They are within-policy ablations, not additional
ICC competitors.

## Scenarios

`tools/run_icc_experiments.sh` runs four scenarios:

| Scenario | Traffic | Rate | Purpose |
| --- | --- | ---: | --- |
| `50n_unicast_pairs` | Repeated unicast | 6/min | Route-cache and ACK-PDR comparison |
| `50n_mixed` | Mixed unicast/broadcast | 6/min | IoT workload with group traffic |
| `50n_mixed_shadow6` | Mixed unicast/broadcast | 6/min | Robustness under stronger shadowing |
| `50n_mixed_rate10` | Mixed unicast/broadcast | 10/min | Offered-load stress test |

After the four matrices, the script runs a short `connected-multihop` quality
probe (three seeds by default) using the same simulator and independent
channel-reception stream. This probe is a gate, not a fifth performance table:
it fails the command if any seed has fewer than the requested connected pairs,
mean selected graph distance below two hops, or fewer than 10% of direct links
below 0.99 static PRR. The diagnostic CSV and report are written with the
`<OUT_PREFIX>_connected_multihop_quality` suffix. Set `ICC_RUN_QUALITY_PROBE=0`
only to reproduce a pre-gate legacy run.

The same script then runs the primary calibrated multi-hop matrix: 50 nodes in
an 8.25 km square, SF7, mixed traffic at 1 flow/min, 24 graph-selected pairs,
analytical edge PRR >= 0.90, 20 seeds, and a matched 2 s MeshCore-like
discovery window. It is intended to test route selection in a connected,
non-saturated regime; the 18 km probe is retained as a separate discovery
stress diagnostic.

Set `ICC_RUN_SENSITIVITY=1` to append the 20-seed SF8 and offered-load
connected-multihop cases from `tools/run_icc_sensitivity_experiments.py` to the
same release run. The default is off so the primary reproduction command
remains short; the sensitivity runner can also be invoked directly.

Run `python3 tools/run_icc_generalization_experiment.py` for separate
generalization strata: unconditioned random source-destination pairs, a
100-node three-hop case, and repeated-pair temporal-fading cases with 600 s
and 30 s route-cache lifetimes. These results are reported separately from the
conditioned first-discovery matrix.

The default setup is 50 nodes in a 3000 m square, 1200 s per run, eight fixed
unicast pairs, SF9/BW125 kHz/CR 4/5, and 20 seeds. Environment variables
`NODES`, `AREA_M`, `DURATION_S`, `PAIR_COUNT`, `SEEDS`, `SEED0`, and `OUT_PREFIX`
can override these values without editing the script.

## Reported Metrics

The simulator separates the two reliability views that should not be conflated:

* `unicast_pdr`: source-side ACK-confirmed PDR.
* `destination_unicast_pdr`: destination DATA arrival ratio before ACK return.

For the main ICC table, use:

* ACK-confirmed PDR and destination DATA arrival ratio.
* Mean and P95 ACK delay.
* Total airtime and channel busy ratio.
* Total energy and energy per successful application delivery.
* Packet reception ratio and collision rate.
* Control overhead, route repairs, and fallback forwarding.

`analyze_results.py` reports mean, sample standard deviation, and a two-sided 95%
Student-t confidence interval over seeds. Pass `--summary-csv` to emit a
machine-readable long-format summary for table generation.

## Reproducibility Rules

1. Keep the same `seed0`, seed count, topology generator, traffic generator,
   PHY configuration, static per-link shadowing realization, and application
   schedule for every protocol.
2. Do not mix CSV files produced before and after the ACK-aware metric update.
3. Use the same current and voltage assumptions for every configuration when
   comparing energy.
4. Treat `meshecho-no-confidence`, `meshecho-no-fallback`,
   `meshecho-no-hop-penalty`, and `meshecho-no-age-penalty` as within-policy
   component controls, not as separate proposed methods.
5. Include the shadowing and offered-load scenarios in the robustness section,
   even if the full method does not win every individual metric.
6. State that this is a packet-level channel model rather than a waveform-level
   LoRa emulator, and report the PHY and radio-current assumptions.
7. Before freezing a matrix, report direct-link PRR quantiles and the cached
   route hop distribution. Reject a setting in which nearly all direct links
   have PRR above 0.99 or nearly all successful cached routes are one hop.
8. New ICC matrices use a matched `600 s` MeshCore-like route-cache TTL and
   `INDEPENDENT_RNG_STREAMS=1` by default, so channel-reception randomness is
   separated from forwarding jitter and learning exploration. Set
   `MESHCORE_ROUTE_TTL_S=300` and `INDEPENDENT_RNG_STREAMS=0` only for legacy
   frozen-result reproducibility.
9. For mechanism claims, equalize route-cache lifetime, retry, and fallback
   budgets across the
   confidence and no-confidence variants and state whether fixed baselines have
   an equivalent recovery controller.
10. The fairness probe uses `--max-timeout-retries 0` for a one-shot,
    budget-matched MeshEcho comparison. The historical
    `--smart-max-timeout-retries` alias remains accepted for old scripts.
    Runs using a nonzero value must be labeled as timeout-recovery
    evaluations.
11. Do not accept a connected-multihop probe based only on aggregate means:
    the quality gate checks pair-pool completeness, mean graph distance, and
    direct-link PRR regime separately for every seed.
12. For fresh cross-protocol route-discovery comparisons, set the MeshCore-like
    collection window to the same 2 s budget used by MeshEcho. Use
    `MESHCORE_DISCOVERY_WINDOW_S=0` only for an explicitly labeled immediate-
    reply legacy reproduction.
13. Temporal-fading cases use deterministic paired block offsets keyed by seed,
    link, and time block. Report the fading sigma and block interval, and do
    not pool them with static-channel estimates.

## Suggested Paper Tables

* **Table I:** Main comparison across managed flooding, matched source routing,
  min-hop, ETX, ETT, and MeshEcho.
* **Table II:** MeshEcho component ablations for ACK PDR, destination PDR,
  airtime, and fallback behavior.
* **Table III:** Robustness under spreading-factor and offered-load changes.

A five-page conference paper should use figures for only the most important
trade-offs. The raw CSV files and long-format summary CSVs preserve the
remaining metrics for supplementary analysis.

See [ICC 2027 Comparison](results/icc2027_comparison.md) for the verified
2.1.22 calibrated-matrix, component-ablation, cache-reuse, generalization,
and robustness summary. The primary artifacts use the
`results/meshecho_v2_1_22_icc2027_calibrated_multihop.csv` prefix, while the
SF/load sensitivity artifacts use
`meshecho_v2_1_22_icc2027_sensitivity_*`.

The component artifact
`results/meshecho_v2_1_22_icc2027_component_ablation.csv` is generated with
the same 20 seeds and connected-pair quality contract. It isolates confidence
ranking, route-miss fallback, hop penalty, and route-age penalty. The primary
matrix produces exactly two-hop selected pairs; deeper pair churn and
hardware-in-the-loop validation remain future work rather than hidden
assumptions. The repeated-pair cache diagnostic is stored under
`results/meshecho_v2_1_22_icc2027_cache_ttl{600,30}.*`; its estimand is
route-cache reuse/aging and it is not pooled with the sparse primary matrix.
