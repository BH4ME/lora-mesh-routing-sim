# ICC 2027 Comparison: MeshEcho 2.1.16

This is the current ICC-facing result summary. The primary claim uses the
calibrated connected-multihop matrix, not the easier repeated-pair matrix. Raw
CSV and long-format summaries are versioned under
`results/meshecho_v2_1_15_icc2027_*` (the verified simulation artifacts reused
by the 2.1.16 paper-only revision).

## Primary calibrated matrix

The matrix uses 50 nodes in an 8250 m square, 600 s runs, mixed traffic at one
flow/min, SF7, 4 dB shadowing, analytical pair-edge PRR >= 0.90, 24 selected
pairs at graph distance 2--4, and 20 seeds. MeshCore-like and CALM use the
same 2 s discovery collection window. Values are means with two-sided 95%
confidence half-widths where shown.

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Discovery success | Multi-hop route fraction | Mean cached hops |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MeshCore-like | 0.537 +/- 0.081 | 0.679 +/- 0.093 | 38.5 +/- 5.3 | 0.741 | 0.775 | 1.80 |
| MeshEcho (CALM) | **0.720 +/- 0.115** | **0.739 +/- 0.115** | **28.1 +/- 4.7** | 0.891 | 0.989 | 2.03 |
| Smart-CALM | 0.563 +/- 0.088 | 0.630 +/- 0.100 | 28.6 +/- 4.7 | 0.801 | 1.000 | 2.13 |
| Smart-CALM, no fallback | 0.561 +/- 0.081 | 0.607 +/- 0.096 | 28.0 +/- 4.5 | 0.811 | 1.000 | 2.11 |
| Smart-CALM, no confidence | 0.382 +/- 0.122 | 0.470 +/- 0.133 | 27.8 +/- 4.6 | 0.589 | 0.730 | 1.61 |

The link-regime gate passed all 20 seeds: selected graph distance was 2.0
hops, 16.0% of direct links were below 0.99 PRR, and 4.6% were below 0.50.
Smart-CALM minus no-confidence was +0.181 ACK PDR with paired 95% CI
[+0.094,+0.268]. Smart-CALM minus no-fallback was +0.002 with CI
[-0.020,+0.024], so recovery and confidence effects are not collapsed into one
claim.

## Legacy robustness matrix

The release also reruns repeated-pair mixed traffic, stronger shadowing, and
higher offered load for regression and contention analysis. These scenarios
use the 3000 m square and are explicitly not neutral multi-hop benchmarks.

| Scenario | MeshCore-like ACK PDR | MeshEcho ACK PDR | Smart-CALM ACK PDR | MeshCore airtime (s) | MeshEcho airtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mixed, 6/min | 0.650 | 0.728 | 0.936 | 898 | 847 |
| Shadow 6 dB, 6/min | 0.646 | 0.745 | 0.930 | 904 | 846 |
| Mixed, 10/min | 0.457 | 0.585 | 0.870 | 1353 | 1255 |

Repeated pairs favor route reuse and direct-link PRR is largely saturated, so
these rows are retained as sensitivity evidence rather than as the main
confidence-aware routing result.

## Quality-gate stress probe

The 18 km, 3-seed connected-multihop probe passed the per-seed gate with 24/24
pairs, mean graph distance 2.014 hops, 64.1% of direct links below 0.99 PRR,
and 44.5% below 0.50 PRR. MeshCore-like discovery success was 0.178. This is
a route-discovery stress diagnostic; its low discovery rate must not be read as
an isolated data-plane ranking.

## Reproduction

```sh
OUT_PREFIX=meshecho_v2_1_16_icc2027 bash tools/run_icc_experiments.sh
```

The script writes the four legacy matrices, the quality-gate CSV/Markdown
report, and the calibrated multi-hop CSV/Markdown report. The paper uses
`paper/icc2027/icc2027_lora_mesh.tex` and is compiled with Tectonic.
