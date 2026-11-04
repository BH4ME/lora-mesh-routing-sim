# MeshEcho-CLAR: source-closure-assisted local ACK repair

Date: 2026-10-03. Status: implemented, pre-development evidence contract.
CLAR is a new MeshEcho-SR reverse-confirmation hypothesis, not an ICC result,
firmware implementation, or verified novelty claim. The failed LPR
5001--5020, DPA 6001--6020, and RAC 7001--7020 cohorts informed this design;
none may serve as independent CLAR validation. The 4001--4040 holdout remains
unopened. Freeze this contract and source hashes before the development run.

## Question and predicted mechanism

Can a DATA-conditioned off-path ACK repair improve deadline source-ACK
delivery versus both a single ACK and an on-path repeat without increasing
complete-network TX airtime by more than a predeclared 10% upper-confidence
bound? RAC could rescue ACKs but failed that cost gate because 3647/3708
repair starts targeted the ACK-terminating source and could not hear a
forwarded ACK from it. CLAR makes that terminal state explicit: after the
source accepts its first valid F ACK, it sends one one-hop ACK_DONE. Only a
candidate that actually decodes the matching DONE cancels its pending repair.
An intermediate-hop candidate still cancels on a locally decoded on-path
ACK continuation. If no closure is decoded before its timer, it may repair.

CLAR does not change the F/R source decision, initial FLOOD, destination's
first realized-path ACK, route commit, PHY, or application schedule. It can
rescue only an ACK after destination DATA delivery; it cannot make an
undelivered DATA packet arrive. Its route cache commits the realized DATA
path, not the off-path ACK transport relay.

## On-wire protocol and local predicates

- Each F ACK carries the existing charged one-byte marker: `255` initial,
  `0` off-path repair, `1` on-path repeat. It carries `flow_id`, endpoint IDs,
  a realized DATA path and `path_index`; in this F/R data plane,
  `request_id == flow_id` is an invariant. The simulator must not use
  `Packet.created_at` or `protocol` as an uncharged wire field.
- Source ACK_DONE has `kind=ACK_DONE`, `origin=source`, `final_dst=destination`,
  `flow_id`, `request_id=flow_id`, `ttl=1`, empty path, and no app payload.
  Under the current wire model it is 10 bytes. It is generated only in the
  first-acceptance `on_ack` callback for a valid in-deadline F ACK, never for
  an invalid/duplicate/late ACK or an R ACK. It is scheduled once with zero
  requested delay, but normal node TX queues and interference still apply.
  It is never forwarded or retransmitted.
- An F FLOOD observation is eligible only if the packet's source and path
  agree, its last path node is the actual radio sender, its request ID equals
  its flow ID, its path is loop-free and within the configured hop budget.
  At receiver `w`, store the decoded prefix ending at the actual sender
  `v`, keyed by `{w, source, destination, flow, request, v}`.
- A candidate `w` may schedule one repair of an initial F ACK from radio
  sender `u` only when: the ACK's endpoints/path/index/marker are coherent;
  its `path[index+1] == u`; `w` is off the ACK-certified DATA path, can relay,
  and has decoded a matching F FLOOD from `v=path[index]` whose *exact
  prefix* equals `ACK.path[:index+1]`; the charged TTL still permits the
  extra hop. A candidate cannot inspect another node's flow record, source
  action map, true PRR, future reception, or eventual ACK success.
- An on-path ACK receiver validates path position, realized-path prefix
  against its own decoded FLOOD (or source-local pending F flow), marker,
  loop freedom, endpoints and hop bound before forwarding. Initial ACKs
  arrive physically from the encoded downstream node. Repair-marked ACKs
  may arrive from one off-path radio sender while retaining the certified
  DATA path; no second off-path repair is permitted. The source applies its
  existing pending-flow and deadline checks and accepts only the first ACK.
- A candidate pending for `v != source` cancels only after decoding `v`'s
  valid ACK continuation for this flow/path. A candidate pending for
  `v == source` cancels only after decoding ACK_DONE *from the source radio*
  with matching source, destination, flow and request. A lost, colliding, or
  late DONE provides no cancellation. A DONE decoded after the matching F
  FLOOD but before the initial ACK is retained as a bounded local closure
  token until that FLOOD observation expires; it blocks later eligibility
  for the same flow. Neither missing DONE nor a simulator metric can be
  interpreted as evidence that the source is still pending.

## Timers, bounds, and cost

- Candidate wait: `0.20 + 0.15*((candidate_id + flow_id) mod 4)` seconds after
  locally decoding the initial ACK. Keep the RAC wait unchanged to isolate
  closure, not because these constants are optimal. Same-slot collisions
  remain possible. No global one-repair-per-flow oracle exists.
- Each node retains at most eight live F-flow observations and at most two
  distinct sender/prefix observations per flow, each for 30 seconds from
  first local decode. Pending repair/repeat timers are capped at eight per
  node; attempted repair/repeat and forwarded-ACK histories are capped at
  32 per node each. A full history refuses a new action rather than evicting
  a still-live duplicate guard. These states expire no later than 30 seconds
  after the associated
  local FLOOD or ACK observation. At most eight matching closure tokens are
  retained per node, tied to live F-flow observations. A candidate stops at
  its *local* expiry;
  only the source knows the exact 30-second application deadline. The
  source can reject a repair arriving after that deadline.
- Every ACK_DONE, initial ACK, repeat, and repair is a real `Packet` passed
  through `Simulator.transmit_later`. Its actual wire bytes, ToA, TX/RX
  modeled energy, queueing, collisions, and complete-network airtime are
  counted. A zero-cost direct state mutation is forbidden. Separate action
  events record DONE TX/RX, candidate eligibility/cancel, repair/repeat TX,
  first source ACK acceptance, and route commit. Outcome metrics use whole
  flows and seed-paired complete runs, not just triggered episodes.

## Frozen arms and evidence gates

1. `meshecho-clar`: local repair plus one-hop source ACK_DONE cancellation.
2. `meshecho-clar-nocancel`: *same* local repair and *same* ACK_DONE frame,
   but candidates ignore DONE. This isolates cancellation from its beacon
   cost, subject to full closed-loop interference effects.
3. `meshecho-clar-repeat`: same F/R plane and F ACK marker; on-path sender
   repeats once after 0.20 s unless it locally decodes the next ACK
   continuation or, at the terminal hop, the matching source ACK_DONE.
   It sends the same ACK_DONE after source acceptance.
4. `meshecho-clar-fr`: same F/R plane and F ACK marker; single initial ACK,
   no repair/repeat and no unnecessary ACK_DONE. This is the plain baseline.

Use one seed-8000 custom smoke only to verify mechanics/artifact integrity,
not to estimate gain. Then run a single frozen development matrix on exactly
8001--8020 with matched application traces and case configurations, 600-s
generation, 630-s full-TX-cost start window, 30-s application ACK deadline,
and the same recurring-fading workload as RAC. Record source/design/runner
SHA-256 hashes and all CSV/manifest artifact hashes. Do not tune on this
cohort after opening it. The predeclared primary gate requires, for CLAR
minus *each* of repeat and plain-FR: seed-paired nominal two-sided 95% ACK
PDR lower CI > 0 and relative complete-network TX-airtime upper CI < +10%.
The exposure gate requires at least 20 valid locally eligible candidate
events across at least ten seeds. The mechanism diagnostic is the paired
DONE-canceled repair count and CLAR-minus-nocancel full-airtime comparison;
report it even if unfavorable, without changing the primary gate.

Also report destination PDR, source ACK delay, collision count, control
bytes, all packet TX ToA/energy, first-F versus later-R outcomes, beacon
decoding and deadline misses, and exact candidate/local-state exposure.
The gate is an author-chosen project criterion, not an ICC acceptance rule;
nominal intervals are not multiplicity-adjusted. If the development gate
fails, stop this hypothesis. Only a passing, unchanged mechanism may open
the once-only 4001--4040 holdout and then random-pair/PHY/load checks.
Paper text, figures, VERSION, GitHub release, and any submission follow
verified evidence, never a suggestive smoke run.

## Prior-art boundary and risks

ACK-based opportunistic suppression is not new: ExOR (DOI
10.1145/1080091.1080108) is a direct ancestor. DSR (DOI
10.17487/RFC4728) and AODV (DOI 10.17487/RFC3561) already cover reverse
paths and reply acknowledgment. Jang et al. (DOI 10.1002/wcm.991) use a
relay acknowledgment from the preceding forwarder to suppress duplicate
forwarding by neighbors; FSA (DOI 10.1109/ICC.2009.5199042) coordinates
opportunistic candidates with an ACK. OFA (DOI
10.1109/IB2COM.2011.6217923) studies an intermediate ACK on behalf of a
forwarder. LoRa opportunistic routing (DOI
10.1109/WoWMoM57956.2023.00065) and reliable mesh transfer (DOI
10.1016/j.comcom.2025.108404) are also relevant. RAC's DATA-conditioned
off-path relay and source closure may be an engineering combination, not a
first-of-kind algorithm; this targeted search is not a complete novelty
review. Any paper claim must be specific to the measured LoRa
airtime/confirmation trade-off and matched controls, without calling
ACK_DONE, candidate suppression, or cooperative ACK relay itself novel.

The largest empirical risk is timing: DONE may queue, collide, or arrive
after a candidate's 0.20--0.65-s timer. Sending DONE also costs airtime and
can change later interference. The frozen RAC logs are diagnostic only;
they cannot supply a CLAR counterfactual. Hardware feasibility and true
Meshtastic/MeshCore firmware behavior remain outside simulation claims.
In those logs, 144 first F ACKs were accepted, a 10-byte SF7 DONE has
0.041216-s ToA, and 3497/3708 physical repairs began more than this ToA
after source acceptance. This is only a loose ideal-timing upper bound:
some candidates are not one-hop source neighbors, channel decoding and
source queueing are unmodeled in that calculation, and the CLAR closed-loop
trajectory will differ. It cannot be converted into a claimed savings rate.

Implementation checkpoint (2026-10-04): public-packet tests cover direct and
multihop repair, source DONE loss/cancellation, four controls, bounded local
histories, malformed continuation rejection, and candidate/repeat radio-queue
starts crossing local evidence expiry. The integrated Python suite passes
401 tests with one skip. This checkpoint is not a population performance
result; the frozen development matrix remains unopened at this point.
