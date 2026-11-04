# DHR source-signal screen (exploratory)

Date: 2026-10-04. Status: exploratory screen complete. This is an analysis of the
already inspected fixed-F DHR development cohort, not a new population trial
or predictive validation. Reserved holdouts are excluded.

## Denominator and timing

The input is solely the frozen `meshecho_dhr_research_recurring_fading_dev_20261004`
flow/action JSONL, seeds 9001--9020, **`meshecho-dhr-none` arm**. This arm has
no rescue payload, so its R outcomes are unmodified by a recovery action.
Of 803 scheduled unicasts, 512 had actual `source_action=R`; two were fallback
R sends after a D decision and are excluded. The primary denominator is **510
initial `decision=R` confirmed-route sends**, spread over 20 seeds and 80
source-destination pairs. By the original 30-s deadline, 172/510 lacked a
source ACK and 150/510 lacked destination delivery. Of the 172 ACK failures,
22 reached the destination. All 172 failing R decisions have a guard event,
and `guard_time - 15 s` equals decision/enqueue time to floating-point
precision. There is no explicit initial-R TX timestamp for the 338 ACKed
sends, so timing there remains an enqueue-time proxy.

At each R decision, replay only preceding source-visible events for that
source-destination pair: latest confirmed-route commit time and path, latest
accepted ACK that refreshes the current route, and recent R ACK timeouts.
This yields route age, last-ACK age, prior R miss streak, and cached path hop
count **before the current send**. A prior accepted ACK's delay is reconstructed
as ACK time minus application enqueue time; firmware would need to retain that
bounded local value to use it. All five fields were available for all 510
decisions. The replay matched all logged `route-ack-misses` F decisions, and
action events were time ordered. The current SR policy prevents an R decision
at two or more prior R misses, so the observed R cohort has miss streak 0 or 1.

## Descriptive signal screen

| Pre-decision group | N | No source ACK | No destination delivery |
| --- | ---: | ---: | ---: |
| Prior R miss 0 | 408 | 111 (27.2%) | 92 (22.5%) |
| Prior R miss 1 | 102 | 61 (59.8%) | 58 (56.9%) |
| Last ACK age <60 s | 254 | 71 (28.0%) | 58 (22.8%) |
| Last ACK age 60--119 s | 187 | 68 (36.4%) | 62 (33.2%) |
| Last ACK age >=120 s | 69 | 33 (47.8%) | 30 (43.5%) |
| Route age <60 s | 106 | 29 (27.4%) | 22 (20.8%) |
| Route age 60--119 s | 125 | 53 (42.4%) | 47 (37.6%) |
| Route age 120--179 s | 103 | 42 (40.8%) | 39 (37.9%) |
| Route age >=180 s | 176 | 48 (27.3%) | 42 (23.9%) |
| Cached path 1 hop | 183 | 102 (55.7%) | 91 (49.7%) |
| Cached path 2 hops | 210 | 46 (21.9%) | 41 (19.5%) |
| Cached path 3 hops | 117 | 24 (20.5%) | 18 (15.4%) |

The simple local rule `last-ACK age >=120 s OR prior R miss=1` separates
68/123 ACK failures (55.3%) from 104/387 (26.9%). Hop count separates risk
within **both** rule groups: below the rule threshold, one-hop routes had
57/123 failures (46.3%) versus 47/264 (17.8%) for longer routes; above it,
45/60 (75.0%) versus 23/63 (36.5%). One-hop minus longer-route ACK-failure
rate was positive in 17/20 seeds (mean within-seed gap 36.8 percentage
points). For destination non-delivery the corresponding within-seed gap was
positive in 17/20 seeds (mean 33.4 points). Thus hop count contains a clear
*development-cohort association* beyond this simple age/miss rule. The
route-age bands are nonmonotonic and are affected by the existing route
selection policy.

Prior ACK delay gave 135/333 failures (40.5%) below 0.3 s, 15/85 (17.6%)
at 0.3--1 s, and 22/92 (23.9%) at >=1 s. All 183 one-hop routes fall below
0.3 s; within two-hop routes, the <0.3-s and >=1-s groups were 33/150
(22.0%) and 13/54 (24.1%). Delay therefore adds no clear independent
separation here; it largely proxies hop count. Among the 172 R ACK failures,
150 (87.2%) were forward non-deliveries. Hop count does not cleanly distinguish
forward loss from delivered-but-unACKed loss within that guard-failure subset:
the non-delivery counts were 91/102, 41/46, and 18/24 for one-, two-, and
three-hop paths.

## Decision and limits

**No new source rule is justified by this screen alone.** The one-hop signal
is a worthwhile hypothesis for a future, frozen mechanism, but hop count is
also a simple threshold feature, not by itself a novel decision principle.
The cohort contains only 80 repeatedly sampled pairs in one recurring-fading
configuration; topology, path selection, packet airtime, and per-pair fading
can confound the hop association. R decisions are selected by the current SR
policy, and the R subset excludes states with two prior misses. Reconstructing
application-enqueue-to-ACK delay does not establish a calibrated link-quality
estimate. The no-rescue observations estimate risk under no rescue; they do
not estimate whether R repeat, F rescue, or another action would be better
for a particular flow, nor their full-network airtime trade-off. The DHR
development joint gate already failed and remains failed.

Any hop-aware successor needs a specified decision objective and a new named
development cohort. It must compare against **the same-trigger fixed R,
fixed F, age/miss-only, and hop-only controls**, with complete-network airtime,
source ACK, and destination delivery endpoints. Independent scenario and
measurement calibration would be needed before a general reliability claim.

## Progress and errors

- Scope/provenance, trace replay, and descriptive comparison complete. No
  population runs, source changes, paper changes, or holdout reads occurred.
- The planning skill's catch-up helper required `python3` because `python`
  was not on PATH. The `python3` invocation completed without output.
