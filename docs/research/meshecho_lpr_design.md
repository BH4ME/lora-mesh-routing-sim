# MeshEcho-LPR: localized payload repair (development contract)

Date: 2026-10-03. Status: implemented simulator prototype, unvalidated hypothesis. LPR replaces the
separate RREQ/RREP-before-DATA refresh in MeshEcho-SR/MAG; it is not a
validated protocol or an ICC paper result. Existing F (useful-DATA flood),
R (confirmed source route), PHY/collision model, and ACK-confirmed route
commit remain the comparison infrastructure. Local repair, opportunistic
forwarding, and DATA-first route learning have prior art; novelty and a
performance advantage must be established, not assumed.

## Evidence motivating the hypothesis

The corrected-timing MAG development revision 3 made 71 candidate returns
on seeds 3001--3020. In the action log, 49 candidate paths are the old path
with exactly one off-path node inserted between two consecutive old nodes;
46 of 66 ACK-committed D candidates have that shape. Of the 49 candidates,
48 change a direct old edge `[u,v]` to `[u,w,v]`. These are path-shape counts,
not an attainable repair success estimate: MAG found those paths using a
network-wide RREQ/RREP process, and the local relays may be unavailable or
collide. They were inspected before LPR was designed and cannot be used as
independent evidence. Reproduction: filter
`results/meshecho_mag_research_recurring_fading_dev3_20261003.actions.jsonl`
to `protocol=meshecho-mag`, `event=candidate/commit`, and test single-node
insertion of the returned path into `old_path`.

## On-wire and state contract

- DATA/FLOOD from the LPR family carry the quantized minimum *successfully
  received* forward SNR margin and its receiving-hop index. Each is one
  modeled byte; `127` means unmeasured margin and `255` means no hop index.
  A lower margin replaces both values; a tie retains the earlier hop.
  The destination copies both into the reverse application ACK. The source
  updates only from an accepted, in-deadline ACK for the current confirmed
  path. A missing ACK does not localize a failed hop or diagnose collision.
- A repair DATA carries a one-byte target-hop index. This is the index of
  successor `v` in the *old* confirmed path; predecessor is `u`. Only a
  confirmed path with at least one edge and room for one extra relay under
  `max_hops` is eligible. The source has at most eight destination states.
- Each node maintains an eight-entry LRU table of recently decoded senders,
  with last-heard time and measured SNR margin. An off-path relay `w` is
  eligible only if it decoded `u`'s repair DATA, is not on the old path, and
  decoded a real transmission from `v` within 300 s with nonnegative SNR
  margin. This is passive local evidence, not a simulator topology query or
  proof that `w` can currently reach `v`.
- The source uses only its own prior sends, accepted ACK margins/indexes,
  route/PHY state, a one-token-per-ten-sends budget, and 300-s per-destination
  cooldown. No coordinates, hidden PRR, future traffic, global airtime, or
  destination-delivery flag enters a decision.

## Action and forwarding contract

The initial trigger deliberately matches MAG's observed low/falling-margin
and repeated-demand rule to isolate the *acquisition mechanism* in the first
comparison: with an ACK-confirmed route, risk is a latest margin at or below
3 dB, or a decline of at least 3 dB to at most 6 dB; at least two earlier
local sends within 300 s, a token, cooldown, a valid hop index, sufficient
hop budget, and a PHY-aware 30-s application deadline are required. This is
a starting rule, not an optimized threshold or guaranteed cost bound. A
healthy route is R; no route or two consecutive source-ACK misses are F.

On a repair action P, the current application DATA follows the old route to
`u`, then `u` broadcasts that same payload once for the segment toward `v`.
`v` can accept this direct copy. Each eligible `w` schedules at most one
delayed rebroadcast; it inserts itself between `u` and `v` in the carried
source path and sends toward `v`. A relay cancels its pending copy if it
decodes an earlier candidate or a `v` continuation/ACK for the flow.
Hidden terminals can still produce several transmissions, so no global
one-relay bound is claimed. `v` accepts the first valid direct or one-relay
copy, suppresses later duplicates, and forwards the useful DATA along the
old suffix. The destination delivers once and returns an ACK along the
*realized* path. There is no RREQ or RREP for P and no same-flow rescue send.

The source accepts a P ACK only if the flow, deadline, and old-path relation
match: its path must be exactly the old path, or that path with one off-path
node inserted at the selected edge, within `max_hops`. Only that ACK may
replace the cached route. A destination delivery without a returned ACK
does not commit. A P timeout leaves the old path until the existing failure
rule triggers F on a later application flow. Packet sizes, all DATA/ACK
transmissions, collision duration, and modeled TX energy use actual frame
lengths. The index and repair bytes are charged on every relevant hop.

## Tests and falsification

Implement one red/green vertical slice at a time: indexed ACK feedback and
byte accounting; a deterministic diamond-topology direct and one-relay P;
no-oracle neighbor eligibility; duplicate/cancellation behavior; wrong,
late, and missing ACK rejection; path-length and deadline boundaries. Keep
the old SR and MAG policies intact as explicit comparators.

Matched controls pay the same margin/index feedback bytes: F/R-only,
same-trigger full useful-DATA F, equal-token periodic P, and a P policy
that chooses a deterministic non-observation-based edge. MAG-D and the
product-inspired common-ACK Meshtastic/MeshCore models are descriptive
external comparisons, not firmware parity claims.

The four control policies are fixed before LPR development runs:

- `meshecho-lpr-fr` uses R on an ACK-confirmed route and F on the same
  cold/stale/two-ACK-miss conditions as LPR, but never attempts P. It still
  transmits the same margin and hop-index feedback bytes.
- `meshecho-lpr-trigger-f` evaluates exactly LPR's risk, repeated-demand,
  token, cooldown, index, hop-budget, and deadline gate. When LPR would P,
  it spends the same token/cooldown and sends the current useful DATA by F;
  otherwise it takes LPR's F/R action. It does not send a repair frame.
- `meshecho-lpr-periodic` substitutes a confirmed-route age of at least
  180 s for the measured-risk trigger, with the same demand, token,
  cooldown, valid-index, hop-budget, and deadline conditions; when due it P
  at the ACK-indexed edge. It pays the same feedback bytes and P frame cost.
- `meshecho-lpr-unobserved-edge` uses LPR's exact P trigger and token budget,
  but on P chooses one old-path edge uniformly using a seed/flow-keyed
  deterministic draw independent of ACK margin or hop index. It retains the
  feedback bytes to isolate *use* of localization, not its wire overhead.

All five policies share the same F/R primitives, 30-s deadline, route TTL,
PHY, per-node relay eligibility, source application trace, and full-packet
accounting. The primary reliability/cost gate applies only to LPR versus
F/R-only and same-trigger F; periodic and unobserved-edge comparisons test
the claimed source of benefit.

Report per-seed scheduled
flows, in-deadline source-ACK and destination PDR, aggregate TX airtime,
window-consistent repair/control packet counts, collisions, delay tail,
route switches, repair exposures, and candidate wins. Keep the 30-s flow
deadline and generation horizon; charge complete packets starting within
the fixed 600+30-s drain window. The existing unwindowed transmission
counts and raw RX energy must not be presented as if they share that window.

The author-chosen reliability/cost gate is a positive paired 95% lower
bound on ACK-PDR gain and a paired 95% upper bound below +10% relative
whole-network TX airtime against **both** F/R-only and same-trigger F.
If localization is claimed, compare against periodic P and the
non-observation edge ablation with the same packet/relay/token budget;
describe any null result. This is not an ICC acceptance rule. The scenario
and analysis contract must be frozen before the untouched 4001--4040
holdout. Use fresh development seeds 5001--5020 for implementation
decisions; the earlier 3001--3020 traces are exploratory selection data.
For a mechanism-specific claim, the 20-seed development set must expose at
least 20 P decisions and 10 ACK-confirmed inserted paths; otherwise treat
even a passing aggregate gate as under-exposed and report it as inconclusive.
These are author-chosen evidence sufficiency thresholds, not significance
tests or venue rules; retain the counts and any failure in the results.
The unconditioned 18-km random-pair case tests cold-start generality but
rarely exposes repair, so it cannot by itself validate LPR. Failure on
cost, delivery, sparse exposure, or the matched controls is a negative
result, not a reason to tune on the holdout.

Before any manuscript novelty claim, verify relevant
local-repair/opportunistic-LoRa prior art and distinguish this exact
feedback/repair contract. No radio deployment or energy measurement has
yet validated the model.

## Prior-art boundary

Bypass Routing (Sengul and Kravets, *Ad Hoc Networks*, 2006,
DOI 10.1016/j.adhoc.2004.10.004) already uses one-hop bypass, overheard
neighbor state, buffered DATA salvage, and destination confirmation. AODV-BR
(Lee and Gerla, WCNC 2000, DOI 10.1109/WCNC.2000.904822) uses overheard
backup forwarding; Neighborhood Aware Source Routing (Spohn and
Garcia-Luna-Aceves, MobiHoc 2001, DOI 10.1145/501416.501419) repairs
source routes with neighborhood state; ExOR (Biswas and Morris, SIGCOMM
2005, DOI 10.1145/1080091.1080108) coordinates opportunistic forwarding.
Dynamic Multi-Hop RT-LoRa (Tran et al., *Sensors*, 2022,
DOI 10.3390/s22093518) is a LoRa dynamic-topology comparison with hardware
evaluation. Do not claim any of those ingredients alone is new. The
candidate distinction is their particular source-triggered,
ACK-indexed, pre-failure, query-free useful-DATA repair combination under
LoRa airtime and deadline accounting; that combination still requires
broader literature verification and positive matched evidence.

The fixed five-policy suite supports only comparisons within this simulator
family. If LPR survives development, add a separately matched local-query
bypass comparator before claiming an advantage over established local
repair; otherwise state explicitly that such superiority was not tested.
