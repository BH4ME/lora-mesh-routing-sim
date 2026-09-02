# Changelog

## 2.1.1 - ICC comparison freeze

- Add the verified ICC 2027 comparison report and handoff note.
- Freeze the new ICC raw CSVs and long-format summaries under the
  `meshecho_v2_1_0_icc_50n_*` prefix.
- Add a deterministic unit test covering the Smart-CALM no-confidence route
  selection branch.
- Bump firmware and project release metadata to `2.1.1`.

## 2.1.0 - Firmware reliability and telemetry

- Complete Smart-CALM fallback delivery with reverse-path ACK generation.
- Clear completed pending flows so an acknowledged packet is not retried after
  the ACK timeout.
- Preserve the original application timestamp across route retries and
  fallback recovery for end-to-end ACK delay telemetry.
- Enforce terminal-hop TTL handling for route discovery and source-route
  replies.
- Bind retry profile parameters to the flow that selected them.
- Add bounded duplicate suppression for fallback forwarding.
- Expose receive failures, route aging, neighbor aging, fallback deliveries,
  ACK delivery counts, ACK delay, and learning counters through `show`.
- Add host smoke coverage for direct route ACK completion and fallback ACK
  completion.
