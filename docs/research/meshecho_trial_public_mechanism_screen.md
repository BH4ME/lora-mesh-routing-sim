# MeshEcho trial-core public mechanism screen

Date: 2026-10-05. Status: prospective exploratory diagnostic, not a causal
population claim, development gate, holdout, or ICC result.

Run exactly the nonreserved seeds 49201--49210 once on the unchanged
`recurring_fading` case with 30-s application deadline. The five arms are
`meshecho-dcb-trial`, `meshecho-dcb-trial-no-switch`,
`meshecho-dcb-trial-blind`, `meshecho-dcb`, and
`meshecho-dhr-flood-ack-delay`. Compare identical scheduled application
trace/configuration hashes and all-scheduled-flow source ACK, destination
delivery, and complete-network TX airtime. Count physically started two-hop
trial R DATA, ordinary trial ACK commits, source-guard abandonments, blind
commits, and per-flow source action/path divergence from no-switch and old
DCB. Do not infer mechanism effects from decision events alone.

This screen asks only whether the current candidate has enough physical
branch exposure to justify a frozen experiment. A useful minimum is five
physically started trials over at least three seeds plus at least one
guard-abandoned trial; lower exposure is a workload-specific NO-GO for
freezing this candidate as the trial mechanism. Passing this screen does
not establish benefit. Report paired endpoint differences descriptively,
including adverse results, without setting or tuning confirmatory margins
from these ten seeds. The reserved 47xxx/48xxx windows remain closed.
