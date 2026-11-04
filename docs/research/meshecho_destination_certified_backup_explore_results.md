# Destination-certified backup: passive 46xxx screen

Date: 2026-10-05. Decision: **GO to a test-first protocol prototype only**.
This is not a treatment effect, a novel-method finding, holdout validation,
or an ICC manuscript result.

## Frozen provenance

- Stock protocol: `meshecho-dhr-flood-ack-delay`; recurring-fading case;
  600-s application generation, 630-s complete-TX accounting, 30-s original
  application deadline.
- One mechanical smoke at seed 46000 used the v2 permit after a direct-CLI
  token repair. The earlier v1 CLI failed before topology and wrote no
  result. V2 smoke manifest SHA-256:
  `2481924958228b44686f1e5c2571175cdb94c15137a8748a8a04fdabe5b24b31`.
- One passive exploration at exactly seeds 46001--46020 used permit SHA-256
  `a4c046bd8bec1f7a6753ce539ff3682138397eb4723b2c92667655411d266ad9`.
  Its manifest is
  `results/meshecho_destination_backup_explore_46001_46020_20261005.manifest.json`,
  SHA-256
  `c51e55cbac2c8a5ae00de23001f008b3402360c3357430ff212d0f213ed9a385`.
- Independent read-only audit matched the sidecar, ten artifact hashes, ten
  input hashes, archived permit, smoke predecessor, all 20 seeds, case and
  deadline. The official no-rerun archive validator passed; smoke strict
  replay passed. Exploration capture recorded stock/observer parity and an
  exact within-run replay for every seed. The independent audit did not rerun
  the exploration cohort.

## Necessary opportunity screen

| Prespecified 2-s primary-gate quantity | Observed passive value |
| --- | ---: |
| Scheduled unicasts, all-flow denominator | 872 |
| Complete network transmissions / airtime | 13,338 / 1084.446208 s |
| Direct initial R sends / nominated direct R sends | 148 / 130 |
| Nominations with backup age <=120 s | 99 |
| Failed primary and current DATA decoded by nominee | 36 in 17 seeds |
| Of those, proxy PRR >=0.5 and nominal deadline feasible | 36 |
| Stock-ACKed F rescues eligible for pre-guard cost substitution | 30 |
| Stock deadline-unACKed source-ACK headroom | 6/872 = 0.688% |
| Optimistic equal-seed net whole-network airtime fraction | 5.5283726% |

The prespecified exposure gate requires at least 20 exposed flows across ten
seeds and at least 16 proxy/deadline-feasible. The cost gate requires an
equal-seed optimistic net fraction >=5%. Both necessary gates pass. The cost
gate clears by only 0.528 percentage points, and only 11/20 individual seeds
exceed 5%. A descriptive t interval for the *opportunity* mean is roughly
3.67--7.38%, crossing the gate; it is not a confidence interval for a new
protocol's saving.

The cost calculation independently reconstructed from archived physical
transmissions and LoRa ToA is 68.854784 s of creditable stock F-recovery
airtime minus 0 s extra F-ACK ToA (190 required extra bytes remain within the
same LoRa symbol step), 0.506880 s for 594 R nomination bytes, 3.695616 s
for all 36 nominal relay DATA starts, and 3.087360 s for two-hop reverse
ACKs on the 30 credited F substitutions. The optimistic margin is
61.564928 s. Dividing pooled totals gives 5.6770845%; the prespecified
equal-seed mean is 5.5283726%. All 48 successful-primary flows whose nominee
decoded the R DATA also had a locally decoded destination ACK within 0.5 s,
so the stock-trace nominal redundant-start count is zero. The 0.5-s
sensitivity matched the 2-s primary screen in these saved traces; it is not
a separate opportunity to choose a timer after seeing results.

## Interpretation and next gate

The observer did not send a nominated packet, change ACK bytes, alter queue
order, create collisions, or test any feedback/relay protocol. Its relay-to-
destination PRR is an offline oracle proxy unavailable to a device. The
destination's stock F ACK was built on first decode, so the reported two-hop
alternative was not actually in that ACK. Actual ACK construction at the
2-s window close, charged fields, relay queueing, physical-start cancellation
and returned ACK reception may erase the narrow cost margin.

Freeze an implementable device-observable packet/state contract and test it
first. Compare the complete candidate against fixed-2-s F, same-byte/no-
forward, unconditional nominated relay, local/overheard selector, IOMC-like
overhearing, fixed source recovery and two-hop-F/LPR-like controls on fresh
paired development data. Measure original-deadline source ACK, destination
delivery, complete network airtime/energy, latency, bytes, queueing, and
state. Only a genuinely positive same-budget causal result can justify an
untouched holdout and subsequent ICC method/results rewrite. Existing 46xxx
observations are exploratory and may never serve as untouched confirmation.
