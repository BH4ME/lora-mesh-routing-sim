#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_PREFIX="${OUT_PREFIX:-icc2027}"
NODES="${NODES:-50}"
AREA_M="${AREA_M:-3000}"
DURATION_S="${DURATION_S:-1200}"
PAIR_COUNT="${PAIR_COUNT:-8}"
SEEDS="${SEEDS:-20}"
SEED0="${SEED0:-1}"

BASE_ARGS=(
  --protocol icc
  --nodes "$NODES"
  --area-m "$AREA_M"
  --duration-s "$DURATION_S"
  --pair-count "$PAIR_COUNT"
  --seeds "$SEEDS"
  --seed0 "$SEED0"
  --max-hops 7
  --sf 9
  --bw-hz 125000
  --cr 1
  --payload-bytes 32
  --tx-power-dbm 17
  --path-loss-exp 2.7
  --shadow-sigma-db 4
  --capture-threshold-db 6
  --tx-current-ma 120
  --rx-current-ma 10.3
  --supply-voltage-v 3.3
)

run_scenario() {
  local suffix="$1"
  local traffic="$2"
  local rate_per_min="$3"
  shift 3

  local csv_path="results/${OUT_PREFIX}_${suffix}.csv"
  local text_summary_path="results/${OUT_PREFIX}_${suffix}_summary.txt"
  local summary_csv_path="results/${OUT_PREFIX}_${suffix}_summary.csv"

  python3 lora_mesh_sim.py \
    "${BASE_ARGS[@]}" \
    --traffic "$traffic" \
    --rate-per-min "$rate_per_min" \
    "$@" \
    --csv "$csv_path"

  python3 analyze_results.py "$csv_path" \
    --summary-csv "$summary_csv_path" \
    > "$text_summary_path"
}

# The first two scenarios support the main comparison. The last two stress
# shadowing and offered load without changing the protocol list or seed set.
run_scenario "50n_unicast_pairs" "unicast" 6
run_scenario "50n_mixed" "mixed" 6
run_scenario "50n_mixed_shadow6" "mixed" 6 --shadow-sigma-db 6
run_scenario "50n_mixed_rate10" "mixed" 10

printf '\nICC experiment outputs written under results/ with prefix %s\n' "$OUT_PREFIX"
