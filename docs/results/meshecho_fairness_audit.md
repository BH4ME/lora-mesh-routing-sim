# MeshEcho Simulation Fairness Audit

Date: 2026-09-04

This audit records the fairness boundary of the packet-level evaluation used
by the ICCT draft. It distinguishes common experimental inputs from
protocol-level advantages that are intentionally or unintentionally present in
the current matrix.

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

The following claims are not supported by the current matrix:

- universal superiority over flooding or source-route caching;
- average confidence-ranking gains in arbitrary random topologies;
- calibrated multi-hop deployment performance;
- a fully budget-matched comparison of all recovery mechanisms.

## Required Follow-Up

The next evaluation should add a random-pair workload, calibrate a genuinely
multi-hop regime using direct-link reception distributions, and compare either
with recovery disabled for every protocol or with the same retry and fallback
budget for every protocol. These changes should be reported as a new
versioned experiment line rather than silently replacing the current results.
New matrices should enable `--independent-rng-streams`; keyed per-event draws
would be a stronger future option before treating same-seed results as a
strict common-random-number comparison.

For the next ICC-facing matrix, report at minimum:

- random-pair and repeated-pair workloads separately;
- direct-link PRR quantiles, connected-flow fraction, and cached-route hop
  distribution;
- the same retry, fallback radius, and recovery-attempt budget for the
  mechanism ablation;
- paired seed-level confidence intervals and effect sizes, not only per-method
  means.
