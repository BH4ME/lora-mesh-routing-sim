# MeshEcho source-action public diagnostic: 49301--49310

Date: 2026-10-05. Status: independently audited exploratory result, not an
ICC claim, confirmatory development result, or untouched holdout.

## Provenance and scope

The prospectively specified seven-arm `recurring_fading` run was executed
once on seeds 49301--49310. The archive prefix is
`results/meshecho_source_action_public_49301_49310_20261005`. Its manifest,
six JSONL files and five saved source hashes passed independent read-only
checks. All seven arms share 399 scheduled application identities (70
seed-arm runs; 2,793 flow and joined-flow rows). The auditor reconciled
16,935 actions, 35,574 physical TX records, 54 paired intervals, ACK and
delivery fields, packet costs, and case/trace pairing. No TX was outside the
declared window. The 28 focused tests and complete 1101-pass, one-skip
regression preceded the formal run.

## Exploratory all-flow outcomes

The ACK and delivery counts use each flow's original 30-s deadline. Airtime
is complete-network physical TX time summed over the ten runs per arm.

| Arm | Source ACK / 399 | Delivered / 399 | Network TX airtime, s |
| --- | ---: | ---: | ---: |
| Old DCB F/R/D | 376 | 397 | 500.36 |
| D-to-F/R | 373 | 399 | 395.95 |
| Useful-data F at old D trigger | 367 | 397 | 451.50 |
| Reversible trial | 368 | 398 | 422.86 |
| Blind switch | 368 | 398 | 422.86 |
| Trial without switch | 374 | 399 | 421.14 |
| Fixed-2-s F-ACK contextual control | 381 | 398 | 497.66 |

D-to-F/R versus old DCB has an equal-seed mean relative airtime difference
of -20.97% (descriptive 95% interval [-30.88%, -11.06%]) and source-ACK
difference of -0.73 percentage points ([-3.33, +1.87]). Its ACK
noninferiority has **not** been established; on seed 49310 its ACK rate is
8.33 percentage points lower. Trial is 11.11 percentage points worse than
old DCB on seed 49304 while spending 7.75 s more network airtime there.

Old DCB made 35 D decisions, 34 because of route aging and one cold start.
All 35 physically sent RREQ and obtained candidate DATA; none fell back
after an RREP discovery timeout. Its RREQ/RREP physical airtime was 103.24 s
over ten seeds, 20.6% of old DCB total. This is gross control cost, not the
counterfactual saving from removing D. D-to-F/R reduced complete-network
airtime by 104.41 s in aggregate, but also changed subsequent closed-loop
route and feedback state.

Trial and blind had identical first physical source actions, paths, source
ACK and destination delivery on all 399 shared flows. Their 4,651
normalized physical TX frames also matched one-for-one. Trial state events
are therefore not evidence of a distinct on-wire benefit in this workload.
Trial versus no-switch did differ, including adverse ACK differences.

## Interpretation and next decision

The same application identity across old DCB and a replacement arm is not
the same pre-decision network state. For example, the 35 old-DCB D flow IDs
begin with 34 R/one F in D-to-F/R, but 30 F/five R in trigger-F. The
trigger-F arm also consumes a source token and updates `last_discovery_at`
at the D trigger whereas the F/R replacement does not. Thus the seven-arm
contrasts neither identify an individual D/R/F treatment effect nor justify
an online route-age threshold.

Reject both the reversible trial and a blanket D-to-F/R replacement as
finished core algorithms. Retain the simulator, PHY, accounting and old
arms as controls. Prospectively compare D, old-route R and useful-data F
from an identical pre-send source/network prefix with matched bookkeeping,
feedback and recovery budgets on new nonreserved seeds. A future online
controller must use only device-visible state, outperform simple same-wire
controls under paired ACK/delivery and charged network-cost gates, and then
pass untouched validation before the ICC manuscript is rewritten.
