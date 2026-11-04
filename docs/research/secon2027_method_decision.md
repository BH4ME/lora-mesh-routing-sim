# Development method decision before formal validation

Decision date: 2026-11-04; prospective task-book §9 record. **Retain the corrected fixed MeshEcho-CPR policy; introduce no new algorithm candidate in this round.** The purpose of the formal study is to measure its reliability/airtime tradeoffs and isolate existing components, including conditions in which it loses. This is not a performance-upgrade claim.

## Evidence available at this decision

Only the completed development pilot v2 is used: plan `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7`, snapshot `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`, exposed development seeds2027000–2027002. Frozen tests161passed, all72runs/audit complete. The original v1 implementation failure and all partial evidence remain archived and excluded from paired performance summaries. Three seeds support diagnosis, not stable confirmatory inference or a claim of significance.

S3-default seed means show CPR ACK-by-deadline0.3262 and airtime211.9265s, compared with MC-like0.4272/85.2791s and legacy ME0.3769/95.7587s. CPR physically starts94 repeats and80.3333 recoveries per seed on average. In S1/S2 CPR has higher descriptive ACK fractions than these routed models but also higher airtime. There is no across-scenario dominance. Matched/default CPR and legacy ME have identical effective inputs and are not independent extra replication.

## What the loss evidence actually supports

Across the three S3-default CPR runs there are 475 scheduled flows, 281 timely destination deliveries and 156 timely source ACKs. Thus194 flows lack timely DATA delivery, and125 are delivered on time without timely source confirmation. These are two material failure populations;194/319 unconfirmed flows lack timely DATA, while125/319 had timely delivery. The distinction is outcome based, not an exclusive causal label for every unsuccessful hop.

At intended routed DATA next hops the RX ledger contains357 capture-collision,102 half-duplex,23 PRR-failure and1453 decoded opportunities. Intended ACK hops contain114 capture-collision,27 half-duplex,13 PRR-failure and1024 decoded opportunities. A flow can contribute multiple opportunities, and FLOOD receiver opportunities have no unique intended next hop. These counts show collision/half-duplex exposure on both directions; they do not identify a unique causal loss for each flow or prove how a different policy would behave. All-listener loss totals would overcount irrelevant receivers and are not used for that inference.

CPR starts282 repeats and241 recoveries in these runs;42 recoveries start after the destination has already received the flow. This is observable confirmation delay/loss ambiguity at the source, not proof all42 recoveries were useless: the source lacks remote-delivery knowledge. The source sees its own flow state, received ACKs and local radio opportunity, not the offline destination flag.

Mean request waiting times are0.3822,0.3237,0.4129s; corresponding95th percentiles are1.0470,1.0346,1.0481s. Request statuses include6574 physical starts,544 canceled requests and11 protocol-no-start records. No queue-expiry-specific request reason appears in this population; flow timeouts, state-capacity refusal and route invalidation must be reported separately. In particular, `DROP_DEADLINE_INFEASIBLE` plus reason `stale-route-generation` does not establish a lack of time. The evidence does not justify calling queue expiry the dominant failure cause. Zero relay-capacity evictions also does not prove that occupancy never reached its configured bound; peak occupancy is unobserved. Successful ACK cancellation occurs80times.

S2-default CPR has11 initially carried paths intersecting active fault edges and19 actual intended-hop transmissions at active fault edges. The static alternative remains6hops within the six-hop limit. This establishes real fault exposure as well as repeat/recovery activity, not guaranteed over-air recovery or its isolated benefit. Full raw mechanism diagnostics retain per-seed details and failures.

## Choice and rejected scope expansion

A bounded local-queue/busy-state backoff or admission policy is a plausible future candidate for S3. This pilot does not establish a local threshold that distinguishes cases in which waiting saves airtime from those in which waiting loses useful retries or deadline budget. Counterfactual destination-success labels are unavailable to an implementable controller. Tuning a new threshold on these three development seeds would also add a new behavioral policy before the existing repeat/recovery/cancellation contributions have been isolated.

For this round, none is implemented or evaluated. Retaining the fixed policy is a deliberate scope/identification choice: the predeclared clean no-repeat, no-recovery and ACK-cancel-off controls can quantify their actual cost and benefit under the same common environment. The formal evaluation must preserve S3 adverse results, show per-scenario tradeoffs and uncertainty, and may conclude that fixed CPR is unsuitable for high offered load. It must not claim universal efficiency, current-product superiority or demonstrated congestion adaptation. If the resulting contribution is insufficient for a submission, the deliverable must say so instead of adding post-validation tuning or swapping validation seeds.

## Prospective boundaries

The one-time formal matrix will include20fresh registered seeds, allS1/S2/S3 primary models in both regimes, three controls inS2/S3matched, and the finite deadline/drain axis10/30/60s onS2matched. No source method/parameter selection follows formal exposure. All planned runs and negative outcomes remain; failure to meet a prospective exposure criterion limits interpretation and does not remove a seed or trigger a replacement cohort. No capacity sensitivity is selected because the development pilot has zero capacity evictions and the study makes no memory-benefit or optimal-capacity claim; future observed evictions remain reported as a limitation.
