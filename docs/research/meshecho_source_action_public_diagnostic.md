# Public source-action diagnostic after trial NO-GO

Date: 2026-10-05. Status: prospective exploratory design, no seed run yet.
This is a design diagnostic, not a development gate, holdout, or ICC result.
The current 49201--49210 trial screen has 14 physical trials but no
trial-versus-blind action/path or endpoint difference; it also shows a
reliability/airtime tradeoff against old DCB. We need to identify whether
the removed old D action, one-miss F rule, or route promotion explains
that tradeoff before specifying another core policy.

Run exactly seeds 49301--49310 once on unchanged `recurring_fading`,
600-s application generation, 630-s TX-start cost cutoff, independent
channel streams, and original 30-s application deadline. These seeds are
nonreserved and must not be called confirmation. The fixed seven arms are:

1. `meshecho-dcb` (old F/R/D source rule, conditional backup)
2. `meshecho-dcb-source-fr` (old source rule with D converted to F/R)
3. `meshecho-dcb-source-trigger-f` (same old D trigger converted to
   useful-data F, with identical DCB feedback and relay behavior)
4. `meshecho-dcb-trial` (new one-miss-F source rule plus reversible trial)
5. `meshecho-dcb-trial-no-switch` (same source rule, no trial)
6. `meshecho-dcb-trial-blind` (same source rule, blind path promotion)
7. `meshecho-dhr-flood-ack-delay` (fixed-2-s F-ACK contextual control)

The seventh-arm amendment was made before any 493xx seed ran. The already
opened 46xxx passive archive reported 67/70 old D triggers as aging and
RREQ/RREP physical airtime near 19% of whole-network airtime. Those are
descriptive history, not a fresh comparator outcome. A payload-bearing F
at the exact D trigger is a necessary simple control for any proposed
lower-cost route-refresh core.

For each seed/arm, save all scheduled flow records, source action events,
and complete physical transmission records in a hashed archive, alongside
the exact case/configuration, scheduled-trace and source-file hashes.
Reject a matrix if the scheduled `(time,src,dst,flow_id)` traces, flow
count, case hash or deadline differ across arms for a seed. For every
flow, join its first source physical DATA/FLOOD/RREQ start, action letter,
path, ACK/delivery by original deadline, and eventual F/R recovery. Count
old D decisions separately by cold versus aging trigger, physical RREQ,
RREP candidate and fallback. Count no-D replacement actions, backup ACK
and one-miss-F decisions, actual physical route/path divergence, and all
scheduled-flow source-ACK and destination PDR, full-network airtime,
windowed TX energy, raw modeled RX energy separately, bytes, collisions
and queue waits. Do not sum the windowed TX and unwindowed RX energy
columns into a single endpoint. Report paired seed deltas with intervals
only as exploratory descriptions.

Do not call a different closed-loop arm's outcome the individual flow's
counterfactual. Specifically, an old-DCB D flow and a trial-arm F/R flow
may have different earlier route state despite identical application
identity. The saved physical/action traces are for mechanism diagnosis,
not per-packet causal attribution. If D replacement is implicated, design
a new *same-wire, same-source-state* factorial intervention and freeze its
decision rule and quantitative reliability/airtime margins on fresh seeds
before any reserved run. Do not tune on 47xxx/48xxx or alter their existing
draft permit.
