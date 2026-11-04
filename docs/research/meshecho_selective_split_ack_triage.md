# Selective split-ACK corridor triage

Date: 2026-10-05. Status: exploratory NO-GO as the next MeshEcho-SR core.
This read-only screen uses the already-opened 46001--46020 passive DHR
archive. It is not a counterfactual protocol experiment, a fresh validation
cohort, or an ICC result.

## Hypothesis and observable mechanism

An accepted F ACK could certify a direct primary path `(s,d)` and a
physically decoded alternative `(s,r,d)`. A later nominated direct R DATA
could ask the destination to return its ACK on `(s,r,d)` only when the
current DATA reception is weak. The relay's local decode of that ACK
would suppress its pending conditional DATA backup. The source would
confirm the direct DATA route, not confuse the reverse ACK corridor with
a forward DATA route. Every mode bit, relay/epoch field, hop and retry
would require complete wire/airtime charging.

This is not a first-use claim. DSR permits an ACK to return on another
multihop path; ACK/signal-based routing and ACK-gated opportunistic relay
forwarding also have verified precedents in
`meshecho_feedback_prior_art_boundary.md` and
`meshecho_destination_certified_backup_screen.md`. The candidate would
need a joint effect beyond same-wire direct ACK, unconditional alternate
ACK, same-path ACK repeat and DCB-only controls.

## Audited passive exposure

The archived `results/meshecho_destination_backup_explore_46001_46020_20261005`
manifest, sidecar, ten artifact hashes, frozen source bundle, authorization
and smoke predecessor were checked. Its 130 nominated direct initial R
flows include 99 with backup certificate age at most 120 s. Of these 99,
52 physically delivered the direct DATA to the destination. Forty-nine
received an accepted initial direct ACK; three did not. Across all 130,
66 direct DATA receptions produced 62 initial direct ACKs and four misses.
All four ACK-miss cases had a nominated relay that decoded the DATA and
the direct destination ACK within 0.5 s, so the current DCB ACK gate would
nominally suppress its backup. The 3/99 age-qualified cases are the
maximum observed direct-ACK-miss exposure that a different reverse ACK
path might affect; they are not evidence that that path would succeed.

In contrast, among the 47 age-qualified direct DATA failures, the nominee
decoded 36 across 17 seeds. Thirty of these 36 eventually obtained a
stock source ACK, leaving six final ACK-headroom cases. The previously
published 46xxx optimistic airtime substitution screen concerns this
forward-DATA-failure branch and is not a measured DCB benefit.

No current DATA-reception SINR or margin was saved in this archive. The
stored receiver IDs and collision-free oracle relay-link PRRs cannot be
substituted for a destination-local 0/1/3 dB trigger or used to calibrate
it without a new passive capture. The direct-ACK miss count is too small
to justify replacing the full core with an unvalidated longer ACK path.

## Decision

Do not implement or claim the split-ACK corridor as the next ICC core on
this evidence. Preserve it as an optional later factorial sensitivity
question only if a separate, prospectively captured receive-quality
signal and same-budget direct-ACK comparison justify it. Prioritize a
source/feedback/recovery rule that addresses the more exposed failed
direct-DATA branch, while retaining old D/F/R and fixed-2-s F controls.
Do not open 47xxx/48xxx, change the ICC manuscript, bump VERSION, or
publish based on this screen.
