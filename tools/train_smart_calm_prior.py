#!/usr/bin/env python3
"""Train an offline Smart-CALM policy prior from representative scenarios."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from argparse import Namespace
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (  # noqa: E402
    RadioConfig,
    Simulator,
    SmartCalmMesh,
    generate_nodes,
    schedule_traffic,
)


TRAIN_SCENARIOS = (
    {"name": "mixed", "traffic": "mixed", "rate_per_min": 6.0, "shadow_sigma_db": 4.0},
    {"name": "shadow6", "traffic": "mixed", "rate_per_min": 6.0, "shadow_sigma_db": 6.0},
    {"name": "rate10", "traffic": "mixed", "rate_per_min": 10.0, "shadow_sigma_db": 4.0},
    {"name": "rate10", "traffic": "mixed", "rate_per_min": 10.0, "shadow_sigma_db": 4.0},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a Smart-CALM prior")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "smart_calm_prior.json")
    parser.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "results" / "smart_calm_prior_training.csv",
    )
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--duration-s", type=float, default=360.0)
    parser.add_argument("--exploration", type=float, default=0.12)
    parser.add_argument("--learning-rate", type=float, default=0.45)
    parser.add_argument("--update-interval-s", type=float, default=30.0)
    parser.add_argument("--flow-timeout-s", type=float, default=35.0)
    parser.add_argument("--nodes", type=int, default=50)
    parser.add_argument("--area-m", type=float, default=3000.0)
    parser.add_argument("--pair-count", type=int, default=8)
    parser.add_argument("--max-hops", type=int, default=7)
    parser.add_argument("--repeater-ratio", type=float, default=0.0)
    parser.add_argument("--sf", type=int, default=9)
    parser.add_argument("--bw-hz", type=int, default=125_000)
    parser.add_argument("--cr", type=int, default=1)
    parser.add_argument("--payload-bytes", type=int, default=32)
    parser.add_argument("--tx-power-dbm", type=float, default=17.0)
    parser.add_argument("--path-loss-exp", type=float, default=2.7)
    parser.add_argument("--capture-threshold-db", type=float, default=6.0)
    parser.add_argument("--calm-route-ttl-s", type=float, default=600.0)
    parser.add_argument("--calm-discovery-window-s", type=float, default=2.0)
    parser.add_argument("--calm-flood-base-delay-s", type=float, default=0.45)
    parser.add_argument("--calm-flood-jitter-s", type=float, default=0.65)
    parser.add_argument("--calm-fallback-ttl", type=int, default=2)
    parser.add_argument("--calm-fallback-confidence-threshold", type=float, default=0.0)
    parser.add_argument("--calm-fallback-delay-margin-s", type=float, default=0.6)
    parser.add_argument("--calm-hop-penalty-per-hop", type=float, default=0.025)
    parser.add_argument("--calm-route-age-penalty", type=float, default=0.1)
    return parser.parse_args()


def build_episode_args(args: argparse.Namespace, scenario: Dict[str, Any]) -> Namespace:
    return Namespace(
        nodes=args.nodes,
        area_m=args.area_m,
        duration_s=args.duration_s,
        rate_per_min=scenario["rate_per_min"],
        traffic=scenario["traffic"],
        pair_count=args.pair_count,
        max_hops=args.max_hops,
        repeater_ratio=args.repeater_ratio,
        sf=args.sf,
        bw_hz=args.bw_hz,
        cr=args.cr,
        payload_bytes=args.payload_bytes,
        tx_power_dbm=args.tx_power_dbm,
        path_loss_exp=args.path_loss_exp,
        shadow_sigma_db=scenario["shadow_sigma_db"],
        capture_threshold_db=args.capture_threshold_db,
        calm_route_ttl_s=args.calm_route_ttl_s,
        calm_discovery_window_s=args.calm_discovery_window_s,
        calm_flood_base_delay_s=args.calm_flood_base_delay_s,
        calm_flood_jitter_s=args.calm_flood_jitter_s,
        calm_fallback_ttl=args.calm_fallback_ttl,
        calm_fallback_confidence_threshold=args.calm_fallback_confidence_threshold,
        calm_fallback_delay_margin_s=args.calm_fallback_delay_margin_s,
        calm_hop_penalty_per_hop=args.calm_hop_penalty_per_hop,
        calm_route_age_penalty=args.calm_route_age_penalty,
        smart_update_interval_s=args.update_interval_s,
        smart_learning_rate=args.learning_rate,
        smart_exploration=args.exploration,
        smart_flow_timeout_s=args.flow_timeout_s,
    )


def train_episode(
    args: argparse.Namespace,
    scenario: Dict[str, Any],
    seed: int,
    prior_q_values: Dict[Tuple[int, int], float],
) -> Tuple[Dict[str, Any], Dict[Tuple[int, int], float]]:
    episode_args = build_episode_args(args, scenario)
    topology_rng = random.Random(seed)
    nodes = generate_nodes(episode_args.nodes, episode_args.area_m, topology_rng, episode_args.repeater_ratio)
    radio = RadioConfig(
        sf=episode_args.sf,
        bw_hz=episode_args.bw_hz,
        cr=episode_args.cr,
        payload_bytes=episode_args.payload_bytes,
        tx_power_dbm=episode_args.tx_power_dbm,
        path_loss_exp=episode_args.path_loss_exp,
        shadow_sigma_db=episode_args.shadow_sigma_db,
        capture_threshold_db=episode_args.capture_threshold_db,
    )
    protocol = SmartCalmMesh(
        update_interval_s=episode_args.smart_update_interval_s,
        learning_rate=episode_args.smart_learning_rate,
        exploration=episode_args.smart_exploration,
        flow_timeout_s=episode_args.smart_flow_timeout_s,
        prior_q_values=prior_q_values,
        flood_base_delay_s=episode_args.calm_flood_base_delay_s,
        flood_jitter_s=episode_args.calm_flood_jitter_s,
        profiles=SmartCalmMesh.profiles_from_base_parameters(
            route_ttl_s=episode_args.calm_route_ttl_s,
            discovery_window_s=episode_args.calm_discovery_window_s,
            fallback_confidence_threshold=episode_args.calm_fallback_confidence_threshold,
            fallback_ttl=episode_args.calm_fallback_ttl,
            fallback_delay_margin_s=episode_args.calm_fallback_delay_margin_s,
            hop_penalty_per_hop=episode_args.calm_hop_penalty_per_hop,
            route_age_penalty=episode_args.calm_route_age_penalty,
        ),
    )
    sim = Simulator(nodes, radio, protocol, seed=seed, max_hops=episode_args.max_hops)
    traffic_rng = random.Random(seed + 10_000)
    schedule_traffic(
        sim,
        episode_args.duration_s,
        scenario["rate_per_min"],
        scenario["traffic"],
        traffic_rng,
        episode_args.pair_count,
    )
    metrics = sim.run(episode_args.duration_s)
    row = metrics.summarize(protocol.name, seed, episode_args.duration_s)
    return row, dict(protocol.q_values)


def q_values_to_rows(q_values: Dict[Tuple[int, int], float]) -> List[Dict[str, Any]]:
    return [
        {"state": state, "action": action, "value": value}
        for (state, action), value in sorted(q_values.items())
    ]


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    prior_q_values: Dict[Tuple[int, int], float] = {}
    episode_rows: List[Dict[str, Any]] = []

    seed_base = 100
    for round_index in range(args.rounds):
        for scenario_index, scenario in enumerate(TRAIN_SCENARIOS):
            for seed_offset in range(args.seeds):
                seed = seed_base + round_index * 1000 + scenario_index * 100 + seed_offset
                row, prior_q_values = train_episode(args, scenario, seed, prior_q_values)
                episode_rows.append(
                    {
                        "round": round_index + 1,
                        "scenario": scenario["name"],
                        "seed": seed,
                        "unicast_pdr": row["unicast_pdr"],
                        "total_airtime_s": row["total_airtime_s"],
                        "collision_fail": row["collision_fail"],
                        "policy_switch_count": row["policy_switch_count"],
                        "policy_update_count": row["policy_update_count"],
                        "policy_reward_total": row["policy_reward_total"],
                    }
                )
                print(
                    f"round={round_index + 1} scenario={scenario['name']} seed={seed} "
                    f"pdr={row['unicast_pdr']:.3f} airtime={row['total_airtime_s']:.1f} "
                    f"collisions={row['collision_fail']:.0f} switches={row['policy_switch_count']}",
                    flush=True,
                )

    prior_payload = {
        "version": 1,
        "rounds": args.rounds,
        "seeds": args.seeds,
        "duration_s": args.duration_s,
        "exploration": args.exploration,
        "learning_rate": args.learning_rate,
        "update_interval_s": args.update_interval_s,
        "flow_timeout_s": args.flow_timeout_s,
        "q_values": q_values_to_rows(prior_q_values),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(prior_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(args.csv, episode_rows)

    print(f"\nWrote prior to {args.output}")
    print(f"Wrote training log to {args.csv}")
    print(f"Learned {len(prior_q_values)} q-values")
    if episode_rows:
        print(f"Mean train PDR: {mean(float(row['unicast_pdr']) for row in episode_rows):.3f}")


if __name__ == "__main__":
    main()
