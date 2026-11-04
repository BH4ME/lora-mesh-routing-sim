# MeshEcho-RAC frozen development result

Date: 2026-10-03. Status: failed predeclared joint primary gate. These are
development results, not an ICC manuscript claim or untouched-holdout result.

## Frozen run and integrity

- Mechanism contract: `docs/research/meshecho_rac_design.md`.
- Matched case: `recurring_fading`, 30-s application ACK deadline, 600-s
  generation horizon, 630-s full-TX-cost start window.
- Policies: `meshecho-rac`, `meshecho-rac-repeat`, `meshecho-rac-fr`.
- Seeds: exactly 7001--7020. There are 60 run rows, 816 scheduled unicast
  flows per policy, 2448 flow records, and 15686 action records. Every seed
  has identical application-trace and full case-configuration hashes across
  its three arms. The four artifact SHA-256 values match the manifest.
- Artifacts: `results/meshecho_rac_research_recurring_fading_dev_20261003.*`.
  The manifest records the exact four source/design hashes and the full
  packet-airtime accounting contract.

## Predeclared paired tests

| Comparator | ACK-PDR gain (RAC minus control), nominal 95% CI | Relative full-TX-airtime change, nominal 95% CI | Gate |
| --- | ---: | ---: | --- |
| On-path repeat | +0.0606 [+0.0065, +0.1148] | +23.2% [+8.0%, +38.4%] | Fail: airtime upper bound exceeds +10% |
| Single ACK | +0.1512 [+0.0961, +0.2063] | +6.0% [-3.9%, +15.9%] | Fail: airtime upper bound exceeds +10% |

The author-chosen joint gate requires the ACK-PDR lower bound to exceed
zero **and** the relative complete-network TX-airtime upper bound to stay
below +10% against **both** controls. Both reliability comparisons pass;
both airtime comparisons fail. These intervals are seed-paired, nominal
two-sided 95% intervals and are not multiplicity-adjusted. The manifest
records `rac_joint_primary_gate=false`, so seeds 4001--4040 remain closed.

## Mechanism and limits

Across 20 seeds, RAC logged 4181 eligible corridor events on all 20 seeds
and 3708 physical off-path relay starts. The exposure gate passes, so low
trigger frequency does not explain the failed cost gate. Pooled deadline
ACK counts are 536/816 (RAC), 490/816 (on-path repeat), and 412/816
(single ACK). Mean full-network TX airtime per seed is 43.498 s, 35.807 s,
and 41.491 s respectively. Pooled counts and mean costs are descriptive;
the prespecified inference is the paired seed-level comparison above.

The `windowed_rac_repair_ack_tx` field counts every started marker-0 ACK
hop transmission, including subsequent on-path forwards. The
`rac_repair_tx_events` field counts physical off-path relay starts only;
it is the source of the 3708 count above. Actual complete-network TX
airtime, not either packet count, defines the primary cost gate. Closed-loop
policy decisions can diverge after an early ACK, so individual later flow
differences cannot be attributed causally to a single repair transmission.

### Frozen action-log forensics

An independent read-only join matched all 3708 physical repair starts to
eligible events. Of these, 3647 (98.35%; 190.087 of 193.267 repair-airtime
seconds) targeted the source as the next ACK hop; 2742 of those were on
one-hop DATA paths. None of the source-next candidates canceled because the
source consumes, rather than forwards, a valid ACK. All 473 observed RAC
cancellations were at intermediate hops. This is a structural flaw in the
continuation-only suppression signal, not a backoff-threshold problem.

In hindsight, 3497/3708 repair starts occurred after the source had
already accepted an ACK; 3276 were on 100 F flows accepted through the
original ACK. Candidate devices cannot observe that source-side fact in
the current protocol, so these are **not** realizable savings without a
new signaling mechanism. Forty-three F flows accepted a repair-marked ACK,
and 101 accepted an initial ACK. Simply prohibiting source-next repair
would also remove some observed successful rescues. The saved closed-loop
traces cannot predict the counterfactual effect of a different rule.

The current simulator prototype also uses global `sim.metrics.flows` and
source-side `flow_data_actions` to validate an ACK at intermediate/candidate
nodes. That is not device-local information and prevents a firmware-ready
claim. A future mechanism must derive these checks from locally decoded
packet fields and bounded local observations, and charge any added wire
fields. This flaw does not rescue RAC's failed cost gate; it further limits
the strength of any claim from this prototype.

## Decision

Stop this RAC hypothesis at development. Do not tune candidate backoff,
thresholds, or state rules on 7001--7020 and then call the same cohort
independent validation. A materially different protocol needs a separately
frozen contract and fresh development seeds. No ICC source/PDF, VERSION,
GitHub release, EDAS submission, or holdout run was changed from this result.
