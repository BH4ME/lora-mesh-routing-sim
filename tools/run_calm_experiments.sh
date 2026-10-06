#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_PREFIX="${OUT_PREFIX:-smart_calm_v1_1}"

SMART_CALM_V1_1_ARGS=(
  --smart-flow-timeout-s 35
  --smart-timeout-fallback-min-ttl 2
)

python3 lora_mesh_sim.py \
  --protocol all4 \
  --nodes 50 \
  --area-m 3000 \
  --duration-s 1200 \
  --traffic unicast \
  --rate-per-min 6 \
  --pair-count 8 \
  "${SMART_CALM_V1_1_ARGS[@]}" \
  --seeds 20 \
  --csv "results/${OUT_PREFIX}_50n_unicast_pairs.csv"

python3 analyze_results.py "results/${OUT_PREFIX}_50n_unicast_pairs.csv" \
  > "results/${OUT_PREFIX}_50n_unicast_pairs_summary.txt"

python3 lora_mesh_sim.py \
  --protocol all4 \
  --nodes 50 \
  --area-m 3000 \
  --duration-s 1200 \
  --traffic mixed \
  --rate-per-min 6 \
  --pair-count 8 \
  "${SMART_CALM_V1_1_ARGS[@]}" \
  --seeds 20 \
  --csv "results/${OUT_PREFIX}_50n_mixed.csv"

python3 analyze_results.py "results/${OUT_PREFIX}_50n_mixed.csv" \
  > "results/${OUT_PREFIX}_50n_mixed_summary.txt"

python3 lora_mesh_sim.py \
  --protocol all4 \
  --nodes 50 \
  --area-m 3000 \
  --duration-s 1200 \
  --traffic mixed \
  --rate-per-min 6 \
  --pair-count 8 \
  --shadow-sigma-db 6 \
  "${SMART_CALM_V1_1_ARGS[@]}" \
  --seeds 20 \
  --csv "results/${OUT_PREFIX}_50n_mixed_shadow6.csv"

python3 analyze_results.py "results/${OUT_PREFIX}_50n_mixed_shadow6.csv" \
  > "results/${OUT_PREFIX}_50n_mixed_shadow6_summary.txt"

python3 lora_mesh_sim.py \
  --protocol all4 \
  --nodes 50 \
  --area-m 3000 \
  --duration-s 1200 \
  --traffic mixed \
  --rate-per-min 10 \
  --pair-count 8 \
  "${SMART_CALM_V1_1_ARGS[@]}" \
  --seeds 20 \
  --csv "results/${OUT_PREFIX}_50n_mixed_rate10.csv"

python3 analyze_results.py "results/${OUT_PREFIX}_50n_mixed_rate10.csv" \
  > "results/${OUT_PREFIX}_50n_mixed_rate10_summary.txt"
