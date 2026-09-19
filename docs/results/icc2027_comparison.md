# ICC 2027 Comparison: MeshEcho 2.1.22

This is the ICC-facing result summary for MeshEcho. Smart-CALM remains a
historical simulator/firmware namespace and is not an ICC protocol, ablation,
primary experiment, or conclusion. The primary estimand is first-discovery
route admission; cache reuse and temporal fading are reported separately.

Raw artifacts are versioned under
`results/meshecho_v2_1_22_icc2027_*`. The primary protocol matrix is
managed flooding, matched source routing, ETX, ETT, min-hop, and MeshEcho.

## Primary calibrated matrix

The matrix uses 50 nodes in an 8250 m square, 600 s runs, mixed traffic at
one flow/min, SF7, 4 dB shadowing, analytical pair-edge PRR >= 0.90, 24
selected pairs at graph distance 2--4, and 20 seeds. The selected graph pairs
are exactly two hops in this calibrated setting. All protocols use the same
2 s discovery window, 600 s route TTL, independent reception stream, and zero
adaptive timeout retries. Values are means; seed-level CSVs and summaries
retain the paired confidence calculations.

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Discovery | Multi-hop route | Mean hops |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Managed flooding | 0.371 | 1.000 | 12.0 | n/a | n/a | n/a |
| Matched source-route | 0.502 | 0.636 | 38.5 | 0.720 | 0.803 | 1.82 |
| ETX metric | 0.661 | 0.741 | 27.6 | 0.861 | 0.843 | 1.91 |
| Fixed-SF ETT metric | 0.661 | 0.741 | 27.6 | 0.861 | 0.843 | 1.91 |
| Min-hop | 0.419 | 0.435 | 26.9 | 0.637 | 0.716 | 1.67 |
| **MeshEcho** | **0.720** | **0.739** | **28.1** | **0.891** | **0.989** | **2.03** |

MeshEcho minus matched source-route is +0.218 ACK PDR with paired 95% CI
[+0.041,+0.395], and -10.3 s airtime with CI [-12.6,-8.1]. Destination PDR
is +0.103 with CI [-0.086,+0.292]. MeshEcho minus ETX/ETT is +0.059 ACK PDR
with CI [-0.108,+0.226], while the min-hop difference is +0.301
[+0.161,+0.441]. The release therefore does not claim a statistically
isolated gain over standard quality metrics.

Every primary row has zero route-cache hits and all selected pairs are two
hops. This is a controlled first-discovery comparison, not a general route
aging or cache-reuse benchmark.

## MeshEcho mechanism attribution

The MeshEcho-only component matrix keeps topology, traffic, discovery budget,
and reception stream unchanged:

| Variant | ACK PDR | Destination PDR | Airtime (s) |
| --- | ---: | ---: | ---: |
| MeshEcho | 0.720 | 0.739 | 28.1 |
| No confidence ranking | 0.572 | 0.635 | 27.7 |
| No route-miss fallback | 0.720 | 0.732 | 28.1 |
| No hop penalty | 0.669 | 0.696 | 28.3 |
| No age penalty | 0.720 | 0.739 | 28.1 |

Paired MeshEcho-minus-ablation ACK deltas are +0.148
[+0.052,+0.244], +0.000 [+0.000,+0.000], +0.050
[-0.029,+0.130], and +0.000 [+0.000,+0.000], respectively. The
no-confidence row is an end-to-end policy-bundle effect: discovery success,
candidate count, and route length also change. Fallback and age results are
workload-specific boundaries, not universal component-null claims.

The seven-node route-conflict audit is the surgical candidate-selection check.
With a 7.5-dB weakened short branch, both candidates appear in 90% of seeds;
MeshEcho selects the longer branch in every observed conflict and improves
ACK PDR by `+0.221 +/- 0.096` over shortest-candidate selection.

## Generalization and temporal fading

These are separate 20-seed strata and are not pooled with the primary matrix.

| Case | MeshEcho ACK/airtime | ETX ACK/airtime | MeshEcho minus ETX ACK | Airtime delta |
| --- | ---: | ---: | ---: | ---: |
| Unconditioned random pairs | 0.404 / 99.5 | 0.308 / 98.1 | +0.096 [+0.056,+0.136] | +1.3 s |
| 100 nodes, 3--5 hops | 0.696 / 160.4 | 0.531 / 156.6 | +0.165 [+0.120,+0.210] | +3.9 s |
| Temporal fading, TTL 600 s | 0.526 / 21.2 | 0.450 / 20.2 | +0.076 [-0.000,+0.152] | +0.9 s |
| Temporal fading, TTL 30 s | 0.324 / 71.3 | 0.256 / 63.3 | +0.067 [-0.023,+0.158] | +8.0 s |

The deep case uses 100 nodes in a 21 km square and graph distances 3--5.
The 21 km calibration was selected before the final run because the 20 km
candidate pool failed the per-seed completeness gate for seed 12. This
failure is retained in the state log rather than silently dropped. The fading
cases use 6 dB blocks every 60 s and intentionally reuse four pairs to expose
cache aging; short TTLs increase repairs and airtime for all route policies.

## Robustness and stress cases

| Case | Managed flooding | Source-route | ETX/ETT | MeshEcho |
| --- | ---: | ---: | ---: | ---: |
| Primary SF7 / 1 min | 0.371 / 12.0 s | 0.502 / 38.5 s | 0.661 / 27.6 s | 0.720 / 28.1 s |
| SF8 / 1 min | 0.434 / 39.2 s | 0.162 / 70.3 s | 0.202 / 57.9 s | 0.405 / 61.7 s |
| SF7 / 4 min | 0.409 / 50.5 s | 0.383 / 151.1 s | 0.450 / 107.6 s | 0.660 / 111.0 s |

The 18 km, 3-seed quality probe passes its pair/link gates but has only
0.178 MeshCore-like discovery success; it is a route-discovery stress
diagnostic, not a neutral protocol ranking.

## Cache-reuse diagnostic

The secondary four-pair unicast workload at four flows/min gives MeshEcho
0.786 ACK PDR, 0.806 destination PDR, and 25.7 s airtime at TTL 600 s, with
32.9 cache hits per run. At TTL 30 s it gives 0.472/0.490 and 88.5 s, with
3.5 cache hits and 18.5 route repairs. These descriptive values are separate
from the zero-hit primary estimand and do not establish a causal age-penalty
effect.

## Reproduction

```sh
OUT_PREFIX=meshecho_v2_1_22_icc2027 \
  bash tools/run_icc_experiments.sh
python3 tools/run_icc_sensitivity_experiments.py \
  --out-prefix meshecho_v2_1_22_icc2027_sensitivity
python3 tools/run_icc_generalization_experiment.py \
  --out-prefix meshecho_v2_1_22_icc2027_generalization
python3 tools/run_icc_cache_experiment.py \
  --out-prefix meshecho_v2_1_22_icc2027_cache
python3 tools/run_route_conflict_experiment.py \
  --seeds 20 \
  --csv results/meshecho_v2_1_22_icc2027_route_conflict.csv \
  --report docs/results/meshecho_v2_1_22_icc2027_route_conflict.md
```

The component-ablation artifact uses
`tools/run_fair_multihop_probe.py` with the five `meshecho-*` protocol names
and the calibrated 50-node connected-multihop parameters. The paper source is
`paper/icc2027/icc2027_lora_mesh.tex`.
