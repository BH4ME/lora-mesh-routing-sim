# MeshEcho Simulation Fairness Audit

Date: 2026-09-04

This audit records the fairness boundary of the packet-level evaluation used
by the ICCT draft. It distinguishes common experimental inputs from
protocol-level advantages that are intentionally or unintentionally present in
the current matrix.

## Bottom Line

The simulator is fair as a shared-harness comparison, but the current
experiments are not yet fair as one general multi-hop benchmark. The original
3 km matrix is too link-friendly and cache-friendly. The later connected-pair
matrix corrects the link-quality saturation, but it drives route discovery
into a broadcast-collision regime in which MeshCore is barely able to install a
route. These are different questions and must be reported separately.

## Common Inputs

For each seed, all protocol configurations use the same:

- node placement and node roles;
- application schedule and source-destination trace;
- LoRa PHY parameters;
- static per-link shadowing realization;
- half-duplex, collision, capture, and probabilistic reception model;
- simulation duration and reported metrics.

The shared-seed comparison is implemented in
`lora_mesh_sim.py::run_one`, where topology and traffic random generators are
derived from the same seed for each protocol.

## Biases and Their Effects

| Item | Current setting or observation | Fairness consequence |
| --- | --- | --- |
| Pair reuse | Eight fixed unicast pairs | Deliberately favors route-cache reuse. This is valid as a cache-efficiency case, not as a neutral workload. |
| Link budget | 50 nodes, 3000 m square, SF9, 17 dBm, path-loss exponent 2.7 | Direct-link reception is too easy for a calibrated multi-hop study. |
| Cached paths | Across the 20 main seeds, 128/129 MeshCore cached routes and 142/142 CALM cached routes were one hop | The main matrix is mostly a connected, contention-dominated network rather than a multi-hop route-selection benchmark. |
| Link-quality stress check | With an additional 8 dB path-loss penalty in a link-budget calculation, the minimum direct-link reception probability over the replayed pairs remained 0.9999866 | The main setting does not expose enough weak-link variation for confidence ranking to matter often. |
| Recovery budget | CALM/MeshEcho has bounded fallback; the fixed baselines do not have an identical recovery controller. The exploratory Smart-CALM configuration additionally allows timeout retries. | End-to-end PDR gains cannot be attributed to confidence ranking alone. |
| Confidence ablation | `smart-calm-no-confidence` is numerically almost identical to `smart-calm` in the main mixed and shadowing matrices | The random matrix does not provide a standalone estimate of the average confidence benefit. |
| Packet-format cost | Every packet kind uses the same configured 32-byte airtime; source-route header growth is not modeled | Airtime for long source-route and fallback packets is simplified and may understate route-header cost. |
| Random-number coupling | `Simulator.random` is used for both packet reception draws and protocol forwarding jitter/exploration | Protocols that create different numbers of transmissions consume different parts of the same reception stream. Shared seeds therefore do not provide strict common random numbers for every channel event. |
| Random-stream mitigation | `--independent-rng-streams` now separates channel-reception draws from protocol jitter/exploration | This removes one source of coupling for new runs, but it does not align executions that generate different numbers of transmissions. Frozen CSVs remain in legacy mode. |

## Artifact Consistency

The historical Smart-CALM ablation CSVs were generated before the
no-fallback confidence-threshold fix now present in `lora_mesh_sim.py`.
For example, the retained frozen CSV reports nonzero fallback forwarding for
`smart-calm-no-fallback`, while a replay with the corrected code reports zero
confidence-triggered fallback for that variant. Those historical rows are
retained for traceability, but they must not be used as current ablation
evidence until the full ablation matrix is regenerated. The three-protocol
main-paper rows (managed flooding, source-route cache, and `calm-mesh`) do not
depend on that branch and remain the frozen results used in the manuscript.

## Recomputed Link-Budget Diagnostics

The default setting was replayed over the 20 main seeds using all 24,500
unordered node pairs and the same static per-link shadowing model as the
simulation. The direct-link reception distribution was:

| Population | Minimum direct PRR | Median direct PRR | Fraction below 0.99 |
| --- | ---: | ---: | ---: |
| All node pairs | `0.999909` | `1.000000` | `0.000` |
| Eight fixed-pair workload instances | `0.9999996` | `1.000000` | `0.000` |

The fixed-pair distances had a median of `1563 m`, a 95th percentile of
`2802 m`, and a maximum of `3290 m`. The result is therefore not just an
artifact of a few unusually short pairs: the configured link budget makes
essentially every pair an extremely high-PRR direct link.

A diagnostic sweep found that simply changing the area to `12 km` or `15 km`
still produced only about `1--3%` multi-hop cached routes in five-seed
replays. Area, transmit power, path-loss exponent, node density, and maximum
hop count must therefore be calibrated together. The acceptance condition for
the next matrix should be a reported, non-degenerate direct-PRR distribution
and a clearly non-trivial fraction of successful multi-hop routes, rather than
an area value selected in isolation.

## Mechanism Control

The separate route-conflict audit uses one fixed seven-node topology. It
intentionally disables online learning, timeout retry, and route-miss fallback,
and staggers route-request forwarding so that candidate admission rather than
RREQ collision is tested.

The 100-seed paired results are:

| Condition | Paired ACK-PDR delta |
| --- | ---: |
| No extra shadowing | `0.000` |
| Short branch weak by 5.0 dB | `0.000` |
| Short branch weak by 7.5 dB | `+0.215` |
| Long branch weak by 7.5 dB | `0.000` |

This is useful evidence that confidence can select a longer, more reliable
route under a sufficiently large quality conflict. It is not evidence of
topology-independent superiority, and its 100 seeds are repeated stochastic
trials on one topology rather than 100 independent layouts.

## Interpretation for the Paper

The current comparison is fair at the common-harness level: all protocols see
the same generated network and workload for a given seed. It is not fully
neutral at the scenario level or fully budget-matched at the mechanism level.
The appropriate claim is therefore:

> MeshEcho provides preliminary common-harness evidence of a
> reliability-airtime tradeoff, while the confidence mechanism is supported
> mainly by a controlled route-conflict experiment.

## New Random-Pair Multi-Hop Probe

To test whether the conclusion changes outside the cache-friendly main
workload, a ten-seed probe was run with 50 nodes in an 18 km square, random
source-destination pairs, mixed traffic at 4 flows/min, SF7, 17 dBm, path-loss
exponent 2.75, 4 dB shadowing, and independent channel-reception randomness.
The direct-link PRR distribution was non-saturated. The values below are the
mean of the per-seed quantiles:

| Population | p05 | p25 | p50 | p75 | p95 | Fraction below 0.99 | Fraction below 0.50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All node pairs, mean per-seed quantile | `0.000026` | `0.017577` | `0.756816` | `0.999517` | `1.000000` | `0.642` | `0.443` |

The mean results were:

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Meshtastic-like | `0.680` | `1.000` | `37.3` | `11606` | `1.67` |
| MeshCore-like | `0.456` | `0.486` | `139.5` | `70969` | `0.56` |
| CALM / MeshEcho | `0.413` | `0.479` | `97.5` | `47492` | `2.49` |
| Smart-CALM | `0.687` | `0.783` | `100.3` | `48204` | `18.99` |

The route cache diagnostics also changed materially: among completed cached
routes, MeshCore-like had about `10.2%` multi-hop routes, CALM about `43.4%`,
and Smart-CALM about `33.6%`. The fixed-profile Smart-CALM control was about
`44.6%`. This is a substantially more informative
multi-hop regime than the original 3 km/SF9 matrix, although some seeds still
have many failed route discoveries.

This probe changes the interpretation of the paper. In a random-pair,
non-saturated setting, CALM/MeshEcho retains an airtime advantage but does not
show a PDR advantage over MeshCore-like. Full Smart-CALM reaches `0.687`
ACK-PDR, while the fixed-profile control reaches `0.822`; therefore the
adaptive controller is not an unconditional improvement in this probe.
Relative to `smart-calm-no-fallback`, full Smart-CALM's paired mean ACK-PDR
gain is `0.047 +/- 0.110`, while relative to
`smart-calm-no-confidence` it is `0.049 +/- 0.062`. These intervals include
zero with ten seeds. The recovery budget and profile choice must therefore be
reported separately from confidence ranking.

## One-Shot Budget Check

To isolate confidence selection from timeout retry, the probe was rerun with
`--smart-max-timeout-retries 0`. This matches the timeout-retry count between
the Smart-CALM variants, but it does not give MeshCore-like a new recovery
controller and therefore is not a claim that all native protocol mechanisms
are identical.

In the 10-seed random-pair setting, Smart-CALM minus no-confidence had an
ACK-PDR difference of `+0.001` with a paired 95% CI of
`[-0.105, 0.108]`. Smart-CALM minus no-fallback was `+0.024` with a paired
95% CI of `[-0.041, 0.090]`. In the 10-seed, 20-node connected-multihop
low-load setting, the corresponding differences were `+0.070`
(`[-0.021, 0.160]`) and `-0.024` (`[-0.059, 0.012]`). These intervals all
include zero, so the current data do not establish a stable average
confidence-ranking gain.

The one-shot outputs are stored separately as:

- `results/meshecho_fair_budget_matched.csv`
- `results/meshecho_fair_budget_matched_connected20.csv`
- `docs/results/meshecho_fair_budget_matched.md`
- `docs/results/meshecho_fair_budget_matched_connected20.md`

## Connected-Pair Route-Discovery Stress Checks

The connected-pair selector uses a shared static link-budget graph: selected
pairs have graph distance 2--4 when edges with analytical PRR at least `0.90`
are retained. This controls the requested pair geometry, but it does not
guarantee that a route-discovery flood succeeds under the simulator's
stochastic reception and collision model.

In a 50-node, 15 km square with 24 shared pairs, unicast traffic at
`0.5 flows/min`, and 10 seeds, the direct-link distribution remained
non-degenerate, but MeshCore-like installed a route in only `0.063` of its
route-discovery attempts. Its ACK and destination PDR were both `0.049`.
CALM installed routes in `0.579` of attempts, while Smart-CALM and its
fixed-profile control were `0.462` and `0.446`, respectively. MeshCore
generated about 294 RREQ transmissions and only 8.1 RREP transmissions per
seed on average; the RREP/RREQ transmission ratio was `0.027`.

This was not caused only by offered application load. A 20-seed single-flow
check with one shared pair still gave MeshCore-like a route-discovery success
rate of `0.050`; only 1 of 20 seeds delivered the selected flow. The result
therefore measures a route-discovery stress case dominated by broadcast
contention and missing recovery logic. It should not be used as a standalone
claim that source-route data forwarding is intrinsically inferior. The stress
case also includes a route-reply timing asymmetry: MeshCore-like replies
immediately after first destination reception, while MeshEcho waits for its
candidate-collection window before replying. The new probe reports
`route_discovery_attempts`, `route_discovery_successes`,
`route_discovery_success_rate`, and `rrep_rreq_tx_ratio` so this distinction is
visible in the raw output.

The probe is stored in:

- `results/meshecho_fair_multihop_probe.csv`
- `docs/results/meshecho_fair_multihop_probe.md`
- `tools/run_fair_multihop_probe.py`

The following claims are not supported by the current matrix:

- universal superiority over flooding or source-route caching;
- average confidence-ranking gains in arbitrary random topologies;
- calibrated multi-hop deployment performance;
- a fully budget-matched comparison of all recovery mechanisms.

## Required Follow-Up

The ten-seed random-pair probe and the connected-pair stress checks should be
expanded into a pre-registered full matrix with more seeds and a calibrated
connected-flow regime. The next matrix should first verify that route discovery
is operational for every route-discovery baseline at a declared light-load
condition, then vary offered load as a separate stress factor. A practical
acceptance rule is to predefine a non-saturated direct-link distribution and a
minimum route-discovery success interval before collecting headline results.

For mechanism ablations, either disable timeout/fallback recovery for every
method or give every method the same maximum number of attempts and the same
fallback radius. Report first-attempt PDR separately from recovered PDR, since
otherwise Smart-CALM's timeout retry is inseparable from its confidence
ranking. These changes should be reported as a new versioned experiment line
rather than silently replacing the current results. New matrices should
enable `--independent-rng-streams`; keyed per-event draws would be a stronger
future option before treating same-seed results as a strict common-random-number
comparison.

For the next ICC-facing matrix, report at minimum:

- random-pair and repeated-pair workloads separately;
- direct-link PRR quantiles, connected-flow fraction, and cached-route hop
  distribution;
- the same retry, fallback radius, and recovery-attempt budget for the
  mechanism ablation;
- paired seed-level confidence intervals and effect sizes, not only per-method
  means.
