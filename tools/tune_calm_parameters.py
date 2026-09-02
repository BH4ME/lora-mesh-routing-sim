#!/usr/bin/env python3
"""Grid-search CALM protocol parameters on reproducible simulator scenarios."""

from __future__ import annotations

import argparse
import csv
import sys
from itertools import product
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lora_mesh_sim import run_one


BASE_ARGS = dict(
    nodes=30,
    area_m=2500.0,
    duration_s=360.0,
    rate_per_min=6.0,
    pair_count=5,
    max_hops=7,
    repeater_ratio=0.0,
    sf=9,
    bw_hz=125_000,
    cr=1,
    payload_bytes=32,
    tx_power_dbm=17.0,
    path_loss_exp=2.7,
    shadow_sigma_db=4.0,
    capture_threshold_db=6.0,
    calm_flood_base_delay_s=0.45,
    calm_flood_jitter_s=0.65,
)


GRID = {
    "calm_route_ttl_s": [600.0, 900.0],
    "calm_discovery_window_s": [2.0, 2.4, 2.8],
    "calm_fallback_confidence_threshold": [0.0, 0.25, 0.45],
    "calm_fallback_ttl": [2],
    "calm_hop_penalty_per_hop": [0.025, 0.035, 0.045],
    "calm_route_age_penalty": [0.1, 0.15, 0.2],
}


def metric_mean(rows: Iterable[Dict[str, Any]], metric: str) -> float:
    values = [float(row[metric]) for row in rows]
    return mean(values) if values else 0.0


def baseline_rows(seeds: int) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    rows: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "unicast": {"meshcore": [], "meshtastic": []},
        "mixed": {"meshcore": [], "meshtastic": []},
    }
    for traffic in ["unicast", "mixed"]:
        for seed in range(1, seeds + 1):
            args = SimpleNamespace(**BASE_ARGS, traffic=traffic)
            rows[traffic]["meshcore"].append(run_one(args, "meshcore", seed))
            rows[traffic]["meshtastic"].append(run_one(args, "meshtastic", seed))
    return rows


def evaluate(
    params: Dict[str, Any],
    seeds: int,
    baselines: Dict[str, Dict[str, List[Dict[str, Any]]]],
) -> Dict[str, Any]:
    calm_rows: List[Dict[str, Any]] = []
    calm_by_traffic: Dict[str, List[Dict[str, Any]]] = {"unicast": [], "mixed": []}

    for traffic in ["unicast", "mixed"]:
        for seed in range(1, seeds + 1):
            args = SimpleNamespace(**BASE_ARGS, **params, traffic=traffic)
            row = run_one(args, "calm", seed)
            calm_rows.append(row)
            calm_by_traffic[traffic].append(row)

    mesh_rows = baselines["unicast"]["meshcore"] + baselines["mixed"]["meshcore"]
    flood_rows = baselines["unicast"]["meshtastic"] + baselines["mixed"]["meshtastic"]

    calm_pdr = metric_mean(calm_rows, "unicast_pdr")
    mesh_pdr = metric_mean(mesh_rows, "unicast_pdr")
    flood_pdr = metric_mean(flood_rows, "unicast_pdr")
    calm_unicast_pdr = metric_mean(calm_by_traffic["unicast"], "unicast_pdr")
    mesh_unicast_pdr = metric_mean(baselines["unicast"]["meshcore"], "unicast_pdr")
    calm_mixed_pdr = metric_mean(calm_by_traffic["mixed"], "unicast_pdr")
    mesh_mixed_pdr = metric_mean(baselines["mixed"]["meshcore"], "unicast_pdr")
    calm_airtime = metric_mean(calm_rows, "total_airtime_s")
    mesh_airtime = metric_mean(mesh_rows, "total_airtime_s")
    flood_airtime = metric_mean(flood_rows, "total_airtime_s")
    calm_collision = metric_mean(calm_rows, "collision_fail")
    mesh_collision = metric_mean(mesh_rows, "collision_fail")
    calm_delay = metric_mean(calm_rows, "avg_delay_s")
    mesh_delay = metric_mean(mesh_rows, "avg_delay_s")

    # Reward recovering MeshCore reliability gaps while keeping CALM closer to
    # MeshCore than flooding on airtime. Mixed traffic is weighted more heavily
    # because that is where fixed source-route caching shows its clearest limit.
    pdr_gain = calm_pdr - mesh_pdr
    weighted_pdr_gain = (calm_unicast_pdr - mesh_unicast_pdr) + 1.7 * (calm_mixed_pdr - mesh_mixed_pdr)
    pdr_gap_to_flood = max(0.0, flood_pdr - calm_pdr)
    airtime_penalty = (calm_airtime - mesh_airtime) / max(flood_airtime - mesh_airtime, 1.0)
    collision_penalty = max(0.0, calm_collision - mesh_collision) / max(mesh_collision, 1.0)
    delay_penalty = max(0.0, calm_delay - mesh_delay) / max(mesh_delay, 0.001)
    unicast_loss_penalty = max(0.0, mesh_unicast_pdr - calm_unicast_pdr)
    score = (
        weighted_pdr_gain
        - 0.25 * pdr_gap_to_flood
        - 0.3 * unicast_loss_penalty
        - 0.35 * airtime_penalty
        - 0.08 * collision_penalty
        - 0.04 * delay_penalty
    )

    return {
        **params,
        "score": round(score, 6),
        "calm_pdr": round(calm_pdr, 6),
        "meshcore_pdr": round(mesh_pdr, 6),
        "meshtastic_pdr": round(flood_pdr, 6),
        "calm_unicast_pdr": round(calm_unicast_pdr, 6),
        "meshcore_unicast_pdr": round(mesh_unicast_pdr, 6),
        "calm_mixed_unicast_pdr": round(calm_mixed_pdr, 6),
        "meshcore_mixed_unicast_pdr": round(mesh_mixed_pdr, 6),
        "calm_airtime_s": round(calm_airtime, 6),
        "meshcore_airtime_s": round(mesh_airtime, 6),
        "meshtastic_airtime_s": round(flood_airtime, 6),
        "calm_collision_fail": round(calm_collision, 6),
        "meshcore_collision_fail": round(mesh_collision, 6),
        "calm_delay_s": round(calm_delay, 6),
        "meshcore_delay_s": round(mesh_delay, 6),
    }


def iter_params() -> Iterable[Dict[str, Any]]:
    keys = list(GRID)
    for values in product(*(GRID[key] for key in keys)):
        yield dict(zip(keys, values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune CALM protocol parameters")
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="optional max number of parameter sets")
    parser.add_argument("--csv", type=Path, default=Path("results/calm_parameter_tuning.csv"))
    parser.add_argument("--node-count", type=int, default=30)
    parser.add_argument("--area-m", type=float, default=2500.0)
    parser.add_argument("--duration-s", type=float, default=360.0)
    parser.add_argument("--rate-per-min", type=float, default=6.0)
    parser.add_argument("--pair-count", type=int, default=5)
    parser.add_argument("--shadow-sigma-db", type=float, default=4.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    BASE_ARGS.update(
        nodes=args.node_count,
        area_m=args.area_m,
        duration_s=args.duration_s,
        rate_per_min=args.rate_per_min,
        pair_count=args.pair_count,
        shadow_sigma_db=args.shadow_sigma_db,
    )
    rows: List[Dict[str, Any]] = []
    baselines = baseline_rows(args.seeds)
    for index, params in enumerate(iter_params(), start=1):
        if args.limit and index > args.limit:
            break
        row = evaluate(params, args.seeds, baselines)
        rows.append(row)
        print(
            f"{index:03d} score={row['score']:.6f} "
            f"pdr={row['calm_pdr']:.3f}/{row['meshcore_pdr']:.3f} "
            f"airtime={row['calm_airtime_s']:.1f}/{row['meshcore_airtime_s']:.1f} "
            f"params={params}",
            flush=True,
        )

    rows.sort(key=lambda row: row["score"], reverse=True)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    best = rows[0]
    print("\nBest parameter set")
    print("------------------")
    for key, value in best.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
