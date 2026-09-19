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
# New matrices match MeshEcho's 600 s route-cache lifetime. Set this to 300
# only when reproducing the legacy frozen native MeshCore-like rows.
MESHCORE_ROUTE_TTL_S="${MESHCORE_ROUTE_TTL_S:-600}"

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
  --meshcore-route-ttl-s "$MESHCORE_ROUTE_TTL_S"
  --meshcore-discovery-window-s "${MESHCORE_DISCOVERY_WINDOW_S:-2}"
)

# Fresh ICC matrices use an isolated channel stream by default so protocol
# jitter/exploration cannot move later reception draws. Set this to 0 only
# when reproducing legacy frozen CSVs.
RNG_ARGS=()
if [[ "${INDEPENDENT_RNG_STREAMS:-1}" == "1" ]]; then
  RNG_ARGS+=(--independent-rng-streams)
fi

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
    "${RNG_ARGS[@]}" \
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

# A short connected-multihop probe is a hard quality gate for the ICC matrix.
# It checks the topology/link regime itself, so a successful matrix run cannot
# silently become a mostly one-hop, direct-PRR-saturated comparison.
if [[ "${ICC_RUN_QUALITY_PROBE:-1}" == "1" ]]; then
  QUALITY_PREFIX="${OUT_PREFIX}_connected_multihop_quality"
  python3 tools/run_fair_multihop_probe.py \
    --scenario "$QUALITY_PREFIX" \
    --nodes "${ICC_QUALITY_NODES:-50}" \
    --area-m "${ICC_QUALITY_AREA_M:-18000}" \
    --duration-s "${ICC_QUALITY_DURATION_S:-180}" \
    --rate-per-min "${ICC_QUALITY_RATE_PER_MIN:-4}" \
    --traffic mixed \
    --pair-mode connected-multihop \
    --pair-count "${ICC_QUALITY_PAIR_COUNT:-24}" \
    --edge-prr-threshold "${ICC_QUALITY_EDGE_PRR_THRESHOLD:-0.70}" \
    --min-graph-hops "${ICC_QUALITY_MIN_GRAPH_HOPS:-2}" \
    --max-graph-hops "${ICC_QUALITY_MAX_GRAPH_HOPS:-4}" \
    --min-direct-prr-below-0-99 "${ICC_MIN_DIRECT_PRR_BELOW_0_99:-0.10}" \
    --min-selected-pair-mean-graph-hops "${ICC_MIN_MEAN_GRAPH_HOPS:-2.0}" \
    --sf 7 \
    --bw-hz 125000 \
    --cr 1 \
    --payload-bytes 32 \
    --tx-power-dbm 17 \
    --path-loss-exp 2.75 \
    --shadow-sigma-db 4 \
    --capture-threshold-db 6 \
    --max-hops 7 \
    --max-timeout-retries 0 \
    --seeds "${ICC_QUALITY_SEEDS:-3}" \
    --seed0 "$SEED0" \
    --protocol meshcore \
    --csv "results/${QUALITY_PREFIX}.csv" \
    --report "docs/results/${QUALITY_PREFIX}.md"
fi

# This calibrated, non-saturated multi-hop matrix is the primary mechanism
# check for ICC. It uses an 8.25 km square, analytical PRR>=0.90 pair edges,
# 1 flow/min, and a matched 2 s MeshCore discovery window so the experiment is
# multi-hop without intentionally collapsing route discovery.
if [[ "${ICC_RUN_CALIBRATED_MULTIHOP:-1}" == "1" ]]; then
  CALIBRATED_PREFIX="${OUT_PREFIX}_calibrated_multihop"
  python3 tools/run_fair_multihop_probe.py \
    --scenario "$CALIBRATED_PREFIX" \
    --nodes "${ICC_CALIBRATED_NODES:-50}" \
    --area-m "${ICC_CALIBRATED_AREA_M:-8250}" \
    --duration-s "${ICC_CALIBRATED_DURATION_S:-600}" \
    --rate-per-min "${ICC_CALIBRATED_RATE_PER_MIN:-1}" \
    --traffic mixed \
    --pair-mode connected-multihop \
    --pair-count "${ICC_CALIBRATED_PAIR_COUNT:-24}" \
    --edge-prr-threshold "${ICC_CALIBRATED_EDGE_PRR_THRESHOLD:-0.90}" \
    --min-graph-hops 2 \
    --max-graph-hops 4 \
    --min-direct-prr-below-0-99 "${ICC_MIN_DIRECT_PRR_BELOW_0_99:-0.10}" \
    --min-selected-pair-mean-graph-hops "${ICC_MIN_MEAN_GRAPH_HOPS:-2.0}" \
    --meshcore-discovery-window-s "${MESHCORE_DISCOVERY_WINDOW_S:-2}" \
    --sf 7 \
    --bw-hz 125000 \
    --cr 1 \
    --payload-bytes 32 \
    --tx-power-dbm 17 \
    --path-loss-exp 2.75 \
    --shadow-sigma-db 4 \
    --capture-threshold-db 6 \
    --max-hops 7 \
    --max-timeout-retries 0 \
    --seeds "${ICC_CALIBRATED_SEEDS:-$SEEDS}" \
    --seed0 "$SEED0" \
    --csv "results/${CALIBRATED_PREFIX}.csv" \
    --report "docs/results/${CALIBRATED_PREFIX}.md"
fi

if [[ "${ICC_RUN_SENSITIVITY:-0}" == "1" ]]; then
  python3 tools/run_icc_sensitivity_experiments.py \
    --seeds "${ICC_SENSITIVITY_SEEDS:-$SEEDS}" \
    --seed0 "$SEED0" \
    --out-prefix "${ICC_SENSITIVITY_PREFIX:-${OUT_PREFIX}_sensitivity}"
fi

if [[ "${ICC_RUN_GENERALIZATION:-0}" == "1" ]]; then
  python3 tools/run_icc_generalization_experiment.py \
    --seeds "${ICC_GENERALIZATION_SEEDS:-$SEEDS}" \
    --seed0 "$SEED0" \
    --out-prefix "${ICC_GENERALIZATION_PREFIX:-${OUT_PREFIX}_generalization}"
fi

printf '\nICC experiment outputs written under results/ with prefix %s\n' "$OUT_PREFIX"
