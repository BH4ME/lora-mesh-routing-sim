# MeshEcho-CPR Smoke Contract (Evidence v2)

This contract defines the first mechanical artifact check for the CPR
successor. It is not a performance or acceptance claim.

- Arms: `meshecho-cpr`, `meshecho-cpr-nocancel`, `meshecho-drc-no-rescue`,
  and `meshecho-drc`.
- Each seed uses one generated topology, one directed pair pool, and one
  application trace shared by all arms.
- Source recovery is physically ordered as one same-path repeat (marker 1)
  followed, only after that repeat starts and remains unacknowledged, by at
  most one marked FLOOD recovery (marker 2).
- A relay may cancel a pending FLOOD only after a physically decoded matching
  ACK and only while its local transmission handle is uncommitted.
- The evidence bundle must reconcile every started request with exactly one
  physical TX, every started TX with one RX attempt per modeled node, and
  every accepted ACK with its successful physical RX attempt.
- For CPR arms, every started `CPR_*_REQUEST` must join exactly one source
  decision, and its placeholder action, actual packet kind, repair marker,
  and physical TX must agree. Accepted ACKs must join a started matching
  initial/repeat/recovery packet and record route generation before and after
  the commit.
- Run scope `(seed, protocol)` and artifact record counts are closed-world;
  duplicate accepted ACK or RX attempt identifiers are invalid.
- The smoke stage does not authorize development, holdout, paper edits,
  version changes, GitHub pushes, or EDAS submission.
