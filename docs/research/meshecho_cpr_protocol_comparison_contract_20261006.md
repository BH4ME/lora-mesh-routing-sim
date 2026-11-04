# CPR External Protocol Comparison Contract

This separate comparison runs `meshecho-cpr`, `meshtastic`, and `meshcore`
under the CPR exposure case. It uses the same generated topology, pair pool,
application trace, radio configuration, fading draws, deadline, and seed for
each protocol. The two named protocols are simulator models, not claims of
firmware equivalence.

The candidate remains the CPR method. The comparison is descriptive evidence
for protocol-family behavior; it is separate from the sealed four-arm CPR
development/holdout gate and does not alter those manifests.

Reproduction command:

```bash
python3 tools/run_cpr_external_comparison.py \
  --case-profile exposure \
  --out-prefix results/meshecho_cpr_external_comparison_92300_92319_20261006
```

The result files contain per-seed rows, paired identity checks, and aggregate
means for deadline ACK PDR, destination PDR, TX airtime, TX energy, and started
requests. The current CPR population remains the authoritative evidence for
the primary claim; this comparison does not add hardware validation.
