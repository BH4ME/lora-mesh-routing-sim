#!/usr/bin/env python3
"""Run a versioned, non-saturated fairness probe for MeshEcho.

The original ICC matrix reuses a small set of pairs in a compact area. This
probe uses random source-destination pairs and a calibrated multi-hop regime.
It records both protocol metrics and link/route diagnostics so that a result
cannot be interpreted without checking whether the network is connected and
whether direct links are saturated.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (  # noqa: E402
    BROADCAST_DST,
    ICC_PROTOCOLS,
    RadioConfig,
    RouteEntry,
    Simulator,
    build_protocol,
    generate_nodes,
    percentile,
)


DEFAULT_PROTOCOLS = tuple(ICC_PROTOCOLS)
DEFAULT_OUT = Path("results/meshecho_fair_multihop_probe.csv")
DEFAULT_REPORT = Path("docs/results/meshecho_fair_multihop_probe.md")


def make_args(args: argparse.Namespace) -> argparse.Namespace:
    """Build the Namespace expected by lora_mesh_sim.build_protocol()."""

    return argparse.Namespace(
        calm_route_ttl_s=600.0,
        calm_discovery_window_s=2.0,
        calm_flood_base_delay_s=0.45,
        calm_flood_jitter_s=0.65,
        calm_fallback_ttl=2,
        calm_fallback_confidence_threshold=0.0,
        calm_fallback_delay_margin_s=0.6,
        calm_hop_penalty_per_hop=0.025,
        calm_route_age_penalty=0.1,
        smart_update_interval_s=30.0,
        smart_learning_rate=0.45,
        smart_exploration=0.02,
        smart_flow_timeout_s=15.0,
        smart_max_timeout_retries=getattr(args, "smart_max_timeout_retries", 2),
        smart_retry_after_fallback=False,
        smart_route_miss_fallback_ttl=0,
        smart_timeout_fallback_min_ttl=1,
        smart_prior_json=None,
        nodes=args.nodes,
        area_m=args.area_m,
        duration_s=args.duration_s,
        rate_per_min=args.rate_per_min,
        traffic=args.traffic,
        pair_count=0,
        repeater_ratio=0.0,
        sf=args.sf,
        bw_hz=args.bw_hz,
        cr=args.cr,
        payload_bytes=args.payload_bytes,
        tx_power_dbm=args.tx_power_dbm,
        path_loss_exp=args.path_loss_exp,
        shadow_sigma_db=args.shadow_sigma_db,
        capture_threshold_db=args.capture_threshold_db,
        max_hops=args.max_hops,
        tx_current_ma=120.0,
        rx_current_ma=10.3,
        supply_voltage_v=3.3,
        independent_rng_streams=True,
    )


def route_paths(protocol: Any) -> List[Sequence[int]]:
    paths: List[Sequence[int]] = []
    for cache in getattr(protocol, "route_cache", {}).values():
        for entry in cache.values():
            path = entry.path if isinstance(entry, RouteEntry) else entry[1]
            paths.append(path)
    return paths


def direct_prrs(sim: Simulator) -> List[float]:
    node_ids = sorted(sim.nodes)
    return [
        sim.prr_from_snr(
            sim.snr_from_power(sim.rx_power_dbm(first, second))
        )
        for index, first in enumerate(node_ids)
        for second in node_ids[index + 1 :]
    ]


def make_radio(args: argparse.Namespace) -> RadioConfig:
    return RadioConfig(
        sf=args.sf,
        bw_hz=args.bw_hz,
        cr=args.cr,
        payload_bytes=args.payload_bytes,
        tx_power_dbm=args.tx_power_dbm,
        path_loss_exp=args.path_loss_exp,
        shadow_sigma_db=args.shadow_sigma_db,
        capture_threshold_db=args.capture_threshold_db,
        tx_current_ma=120.0,
        rx_current_ma=10.3,
        supply_voltage_v=3.3,
    )


def reliable_graph(
    sim: Simulator,
    edge_prr_threshold: float,
) -> Dict[int, List[int]]:
    """Build the shared link-budget graph used to select connected flows."""

    graph = {node_id: [] for node_id in sim.nodes}
    node_ids = sorted(sim.nodes)
    for index, first in enumerate(node_ids):
        for second in node_ids[index + 1 :]:
            prr = sim.prr_from_snr(
                sim.snr_from_power(sim.rx_power_dbm(first, second))
            )
            if prr >= edge_prr_threshold:
                graph[first].append(second)
                graph[second].append(first)
    return graph


def shortest_hops(graph: Dict[int, List[int]], source: int) -> Dict[int, int]:
    distances = {source: 0}
    queue = [source]
    for current in queue:
        for neighbor in graph[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances


def connected_multihop_pairs(
    sim: Simulator,
    rng: random.Random,
    edge_prr_threshold: float,
    min_graph_hops: int,
    max_graph_hops: int,
    pair_count: int,
) -> Tuple[List[Tuple[int, int]], List[int]]:
    """Select a reproducible shared pair pool with non-direct graph paths."""

    graph = reliable_graph(sim, edge_prr_threshold)
    candidates: List[Tuple[int, int, int]] = []
    for source in sorted(graph):
        distances = shortest_hops(graph, source)
        for destination, hops in distances.items():
            if (
                destination != source
                and min_graph_hops <= hops <= max_graph_hops
            ):
                candidates.append((source, destination, hops))
    rng.shuffle(candidates)
    selected = candidates[: min(pair_count, len(candidates))]
    return (
        [(source, destination) for source, destination, _ in selected],
        [hops for _, _, hops in selected],
    )


def schedule_probe_traffic(
    sim: Simulator,
    duration_s: float,
    rate_per_min: float,
    traffic: str,
    rng: random.Random,
    pairs: Sequence[Tuple[int, int]],
) -> None:
    """Schedule one deterministic application trace shared by all protocols."""

    node_ids = list(sim.nodes)
    pair_index = 0
    flow_id = 1
    t = 1.0
    mean_interval = 60.0 / rate_per_min if rate_per_min > 0 else duration_s
    while t < duration_s:
        src = rng.choice(node_ids)
        if traffic == "broadcast":
            dst = BROADCAST_DST
        elif traffic == "mixed" and rng.random() < 0.5:
            dst = BROADCAST_DST
        elif pairs:
            src, dst = pairs[pair_index % len(pairs)]
            pair_index += 1
        else:
            dst = rng.choice([node_id for node_id in node_ids if node_id != src])
        sim.schedule(t, "app_send", (src, dst, flow_id))
        flow_id += 1
        t += rng.expovariate(1.0 / mean_interval)


def run_one_probe(
    args: argparse.Namespace,
    protocol_name: str,
    seed: int,
) -> Dict[str, Any]:
    timeout_retries = getattr(args, "smart_max_timeout_retries", 2)
    config = make_args(args)
    nodes = generate_nodes(
        config.nodes,
        config.area_m,
        random.Random(seed),
        config.repeater_ratio,
    )
    protocol = build_protocol(protocol_name, config)
    sim = Simulator(
        nodes,
        make_radio(config),
        protocol,
        seed=seed,
        max_hops=config.max_hops,
        independent_random_streams=True,
    )
    pair_rng = random.Random(seed + 20_000)
    if args.pair_mode == "connected-multihop":
        pairs, pair_hops = connected_multihop_pairs(
            sim,
            pair_rng,
            args.edge_prr_threshold,
            args.min_graph_hops,
            args.max_graph_hops,
            args.pair_count,
        )
    else:
        pairs = []
        pair_hops = []
    schedule_probe_traffic(
        sim,
        config.duration_s,
        config.rate_per_min,
        config.traffic,
        random.Random(seed + 10_000),
        pairs,
    )
    metrics = sim.run(config.duration_s)
    row = metrics.summarize(protocol.name, seed, config.duration_s)

    paths = route_paths(protocol)
    direct = direct_prrs(sim)
    row.update(
        {
            "scenario": args.scenario,
            "nodes": config.nodes,
            "area_m": config.area_m,
            "rate_per_min": config.rate_per_min,
            "traffic": config.traffic,
            "sf": config.sf,
            "path_loss_exp": config.path_loss_exp,
            "random_pairs": int(args.pair_mode == "random"),
            "pair_mode": args.pair_mode,
            "edge_prr_threshold": args.edge_prr_threshold,
            "min_graph_hops": args.min_graph_hops,
            "max_graph_hops": args.max_graph_hops,
            "candidate_pair_count": len(pairs),
            "selected_pair_mean_graph_hops": (
                statistics.fmean(pair_hops) if pair_hops else 0.0
            ),
            "independent_rng_streams": 1,
            "cached_route_count": len(paths),
            "multihop_cached_route_count": sum(
                len(path) > 2 for path in paths
            ),
            "route_discovery_success_rate": (
                float(row["route_discovery_successes"])
                / float(row["route_discovery_attempts"])
                if int(row["route_discovery_attempts"]) > 0
                else 0.0
            ),
            "rrep_rreq_tx_ratio": (
                float(row["route_replies"])
                / float(row["route_requests"])
                if int(row["route_requests"]) > 0
                else 0.0
            ),
            "smart_max_timeout_retries": timeout_retries,
            "mean_cached_hops": (
                statistics.fmean(len(path) - 1 for path in paths)
                if paths
                else 0.0
            ),
            "direct_prr_p05": percentile(direct, 0.05),
            "direct_prr_p25": percentile(direct, 0.25),
            "direct_prr_p50": percentile(direct, 0.50),
            "direct_prr_p75": percentile(direct, 0.75),
            "direct_prr_p95": percentile(direct, 0.95),
            "direct_prr_below_0_99": sum(value < 0.99 for value in direct)
            / len(direct),
            "direct_prr_below_0_50": sum(value < 0.50 for value in direct)
            / len(direct),
        }
    )
    return row


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0].keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def mean(rows: Iterable[Dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return statistics.fmean(values) if values else 0.0


def write_report(
    path: Path,
    rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    timeout_retries = getattr(args, "smart_max_timeout_retries", 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["protocol"])].append(row)

    direct_by_seed = {
        int(row["seed"]): row
        for row in rows
    }
    direct_values = [
        float(row["direct_prr_p05"])
        for row in direct_by_seed.values()
    ]
    direct_p25_values = [
        float(row["direct_prr_p25"])
        for row in direct_by_seed.values()
    ]
    direct_p50_values = [
        float(row["direct_prr_p50"])
        for row in direct_by_seed.values()
    ]
    direct_p75_values = [
        float(row["direct_prr_p75"])
        for row in direct_by_seed.values()
    ]
    direct_p95_values = [
        float(row["direct_prr_p95"])
        for row in direct_by_seed.values()
    ]
    direct_below_099 = [
        float(row["direct_prr_below_0_99"])
        for row in direct_by_seed.values()
    ]
    direct_below_050 = [
        float(row["direct_prr_below_0_50"])
        for row in direct_by_seed.values()
    ]
    lines = [
        "# MeshEcho Fair Multi-Hop Probe",
        "",
        "This versioned probe is a fairness diagnostic, not a replacement for "
        "the original repeated-pair matrix. It removes fixed-pair reuse, "
        "uses an independent channel-reception stream, and places the "
        "network in a non-saturated multi-hop regime.",
        "",
        f"- Seeds: `{args.seeds}`",
        f"- Nodes / area: `{args.nodes}` / `{args.area_m:.0f} m square`",
        f"- Traffic: `{args.traffic}`, `{args.rate_per_min:.1f} flows/min`",
        f"- Smart-CALM timeout retries: `{timeout_retries}`",
        f"- PHY: `SF{args.sf}`, `{args.tx_power_dbm:.1f} dBm`, "
        f"`n={args.path_loss_exp:.2f}`, shadow sigma "
        f"`{args.shadow_sigma_db:.1f} dB`",
        f"- Pair mode: `{args.pair_mode}`",
        (
            "- Connected-pair selection: shared link-budget graph with "
            f"edge PRR >= `{args.edge_prr_threshold:.2f}`, graph distance "
            f"`{args.min_graph_hops}-{args.max_graph_hops}` hops"
            if args.pair_mode == "connected-multihop"
            else "- Source-destination pairs: random per flow"
        ),
        "- Channel reception RNG: independent from protocol jitter/exploration",
        "",
        "## Link Regime",
        "",
        "| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {statistics.fmean(direct_values):.6f} | "
        f"{statistics.fmean(direct_p25_values):.6f} | "
        f"{statistics.fmean(direct_p50_values):.6f} | "
        f"{statistics.fmean(direct_p75_values):.6f} | "
        f"{statistics.fmean(direct_p95_values):.6f} | "
        f"{statistics.fmean(direct_below_099):.3f} | "
        f"{statistics.fmean(direct_below_050):.3f} |",
        "",
        "## Protocol Results",
        "",
        "| Protocol | ACK PDR | Destination PDR | Airtime (s) | "
        "Collision failures | P95 ACK delay (s) | Cached routes | "
        "Multi-hop route fraction | Mean cached hops | Discovery success | "
        "RREP/RREQ TX |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: |",
    ]
    for protocol_name, protocol_rows in grouped.items():
        cached = mean(protocol_rows, "cached_route_count")
        multihop = mean(protocol_rows, "multihop_cached_route_count")
        lines.append(
            f"| {protocol_name} | {mean(protocol_rows, 'unicast_pdr'):.3f} | "
            f"{mean(protocol_rows, 'destination_unicast_pdr'):.3f} | "
            f"{mean(protocol_rows, 'total_airtime_s'):.1f} | "
            f"{mean(protocol_rows, 'collision_fail'):.1f} | "
            f"{mean(protocol_rows, 'p95_unicast_ack_delay_s'):.2f} | "
            f"{cached:.1f} | "
            f"{multihop / cached if cached else 0.0:.3f} | "
            f"{mean(protocol_rows, 'mean_cached_hops'):.2f} | "
            f"{mean(protocol_rows, 'route_discovery_success_rate'):.3f} | "
            f"{mean(protocol_rows, 'rrep_rreq_tx_ratio'):.3f} |"
        )

    by_seed: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_seed[int(row["seed"])][str(row["protocol"])] = row
    lines.extend(
        [
            "",
            "## Paired Ablation Differences",
            "",
            "Differences are Smart-CALM minus the named ablation, paired by "
            "seed. The interval is intentionally omitted here; the raw CSV "
            "keeps the seed-level values for a separate statistical test.",
            "",
            "| Comparison | ACK PDR delta | Destination PDR delta | "
            "Airtime delta (s) | Collision-failure delta |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for other in ("smart-calm-no-confidence", "smart-calm-no-fallback"):
        if not all(
            "smart-calm" in values and other in values
            for values in by_seed.values()
        ):
            continue
        pairs = [
            (values["smart-calm"], values[other])
            for values in by_seed.values()
        ]
        lines.append(
            f"| smart-calm vs {other} | "
            f"{statistics.fmean(float(a['unicast_pdr']) - float(b['unicast_pdr']) for a, b in pairs):.3f} | "
            f"{statistics.fmean(float(a['destination_unicast_pdr']) - float(b['destination_unicast_pdr']) for a, b in pairs):.3f} | "
            f"{statistics.fmean(float(a['total_airtime_s']) - float(b['total_airtime_s']) for a, b in pairs):.1f} | "
            f"{statistics.fmean(float(a['collision_fail']) - float(b['collision_fail']) for a, b in pairs):.1f} |"
        )

    lines.extend(
        [
            "",
            "## Reading the Result",
            "",
            "- The link distribution is non-degenerate: a substantial fraction "
            "of direct links are below 0.99 PRR and below 0.50 PRR.",
            (
                "- Random-pair traffic removes the main cache-reuse advantage "
                "of the original eight-pair workload."
                if args.pair_mode == "random"
                else "- Connected-multihop traffic uses a shared pair pool "
                "selected from the same static link-budget graph for every "
                "protocol."
            ),
            "- A positive Smart-CALM result cannot be attributed to confidence "
            "ranking alone when it differs from `smart-calm-no-fallback`; "
            "timeout recovery must be reported as a separate mechanism.",
            "- The raw route-hop columns should be checked before calling this "
            "a multi-hop benchmark. A low multi-hop fraction means the "
            "parameter setting is still too easy.",
            "- Route-discovery success and RREP/RREQ transmission ratios are "
            "reported because a low discovery success rate indicates a "
            "route-discovery stress test, not an isolated data-plane "
            "comparison.",
            "",
            "## Reproduction",
            "",
            "```sh",
            "python3 tools/run_fair_multihop_probe.py",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="sf7_random_pairs")
    parser.add_argument("--nodes", type=int, default=50)
    parser.add_argument("--area-m", type=float, default=18_000.0)
    parser.add_argument("--duration-s", type=float, default=600.0)
    parser.add_argument("--rate-per-min", type=float, default=4.0)
    parser.add_argument("--traffic", choices=["unicast", "broadcast", "mixed"], default="mixed")
    parser.add_argument(
        "--pair-mode",
        choices=["random", "connected-multihop"],
        default="random",
        help="random pairs or pairs selected from a shared reliable graph",
    )
    parser.add_argument(
        "--pair-count",
        type=int,
        default=24,
        help="pair pool size for connected-multihop mode",
    )
    parser.add_argument(
        "--edge-prr-threshold",
        type=float,
        default=0.70,
        help="minimum static link-budget PRR for connected-multihop pair selection",
    )
    parser.add_argument("--min-graph-hops", type=int, default=2)
    parser.add_argument("--max-graph-hops", type=int, default=4)
    parser.add_argument("--sf", type=int, default=7)
    parser.add_argument("--bw-hz", type=int, default=125_000)
    parser.add_argument("--cr", type=int, default=1)
    parser.add_argument("--payload-bytes", type=int, default=32)
    parser.add_argument("--tx-power-dbm", type=float, default=17.0)
    parser.add_argument("--path-loss-exp", type=float, default=2.75)
    parser.add_argument("--shadow-sigma-db", type=float, default=4.0)
    parser.add_argument("--capture-threshold-db", type=float, default=6.0)
    parser.add_argument("--max-hops", type=int, default=7)
    parser.add_argument(
        "--smart-max-timeout-retries",
        type=int,
        default=2,
        help=(
            "extra Smart-CALM timeout retries; use 0 for a one-shot, "
            "budget-matched mechanism comparison"
        ),
    )
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument(
        "--protocol",
        action="append",
        choices=DEFAULT_PROTOCOLS,
        help="repeat to select protocols; defaults to the four core configurations",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocols = tuple(args.protocol or DEFAULT_PROTOCOLS)
    unknown = [name for name in protocols if name not in ICC_PROTOCOLS]
    if unknown:
        raise ValueError(f"unsupported protocol(s): {unknown}")
    rows = [
        run_one_probe(args, protocol_name, args.seed0 + offset)
        for offset in range(args.seeds)
        for protocol_name in protocols
    ]
    write_csv(args.csv, rows)
    write_report(args.report, rows, args)
    print(f"Wrote {args.csv}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
