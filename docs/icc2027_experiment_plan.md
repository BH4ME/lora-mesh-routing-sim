# ICC 2027 Experiment Plan

This repository provides a reproducible comparison plan for a LoRa mesh paper
targeting the IoT and sensor-network communication scope.

## Protocol Matrix

The `--protocol icc` group runs the following seven configurations on the same
topology, traffic trace, PHY parameters, and random seed:

| Configuration | Role in the paper |
| --- | --- |
| `meshtastic` | Managed-flooding baseline |
| `meshcore` | Route-discovery and source-route baseline |
| `calm` | Confidence-aware bounded-fallback method without learning |
| `smart-calm` | Full method: profile selection plus bounded fallback |
| `smart-calm-static` | Learning ablation: fixed balanced profile |
| `smart-calm-no-fallback` | Fallback ablation |
| `smart-calm-no-confidence` | Confidence-ranking ablation |

The ablations are intended to answer whether the gain comes from online
adaptation, bounded redundancy, or confidence-aware route selection. They must
remain in the same table as the full method; otherwise the contribution is
hard to isolate.

## Scenarios

`tools/run_icc_experiments.sh` runs four scenarios:

| Scenario | Traffic | Rate | Purpose |
| --- | --- | ---: | --- |
| `50n_unicast_pairs` | Repeated unicast | 6/min | Route-cache and ACK-PDR comparison |
| `50n_mixed` | Mixed unicast/broadcast | 6/min | IoT workload with group traffic |
| `50n_mixed_shadow6` | Mixed unicast/broadcast | 6/min | Robustness under stronger shadowing |
| `50n_mixed_rate10` | Mixed unicast/broadcast | 10/min | Offered-load stress test |

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
4. Treat `smart-calm-static` as the no-learning control, not as a second full
   method.
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
10. The fairness probe accepts
    `--smart-max-timeout-retries 0` for a one-shot, budget-matched mechanism
    comparison. Runs using the default value `2` must be labeled as recovery
    evaluations, because the fixed baselines do not have the same timeout
    controller.

## Suggested Paper Tables

* **Table I:** Main unicast and mixed-traffic comparison across all baselines and
  Smart-CALM.
* **Table II:** Smart-CALM ablations for PDR, P95 ACK delay, airtime, energy,
  collision rate, and fallback count.
* **Table III:** Robustness under shadowing and high offered load.

A six-page conference paper should use figures for only the most important
trade-offs. The raw CSV files and long-format summary CSVs preserve the
remaining metrics for supplementary analysis.

See [ICC 2027 Comparison](results/icc2027_comparison.md) for the verified
four-scenario summary.

The current `2.1.13` audit concludes that the existing 3000 m matrix is fair as
a shared-harness comparison, but too link-friendly and too asymmetric for a
standalone claim about general multi-hop confidence-aware routing. Its legacy
native rows also use a shorter MeshCore-like route-cache TTL than MeshEcho.
See
`docs/results/meshecho_fairness_audit.md` before using the frozen results.

The ten-seed random-pair probe in
`docs/results/meshecho_fair_multihop_probe.md` confirms this boundary:
CALM/MeshEcho keeps an airtime advantage but does not beat the source-route
baseline on ACK PDR in the non-saturated multi-hop setting. Smart-CALM's
remaining PDR difference is not statistically established as a
confidence-ranking gain after the one-shot timeout budget check. The connected
pair diagnostics further show that some hard settings are route-discovery
stress cases rather than neutral data-plane comparisons.

The pre-fix Smart-CALM ablation rows in the historical `2.1.3`/`2.1.7`
artifacts must not be used as current evidence for the no-fallback variant.
The no-fallback implementation and its regression test were corrected in
`2.1.8`; a new ablation matrix must be generated before making quantitative
claims about those rows.
