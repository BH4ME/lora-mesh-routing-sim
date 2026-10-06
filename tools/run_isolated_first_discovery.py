#!/usr/bin/env python3
"""Compare first route discoveries on isolated, shared source-destination pairs."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (  # noqa: E402
    MeshCoreLike,
    MeshEcho,
    MeshEchoCalibrated,
    MetricMesh,
    MinHopMesh,
    Node,
    RadioConfig,
    RoutingProtocol,
    Simulator,
    generate_nodes,
)
from tools.run_fair_multihop_probe import (  # noqa: E402
    connected_multihop_pairs,
    paired_mean_ci,
)


PROTOCOLS = (
    "meshecho",
    "meshecho-calibrated",
    "etx-mesh",
    "prr-product-mesh",
    "minhop-mesh",
    "meshcore-like",
)


@dataclass(frozen=True)
class ExperimentConfig:
    nodes: int = 50
    area_m: float = 8250.0
    pair_count: int = 24
    edge_prr_threshold: float = 0.90
    min_graph_hops: int = 2
    max_graph_hops: int = 4
    sf: int = 7
    tx_power_dbm: float = 17.0
    path_loss_exp: float = 2.75
    shadow_sigma_db: float = 4.0
    discovery_window_s: float = 2.0
    duration_s: float = 12.0
    max_hops: int = 7


def make_protocol(name: str, discovery_window_s: float) -> RoutingProtocol:
    if name == "meshecho":
        return MeshEcho(
            discovery_window_s=discovery_window_s,
            route_miss_recovery_enabled=False,
        )
    if name == "meshecho-calibrated":
        return MeshEchoCalibrated(
            discovery_window_s=discovery_window_s,
            route_miss_recovery_enabled=False,
        )
    if name == "etx-mesh":
        return MetricMesh("etx", discovery_window_s=discovery_window_s)
    if name == "prr-product-mesh":
        return MetricMesh("prr-product", discovery_window_s=discovery_window_s)
    if name == "minhop-mesh":
        return MinHopMesh(discovery_window_s=discovery_window_s)
    if name == "meshcore-like":
        return MeshCoreLike(discovery_window_s=discovery_window_s)
    raise ValueError(f"unknown protocol: {name}")


def run_seed(seed: int, config: ExperimentConfig) -> List[Dict[str, Any]]:
    if config.pair_count <= 0:
        raise ValueError("pair_count must be positive")
    if config.duration_s <= config.discovery_window_s + 0.1:
        raise ValueError("duration_s must extend beyond route discovery")

    nodes = generate_nodes(config.nodes, config.area_m, random.Random(seed))
    radio = RadioConfig(
        sf=config.sf,
        tx_power_dbm=config.tx_power_dbm,
        path_loss_exp=config.path_loss_exp,
        shadow_sigma_db=config.shadow_sigma_db,
    )
    selector = Simulator(
        [replace(node) for node in nodes],
        radio,
        MeshEcho(),
        seed=seed,
        max_hops=config.max_hops,
        independent_random_streams=True,
        matched_rreq_timing=True,
    )
    pairs, graph_hops = connected_multihop_pairs(
        selector,
        random.Random(seed + 20_000),
        config.edge_prr_threshold,
        config.min_graph_hops,
        config.max_graph_hops,
        config.pair_count,
    )
    if len(pairs) != config.pair_count:
        raise ValueError(
            f"seed {seed} has only {len(pairs)} connected pairs; "
            f"requested {config.pair_count}"
        )

    rows: List[Dict[str, Any]] = []
    for pair_index, ((source, destination), hops) in enumerate(
        zip(pairs, graph_hops), start=1
    ):
        pair_rows: List[Dict[str, Any]] = []
        candidate_sets: List[Tuple[Tuple[int, ...], ...]] = []
        for name in PROTOCOLS:
            protocol = make_protocol(name, config.discovery_window_s)
            sim = Simulator(
                [replace(node) for node in nodes],
                radio,
                protocol,
                seed=seed,
                max_hops=config.max_hops,
                independent_random_streams=True,
                matched_rreq_timing=True,
            )
            sim.schedule(0.1, "app_send", (source, destination, 1))
            metrics = sim.run(config.duration_s)
            if len(protocol.discovery_records) != 1 or len(metrics.flows) != 1:
                raise RuntimeError(
                    f"seed {seed} pair {pair_index} {name} did not complete "
                    "one isolated route discovery"
                )
            record = protocol.discovery_records[0]
            flow = metrics.flows[1]
            candidate_sets.append(record.candidate_paths)
            pair_rows.append(
                {
                    "seed": seed,
                    "pair_index": pair_index,
                    "source": source,
                    "destination": destination,
                    "selected_graph_hops": hops,
                    "protocol": name,
                    "matched_rreq_timing": int(sim.matched_rreq_timing),
                    "unicast_flows": 1,
                    "discovery_count": len(protocol.discovery_records),
                    "candidate_count": len(record.candidate_paths),
                    "candidate_paths_json": json.dumps(record.candidate_paths),
                    "selected_path_json": json.dumps(record.selected_path),
                    "destination_delivered": int(flow.delivered_at is not None),
                    "ack_confirmed": int(flow.acked_at is not None),
                    "total_airtime_s": metrics.total_airtime_s,
                    "route_cache_hits": metrics.route_cache_hits,
                    "route_repair_count": metrics.route_repair_count,
                    "fallback_forward_count": metrics.fallback_forward_count,
                }
            )
        identical = int(len(set(candidate_sets)) == 1)
        for row in pair_rows:
            row["candidate_sets_identical"] = identical
            row["shared_multi_candidate_set"] = int(
                identical and len(candidate_sets[0]) >= 2
            )
        rows.extend(pair_rows)
    return rows


def render_report(rows: List[Dict[str, Any]], config: ExperimentConfig) -> str:
    groups: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(int(row["seed"]), int(row["pair_index"]))].append(row)

    matched = 0
    multi_candidate = 0
    mismatches = []
    for (seed, pair_index), pair_rows in sorted(groups.items()):
        if len(pair_rows) != len(PROTOCOLS) or {
            row["protocol"] for row in pair_rows
        } != set(PROTOCOLS):
            raise ValueError(f"seed {seed}, pair {pair_index} has incomplete policies")
        candidate_sets = {
            row["protocol"]: tuple(
                tuple(path) for path in json.loads(row["candidate_paths_json"])
            )
            for row in pair_rows
        }
        if len(set(candidate_sets.values())) == 1:
            matched += 1
            multi_candidate += int(len(next(iter(candidate_sets.values()))) >= 2)
        else:
            mismatches.append(f"seed {seed}, pair {pair_index}")

    lines = [
        "# Isolated First-Discovery Comparison",
        "",
        f"- Seeds: {len({seed for seed, _ in groups})}",
        f"- Selected pairs per seed: {config.pair_count}",
        f"- Simulations: {len(rows)}; one unicast and a fresh simulator per row",
        f"- RREQ relay timing: matched across all {len(PROTOCOLS)} policies",
        "- MeshEcho route-miss fallback: disabled for this isolation test",
        "- PRR-product: product of model-derived PRR from received RREQ "
        "SINR, with no retry or fallback",
        "- `meshcore-like` is the matched-window shortest-candidate "
        "source-route comparator",
        "- Pair selection uses an analytical PRR graph only to choose shared "
        "source-destination pairs; route policies do not receive that graph",
        "",
        "## Candidate Exposure",
        "",
        f"{matched}/{len(groups)} pairs had identical candidate sets across "
        f"all {len(PROTOCOLS)} policies.",
        f"{multi_candidate} matched pairs exposed at least two candidates.",
        "",
    ]
    if mismatches:
        lines.extend(
            [
                "Candidate sets differed, so this experiment cannot attribute "
                "outcome differences solely to route ranking.",
                "Mismatched pairs: " + "; ".join(mismatches) + ".",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "All recorded candidate sets matched. Selected-path contrasts "
                "condition on the same observed choices; ACK and airtime also "
                "include route-reply and data-plane behavior.",
                "",
            ]
        )

    lines.extend(
        [
            "## Descriptive Outcomes",
            "",
            "Each row below is a mean over isolated single-unicast pairs. "
            "Pairs in one seed share topology and are not independent "
            "statistical replicates.",
            "",
            "| Policy | ACK completion | Destination delivery | Airtime per pair (s) |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for protocol in PROTOCOLS:
        policy_rows = [row for row in rows if row["protocol"] == protocol]
        if not policy_rows:
            continue
        count = len(policy_rows)
        lines.append(
            f"| {protocol} | "
            f"{sum(int(row['ack_confirmed']) for row in policy_rows) / count:.3f} | "
            f"{sum(int(row['destination_delivered']) for row in policy_rows) / count:.3f} | "
            f"{sum(float(row['total_airtime_s']) for row in policy_rows) / count:.3f} |"
        )

    seed_rows: Dict[Tuple[int, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seed_rows[(int(row["seed"]), str(row["protocol"]))].append(row)
    seeds = sorted({seed for seed, _ in seed_rows})
    lines.extend(
        [
            "",
            "## Seed-Paired Differences",
            "",
            "MeshEcho minus each comparator; each seed contributes one mean "
            "over its selected pairs. Intervals are two-sided 95% paired "
            "t intervals across seeds, not across individual flows.",
            "",
            "| Comparator | ACK delta [95% CI] | Destination delta [95% CI] | Airtime per pair delta (s) [95% CI] |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for comparator in PROTOCOLS[1:]:
        intervals = []
        for field in ("ack_confirmed", "destination_delivered", "total_airtime_s"):
            differences = [
                statistics.fmean(float(row[field]) for row in seed_rows[(seed, "meshecho")])
                - statistics.fmean(float(row[field]) for row in seed_rows[(seed, comparator)])
                for seed in seeds
            ]
            estimate, lower, upper = paired_mean_ci(differences)
            intervals.append(f"{estimate:+.3f} [{lower:+.3f},{upper:+.3f}]")
        lines.append(f"| {comparator} | " + " | ".join(intervals) + " |")

    lines.extend(
        [
            "",
            "## Selected-Path Attribution Check",
            "",
            "For pairs where MeshEcho and a comparator selected the same path, "
            "the table counts any ACK, destination, or airtime mismatch. "
            "Zero mismatches supports a route-choice explanation in this "
            "isolated simulator, conditional on identical candidate exposure.",
            "",
            "| Comparator | Different selected path | Same selected path | "
            "Same-path outcome mismatches |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for comparator in PROTOCOLS[1:]:
        different = 0
        same = 0
        mismatches = 0
        for pair_rows in groups.values():
            by_protocol = {row["protocol"]: row for row in pair_rows}
            echo = by_protocol["meshecho"]
            other = by_protocol[comparator]
            if echo["selected_path_json"] != other["selected_path_json"]:
                different += 1
                continue
            same += 1
            mismatches += int(
                echo["ack_confirmed"] != other["ack_confirmed"]
                or echo["destination_delivered"] != other["destination_delivered"]
                or abs(float(echo["total_airtime_s"]) - float(other["total_airtime_s"])) > 1e-9
            )
        lines.append(f"| {comparator} | {different} | {same} | {mismatches} |")
    lines.extend(
        [
            "",
            (
                "One seed is descriptive only; its degenerate interval is not "
                "an inferential confidence interval."
                if len(seeds) < 2
                else "Paired intervals treat seeds, not individual flows, as "
                "independent statistical units."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: List[str] = None) -> None:
    defaults = ExperimentConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--nodes", type=int, default=defaults.nodes)
    parser.add_argument("--area-m", type=float, default=defaults.area_m)
    parser.add_argument("--pair-count", type=int, default=defaults.pair_count)
    parser.add_argument(
        "--edge-prr-threshold", type=float, default=defaults.edge_prr_threshold
    )
    parser.add_argument("--min-graph-hops", type=int, default=defaults.min_graph_hops)
    parser.add_argument("--max-graph-hops", type=int, default=defaults.max_graph_hops)
    parser.add_argument("--sf", type=int, default=defaults.sf)
    parser.add_argument("--tx-power-dbm", type=float, default=defaults.tx_power_dbm)
    parser.add_argument("--path-loss-exp", type=float, default=defaults.path_loss_exp)
    parser.add_argument(
        "--shadow-sigma-db", type=float, default=defaults.shadow_sigma_db
    )
    parser.add_argument(
        "--discovery-window-s", type=float, default=defaults.discovery_window_s
    )
    parser.add_argument("--duration-s", type=float, default=defaults.duration_s)
    parser.add_argument("--max-hops", type=int, default=defaults.max_hops)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.seeds <= 0:
        parser.error("--seeds must be positive")
    if args.csv == args.report:
        parser.error("--csv and --report must be different paths")
    config = ExperimentConfig(
        nodes=args.nodes,
        area_m=args.area_m,
        pair_count=args.pair_count,
        edge_prr_threshold=args.edge_prr_threshold,
        min_graph_hops=args.min_graph_hops,
        max_graph_hops=args.max_graph_hops,
        sf=args.sf,
        tx_power_dbm=args.tx_power_dbm,
        path_loss_exp=args.path_loss_exp,
        shadow_sigma_db=args.shadow_sigma_db,
        discovery_window_s=args.discovery_window_s,
        duration_s=args.duration_s,
        max_hops=args.max_hops,
    )
    rows = [
        row
        for seed in range(args.seed0, args.seed0 + args.seeds)
        for row in run_seed(seed, config)
    ]
    report = render_report(rows, config)
    for path in (args.csv, args.report):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with args.report.open("x", encoding="utf-8") as stream:
        stream.write(report)
    print(f"Wrote {len(rows)} isolated policy rows to {args.csv}")
    print(f"Wrote candidate-exposure report to {args.report}")


if __name__ == "__main__":
    main()
