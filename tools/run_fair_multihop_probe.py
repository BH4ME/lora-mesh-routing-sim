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
import hashlib
import json
import math
import random
import shlex
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
    MESHECHO_ABLATIONS,
    RadioConfig,
    RouteEntry,
    Simulator,
    build_protocol,
    generate_nodes,
    percentile,
)


DEFAULT_PROTOCOLS = tuple(ICC_PROTOCOLS)
FAIR_PROBE_PROTOCOLS = (
    tuple(ICC_PROTOCOLS)
    + ("prr-product", "prr-product-fallback", "meshecho-calibrated", "meshecho-ack-evict", "prr-product-ack-evict")
    + tuple(MESHECHO_ABLATIONS)
    + ("meshecho-budgeted",)
)
DEFAULT_OUT = Path("results/meshecho_fair_multihop_probe.csv")
DEFAULT_REPORT = Path("docs/results/meshecho_fair_multihop_probe.md")


class ProbeRegimeError(ValueError):
    """Raised when a connected-multihop probe would produce degenerate evidence."""


def validate_non_degenerate_regime(
    rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    """Reject saturated links or incomplete multi-hop pair pools per seed.

    Diagnostics are duplicated for each protocol because every protocol uses
    the same seed-specific topology and pair-selection procedure. Checking
    each row still makes the quality gate robust to future protocol-specific
    topology changes and prevents an aggregate mean from hiding a bad seed.
    """

    if getattr(args, "pair_mode", "random") != "connected-multihop":
        return
    if not rows:
        raise ProbeRegimeError("connected-multihop probe produced no rows")

    requested_pairs = int(getattr(args, "pair_count", 0))
    if requested_pairs <= 0:
        raise ProbeRegimeError(
            "connected-multihop requires a positive requested pair pool"
        )
    minimum_subthreshold = float(
        getattr(args, "min_direct_prr_below_0_99", 0.10)
    )
    minimum_mean_hops = float(
        getattr(args, "min_selected_pair_mean_graph_hops", 2.0)
    )
    traffic_trace_by_seed: Dict[Any, str] = {}

    for row in rows:
        seed = row.get("seed", "?")
        protocol = row.get("protocol", "?")
        candidate_count = int(row["candidate_pair_count"])
        if candidate_count < requested_pairs:
            raise ProbeRegimeError(
                f"seed {seed} ({protocol}) pair pool has only "
                f"{candidate_count} pairs; requested {requested_pairs}"
            )
        if getattr(args, "pair_schedule", "poisson") == "fixed-once":
            expected_counts = {
                "scheduled_unicast_flows": requested_pairs,
                "scheduled_distinct_unicast_pairs": requested_pairs,
                "unicast_flows": requested_pairs,
                "observed_distinct_unicast_pairs": requested_pairs,
                "scheduled_broadcast_flows": 0,
                "broadcast_flows": 0,
            }
            mismatches = [
                f"{key}={row.get(key, 'missing')} (expected {expected})"
                for key, expected in expected_counts.items()
                if int(row.get(key, -1)) != expected
            ]
            if mismatches:
                raise ProbeRegimeError(
                    f"seed {seed} ({protocol}) fixed-once workload incomplete: "
                    + ", ".join(mismatches)
                )
            trace = str(row.get("scheduled_trace_sha256", ""))
            previous_trace = traffic_trace_by_seed.setdefault(seed, trace)
            if not trace or trace != previous_trace:
                raise ProbeRegimeError(
                    f"seed {seed} ({protocol}) traffic trace differs across protocols"
                )
        if getattr(args, "require_repeated_pairs", False):
            trace = str(row.get("scheduled_trace_sha256", ""))
            previous_trace = traffic_trace_by_seed.setdefault(seed, trace)
            if not trace or trace != previous_trace:
                raise ProbeRegimeError(
                    f"seed {seed} ({protocol}) traffic trace differs across protocols"
                )
            scheduled_flows = int(row.get("scheduled_unicast_flows", -1))
            observed_flows = int(row.get("unicast_flows", -1))
            if (
                scheduled_flows < 1
                or observed_flows != scheduled_flows
                or int(row.get("scheduled_broadcast_flows", -1)) != 0
                or int(row.get("broadcast_flows", -1)) != 0
            ):
                raise ProbeRegimeError(
                    f"seed {seed} ({protocol}) scheduled/observed unicast "
                    f"flow count differs or includes broadcast traffic: "
                    f"{scheduled_flows}/{observed_flows}"
                )
            if (
                int(row.get("scheduled_distinct_unicast_pairs", -1)) != requested_pairs
                or int(row.get("observed_distinct_unicast_pairs", -1)) != requested_pairs
            ):
                raise ProbeRegimeError(
                    f"seed {seed} ({protocol}) selected source-destination pairs "
                    f"are not all scheduled and observed"
                )
            if int(row.get("scheduled_min_flows_per_pair", -1)) < 2:
                raise ProbeRegimeError(
                    f"seed {seed} ({protocol}) each selected pair needs "
                    "at least two scheduled unicasts"
                )
            if int(row.get("scheduled_min_time_blocks_per_pair", -1)) < 2:
                raise ProbeRegimeError(
                    f"seed {seed} ({protocol}) each selected pair needs "
                    "at least two time blocks"
                )
        mean_hops = float(row["selected_pair_mean_graph_hops"])
        if mean_hops < minimum_mean_hops:
            raise ProbeRegimeError(
                f"seed {seed} ({protocol}) selected pair graph hops "
                f"{mean_hops:.3f} below required {minimum_mean_hops:.3f}"
            )
        subthreshold_fraction = float(row["direct_prr_below_0_99"])
        if subthreshold_fraction < minimum_subthreshold:
            raise ProbeRegimeError(
                f"seed {seed} ({protocol}) direct-link PRR below 0.99 "
                f"fraction {subthreshold_fraction:.3f} below required "
                f"{minimum_subthreshold:.3f}"
            )


def make_args(args: argparse.Namespace) -> argparse.Namespace:
    """Build the Namespace expected by lora_mesh_sim.build_protocol()."""

    route_ttl_s = float(getattr(args, "route_ttl_s", 600.0))
    return argparse.Namespace(
        calm_route_ttl_s=route_ttl_s,
        meshcore_route_ttl_s=route_ttl_s,
        meshcore_discovery_window_s=getattr(
            args,
            "meshcore_discovery_window_s",
            2.0,
        ),
        calm_discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
        calm_flood_base_delay_s=getattr(args, "calm_flood_base_delay_s", 0.45),
        calm_flood_jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
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
        temporal_fading_sigma_db=getattr(args, "temporal_fading_sigma_db", 0.0),
        temporal_fading_interval_s=getattr(
            args,
            "temporal_fading_interval_s",
            60.0,
        ),
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
        temporal_fading_sigma_db=getattr(args, "temporal_fading_sigma_db", 0.0),
        temporal_fading_interval_s=getattr(
            args,
            "temporal_fading_interval_s",
            60.0,
        ),
        capture_threshold_db=args.capture_threshold_db,
        tx_current_ma=120.0,
        rx_current_ma=10.3,
        supply_voltage_v=3.3,
    )


def paired_mean_ci(values: Sequence[float]) -> Tuple[float, float, float]:
    """Return a paired mean and two-sided 95% t interval."""

    if not values:
        return 0.0, 0.0, 0.0
    mean_value = statistics.fmean(values)
    if len(values) < 2:
        return mean_value, mean_value, mean_value
    critical = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
    }.get(len(values) - 1, 1.96)
    half = critical * statistics.stdev(values) / math.sqrt(len(values))
    return mean_value, mean_value - half, mean_value + half


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
    pair_schedule: str = "poisson",
) -> None:
    """Schedule one deterministic application trace shared by all protocols."""

    if pair_schedule == "fixed-once":
        if traffic != "unicast" or not pairs:
            raise ValueError("fixed-once requires unicast traffic and selected pairs")
        interval_s = duration_s / len(pairs)
        jitter_s = min(interval_s * 0.1, 5.0)
        for flow_id, (src, dst) in enumerate(pairs, start=1):
            when = (flow_id - 0.5) * interval_s + rng.uniform(-jitter_s, jitter_s)
            sim.schedule(when, "app_send", (src, dst, flow_id))
        return

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
        matched_rreq_timing=bool(getattr(args, "matched_rreq_timing", False)),
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
        getattr(args, "pair_schedule", "poisson"),
    )
    scheduled_events = sorted(
        (when, *data)
        for when, _, kind, data in sim.events
        if kind == "app_send"
    )
    scheduled = [(src, dst, flow_id) for _, src, dst, flow_id in scheduled_events]
    scheduled_unicast_pairs = [
        (src, dst) for src, dst, _ in scheduled if dst != BROADCAST_DST
    ]
    pair_send_times: Dict[Tuple[int, int], List[float]] = defaultdict(list)
    for when, src, dst, _ in scheduled_events:
        if dst != BROADCAST_DST:
            pair_send_times[(src, dst)].append(when)
    block_interval_s = max(config.temporal_fading_interval_s, 1e-9)
    scheduled_pair_counts = [
        {
            "src": src,
            "dst": dst,
            "flows": len(pair_send_times[(src, dst)]),
            "time_blocks": len(
                {int(when // block_interval_s) for when in pair_send_times[(src, dst)]}
            ),
        }
        for src, dst in sorted(pairs)
    ]
    metrics = sim.run(config.duration_s)
    row = metrics.summarize(protocol.name, seed, config.duration_s)
    discovery_records = sorted(protocol.discovery_records, key=lambda record: record.key)
    discovery_fingerprints = [
        {
            "key": list(record.key),
            "candidate_count": len(record.candidate_paths),
            "sha256": hashlib.sha256(
                json.dumps(record.candidate_paths, separators=(",", ":")).encode("ascii")
            ).hexdigest(),
        }
        for record in discovery_records
    ]
    observed_unicast_pairs = {
        (flow.src, flow.dst)
        for flow in metrics.flows.values()
        if flow.dst != BROADCAST_DST
    }

    paths = route_paths(protocol)
    direct = direct_prrs(sim)
    row.update(
        {
            "scenario": args.scenario,
            "nodes": config.nodes,
            "area_m": config.area_m,
            "rate_per_min": config.rate_per_min,
            "traffic": config.traffic,
            "pair_schedule": getattr(args, "pair_schedule", "poisson"),
            "matched_rreq_timing": int(sim.matched_rreq_timing),
            "discovery_record_count": len(discovery_records),
            "discovery_candidate_path_total": sum(
                len(record.candidate_paths) for record in discovery_records
            ),
            "discovery_multi_candidate_count": sum(
                len(record.candidate_paths) >= 2 for record in discovery_records
            ),
            "discovery_candidate_fingerprints_json": json.dumps(
                discovery_fingerprints, separators=(",", ":")
            ),
            "discovery_records_json": json.dumps(
                [
                    {
                        "key": record.key,
                        "started_at": record.started_at,
                        "closed_at": record.closed_at,
                        "candidate_paths": record.candidate_paths,
                        "selected_path": record.selected_path,
                    }
                    for record in discovery_records
                ],
                separators=(",", ":"),
            ),
            "scheduled_unicast_flows": len(scheduled_unicast_pairs),
            "scheduled_broadcast_flows": len(scheduled) - len(scheduled_unicast_pairs),
            "scheduled_distinct_unicast_pairs": len(set(scheduled_unicast_pairs)),
            "scheduled_pair_counts_json": json.dumps(
                scheduled_pair_counts, separators=(",", ":")
            ),
            "scheduled_min_flows_per_pair": min(
                (item["flows"] for item in scheduled_pair_counts), default=0
            ),
            "scheduled_min_time_blocks_per_pair": min(
                (item["time_blocks"] for item in scheduled_pair_counts), default=0
            ),
            "observed_distinct_unicast_pairs": len(observed_unicast_pairs),
            "scheduled_rate_per_min": len(scheduled) * 60.0 / config.duration_s,
            "scheduled_trace_sha256": hashlib.sha256(
                json.dumps(scheduled_events, separators=(",", ":")).encode("ascii")
            ).hexdigest(),
            "sf": config.sf,
            "path_loss_exp": config.path_loss_exp,
            "temporal_fading_sigma_db": config.temporal_fading_sigma_db,
            "temporal_fading_interval_s": config.temporal_fading_interval_s,
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
    is_cache_reuse = bool(
        getattr(args, "report_cache_reuse", hasattr(args, "route_ttl_s"))
    )
    is_feedback = bool(getattr(args, "require_repeated_pairs", False))
    fixed_once = getattr(args, "pair_schedule", "poisson") == "fixed-once"
    if fixed_once:
        opening = (
            "This one-shot multihop workload sends one unicast for each "
            "selected directed pair. It measures first-discovery behavior "
            "with no repeated source-destination pair."
        )
    elif is_feedback:
        opening = (
            "This matched-discovery, repeated-pair feedback workload measures "
            "route-cache reuse and recovery across channel time blocks. It is "
            "reported separately from the sparse first-discovery experiment."
        )
    elif is_cache_reuse:
        opening = (
            f"This versioned probe deliberately reuses a {args.pair_count}-pair connected "
            "unicast workload to measure route-cache reuse and route aging. "
            "It is a secondary diagnostic, not the primary sparse-flow "
            "multi-hop estimand."
        )
    elif args.pair_mode == "connected-multihop":
        opening = (
            "This probe cycles through a selected connected-pair pool on a "
            "Poisson application schedule. Pairs may repeat, and some selected "
            "pairs may not be observed. Channel reception uses an independent "
            "random stream."
        )
    else:
        opening = (
            "This probe samples source-destination pairs per flow instead of "
            "cycling through a selected pool. Channel reception uses an "
            "independent random stream."
        )
    traffic_summary = (
        f"- Traffic: `{args.traffic}`, "
        f"`{mean(rows, 'scheduled_rate_per_min'):.1f} scheduled flows/min` "
        "(`fixed-once`)"
        if fixed_once
        else f"- Traffic: `{args.traffic}`, `{args.rate_per_min:.1f} flows/min`"
    )
    lines = [
        "# MeshEcho Fair Multi-Hop Probe",
        "",
        opening,
        "",
        f"- Seeds: `{args.seeds}`",
        f"- Nodes / area: `{args.nodes}` / `{args.area_m:.0f} m square`",
        traffic_summary,
        f"- MeshEcho timeout-retry budget: `{timeout_retries}`",
        (
            f"- Route-cache TTL: `{args.route_ttl_s:.1f} s`"
            if is_cache_reuse
            else "- Route-cache TTL: `600.0 s` in the matched ICC matrix"
        ),
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
        f"- MeshCore-like discovery window: `{getattr(args, 'meshcore_discovery_window_s', 2.0):.2f} s`",
        f"- Matched RREQ relay timing: `{bool(getattr(args, 'matched_rreq_timing', False))}`",
        "- Channel reception RNG: independent from protocol jitter/exploration",
        (
            "- Quality gate: PASSED for every seed; direct-link PRR below "
            f"0.99 >= `{getattr(args, 'min_direct_prr_below_0_99', 0.10):.2f}`, "
            f"pair pool complete, mean graph hops >= "
            f"`{getattr(args, 'min_selected_pair_mean_graph_hops', 2.0):.2f}`"
            if args.pair_mode == "connected-multihop"
            else "- Quality gate: not required for random-pair mode"
        ),
        (
            "- Repeated-pair gate: every selected pair has at least two "
            "scheduled application unicasts across at least two scheduled "
            "time blocks; application flow counts and paired traffic traces "
            "match. Actual DATA transmission and route reuse are reflected "
            "separately by delivery and cache metrics."
            if is_feedback
            else ""
        ),
        (
            f"- Temporal block fading: sigma `{args.temporal_fading_sigma_db:.1f} dB`, "
            f"interval `{args.temporal_fading_interval_s:.1f} s`"
            if getattr(args, "temporal_fading_sigma_db", 0.0) > 0.0
            else "- Temporal block fading: disabled (static per-link shadowing)"
        ),
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

    lines.extend(
        [
            "",
            "## Application Denominators",
            "",
            "Counts are totals across seeds; pair ranges are per-seed minima "
            "and maxima. ACK and destination counts use observed unicasts "
            "as their denominator. In the protocol-results means, each seed "
            "has equal weight; pooled flow counts below can imply a different "
            "overall ratio when seed-level flow counts vary. The CSV preserves "
            "every seed's counts.",
            "",
            "| Protocol | Scheduled unicast | Observed unicast | "
            "Scheduled distinct pairs/seed | Observed distinct pairs/seed | "
            "ACKs / observed unicast | Destinations / observed unicast | "
            "Scheduled broadcast |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for protocol_name, protocol_rows in grouped.items():
        scheduled = sum(int(row["scheduled_unicast_flows"]) for row in protocol_rows)
        observed = sum(int(row["unicast_flows"]) for row in protocol_rows)
        scheduled_pairs = [
            int(row["scheduled_distinct_unicast_pairs"]) for row in protocol_rows
        ]
        observed_pairs = [
            int(row["observed_distinct_unicast_pairs"]) for row in protocol_rows
        ]
        acks = sum(int(row["unicast_acks"]) for row in protocol_rows)
        destinations = sum(int(row["unicast_deliveries"]) for row in protocol_rows)
        broadcasts = sum(int(row["scheduled_broadcast_flows"]) for row in protocol_rows)
        lines.append(
            f"| {protocol_name} | {scheduled} | {observed} | "
            f"{min(scheduled_pairs)}-{max(scheduled_pairs)} | "
            f"{min(observed_pairs)}-{max(observed_pairs)} | "
            f"{acks}/{observed} | {destinations}/{observed} | {broadcasts} |"
        )

    if is_feedback:
        rows_by_seed = {int(row["seed"]): row for row in rows}
        lines.extend(
            [
                "",
                "## Repeated-Pair Audit",
                "",
                "Each seed uses one application trace shared by all protocols. "
                "The CSV also preserves `scheduled_pair_counts_json` and the "
                "full `scheduled_trace_sha256` for per-pair inspection.",
                "",
                "| Seed | Scheduled/observed application unicasts | Selected pairs | "
                "Min scheduled unicasts/pair | Min scheduled blocks/pair |",
                "| ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for seed, row in sorted(rows_by_seed.items()):
            lines.append(
                f"| {seed} | {row['scheduled_unicast_flows']}/"
                f"{row['unicast_flows']} | "
                f"{row['scheduled_distinct_unicast_pairs']} | "
                f"{row['scheduled_min_flows_per_pair']} | "
                f"{row['scheduled_min_time_blocks_per_pair']} |"
            )
        lines.extend(
            [
                "",
                "## Feedback Diagnostics",
                "",
                "Counts and energy are means per seed. `Legacy repair events` "
                "mix cache expiry and failed discovery; they are not successful "
                "repairs. Invalidations after destination DATA are a simulator-only "
                "diagnostic of destination-delivered but ACK-unconfirmed flows; "
                "they do not prove the path remained valid at timeout and are "
                "never policy input.",
                "",
                "| Protocol | Route-cache hits | Cache misses | Route discoveries | "
                "Discovery successes | Legacy repair events | "
                "ACK timeout invalidations | Invalidations after destination DATA | "
                "Total energy (J) | Mean ACK delay (s) |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for protocol_name, protocol_rows in grouped.items():
            invalidations = statistics.fmean(
                float(row.get("ack_timeout_invalidations", 0))
                for row in protocol_rows
            )
            after_delivery = statistics.fmean(
                float(row.get("timeout_invalidations_after_destination_delivery", 0))
                for row in protocol_rows
            )
            lines.append(
                f"| {protocol_name} | {mean(protocol_rows, 'route_cache_hits'):.1f} | "
                f"{mean(protocol_rows, 'route_cache_misses'):.1f} | "
                f"{mean(protocol_rows, 'route_discovery_attempts'):.1f} | "
                f"{mean(protocol_rows, 'route_discovery_successes'):.1f} | "
                f"{mean(protocol_rows, 'route_repair_count'):.1f} | "
                f"{invalidations:.1f} | {after_delivery:.1f} | "
                f"{mean(protocol_rows, 'total_energy_j'):.1f} | "
                f"{mean(protocol_rows, 'unicast_ack_delay_s'):.2f} |"
            )

    lines.extend(
        [
            "",
            "## Discovery Candidate Audit",
            "",
            "Counts are totals across seeds. Each protocol/seed CSV row has "
            "`discovery_record_count`, `discovery_candidate_path_total`, "
            "`discovery_multi_candidate_count`, `discovery_records_json`, and "
            "`discovery_candidate_fingerprints_json`. The JSON record field "
            "contains the observed candidate and selected paths for each "
            "discovery; fingerprints support paired set comparisons.",
            "",
            "| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for protocol_name, protocol_rows in grouped.items():
        lines.append(
            f"| {protocol_name} | "
            f"{sum(int(row['discovery_record_count']) for row in protocol_rows)} | "
            f"{sum(int(row['discovery_candidate_path_total']) for row in protocol_rows)} | "
            f"{sum(int(row['discovery_multi_candidate_count']) for row in protocol_rows)} |"
        )

    by_seed: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_seed[int(row["seed"])][str(row["protocol"])] = row
    if "meshecho" in next(iter(by_seed.values()), {}):
        lines.extend(
            [
                "",
                "## Paired MeshEcho Comparisons",
                "",
                "Differences are MeshEcho minus the named comparator, paired by "
                "seed. Entries are mean deltas with two-sided 95% paired "
                "confidence intervals.",
                "",
                "| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for other in (
            "meshecho-calibrated",
            "meshcore-like",
            "etx-mesh",
            "ett-mesh",
            "prr-product-mesh",
            "prr-product-fallback-mesh",
            "minhop-mesh",
            "meshtastic-like",
        ):
            if not all(other in values for values in by_seed.values()):
                continue
            pairs = [
                (values["meshecho"], values[other])
                for values in by_seed.values()
            ]
            ack = paired_mean_ci(
                [
                    float(a["unicast_pdr"]) - float(b["unicast_pdr"])
                    for a, b in pairs
                ]
            )
            dest = paired_mean_ci(
                [
                    float(a["destination_unicast_pdr"])
                    - float(b["destination_unicast_pdr"])
                    for a, b in pairs
                ]
            )
            airtime = paired_mean_ci(
                [
                    float(a["total_airtime_s"]) - float(b["total_airtime_s"])
                    for a, b in pairs
                ]
            )
            lines.append(
                f"| MeshEcho vs {other} | "
                f"{ack[0]:+.3f} [{ack[1]:+.3f},{ack[2]:+.3f}] | "
                f"{dest[0]:+.3f} [{dest[1]:+.3f},{dest[2]:+.3f}] | "
                f"{airtime[0]:+.1f} [{airtime[1]:+.1f},{airtime[2]:+.1f}] |"
            )

        if any(
            all(variant in values for values in by_seed.values())
            for variant in MESHECHO_ABLATIONS
        ):
            lines.extend(
                [
                    "",
                    "## MeshEcho Component Ablations",
                    "",
                    "These paired rows isolate MeshEcho components while "
                    "keeping the topology, traffic, discovery budget, and "
                    "reception stream unchanged.",
                    "",
                    "| Ablation | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |",
                    "| --- | ---: | ---: | ---: |",
                ]
            )
            for other in MESHECHO_ABLATIONS:
                if not all(other in values for values in by_seed.values()):
                    continue
                pairs = [
                    (values["meshecho"], values[other])
                    for values in by_seed.values()
                ]
                ack = paired_mean_ci(
                    [
                        float(a["unicast_pdr"]) - float(b["unicast_pdr"])
                        for a, b in pairs
                    ]
                )
                dest = paired_mean_ci(
                    [
                        float(a["destination_unicast_pdr"])
                        - float(b["destination_unicast_pdr"])
                        for a, b in pairs
                    ]
                )
                airtime = paired_mean_ci(
                    [
                        float(a["total_airtime_s"])
                        - float(b["total_airtime_s"])
                        for a, b in pairs
                    ]
                )
                lines.append(
                    f"| MeshEcho vs {other} | "
                    f"{ack[0]:+.3f} [{ack[1]:+.3f},{ack[2]:+.3f}] | "
                    f"{dest[0]:+.3f} [{dest[1]:+.3f},{dest[2]:+.3f}] | "
                    f"{airtime[0]:+.1f} [{airtime[1]:+.1f},{airtime[2]:+.1f}] |"
                )

    baseline_labels = {
        "meshtastic-like": "managed flooding",
        "meshcore-like": "matched source routing",
        "etx-mesh": "ETX",
        "ett-mesh": "ETT",
        "prr-product-mesh": "PRR-product",
        "prr-product-fallback-mesh": "PRR-product with matched fallback",
        "minhop-mesh": "min-hop",
    }
    available_baselines = [
        label for name, label in baseline_labels.items() if name in grouped
    ]
    comparison_note = (
        "- MeshEcho is compared with " + ", ".join(available_baselines)
        + " under shared application traffic. Routed policies use the stated "
        "discovery window and timeout-retry budget."
        if "meshecho" in grouped and available_baselines
        else "- This run contains MeshEcho and its listed variants."
        if "meshecho" in grouped
        else "- The controlled route-conflict experiment is the surgical "
        "candidate-selection test."
    )
    variant_notes = []
    if "meshecho-budgeted" in grouped:
        variant_notes.append(
            "- The budgeted variant is an optional comparator; "
            "meshecho-no-* variants are component ablations."
        )
    elif any(name in grouped for name in MESHECHO_ABLATIONS):
        variant_notes.append("- The meshecho-no-* variants are component ablations.")
    if "meshecho-ack-evict" in grouped:
        variant_notes.append(
            "- The ACK-timeout route-invalidation variant is an optional "
            "comparator, not a meshecho-no-* component ablation."
        )
    if "meshecho-calibrated" in grouped:
        variant_notes.append(
            "- The calibrated max-min PRR variant ranks paths by the weakest "
            "model-inferred RREQ hop PRR, without an extra hop penalty; it is "
            "an experimental MeshEcho variant, not a standard baseline."
        )
    if not variant_notes:
        variant_notes.append(
            "- No MeshEcho component variants were run in this case."
        )
    scenario = str(getattr(args, "scenario", ""))
    generalization_prefix = "icc2027_generalization_"
    if scenario.startswith(generalization_prefix):
        case = scenario[len(generalization_prefix):]
        if path.stem.endswith(f"_{case}"):
            out_prefix = path.stem[: -(len(case) + 1)]
            protocol_cli_names = {
                "meshtastic-like": "meshtastic",
                "meshcore-like": "meshcore",
                "etx-mesh": "etx",
                "ett-mesh": "ett",
                "prr-product-mesh": "prr-product",
                "prr-product-fallback-mesh": "prr-product-fallback",
                "meshecho-ack-evict": "meshecho-ack-evict",
                "prr-product-ack-evict-mesh": "prr-product-ack-evict",
                "minhop-mesh": "minhop",
            }
            reproduction = " \\\n  ".join(
                [
                    "python3 tools/run_icc_generalization_experiment.py",
                    f"--case {case}",
                    f"--seeds {len(by_seed)} --seed0 {min(by_seed)}",
                    f"--out-prefix {out_prefix}",
                    *(
                        f"--protocol {protocol_cli_names.get(name, name)}"
                        for name in grouped
                    ),
                ]
            )
        else:
            reproduction = "python3 tools/run_icc_generalization_experiment.py"
    else:
        protocol_cli_names = {
            "meshtastic-like": "meshtastic",
            "meshcore-like": "meshcore",
            "etx-mesh": "etx",
            "ett-mesh": "ett",
            "prr-product-mesh": "prr-product",
            "prr-product-fallback-mesh": "prr-product-fallback",
            "meshecho-ack-evict": "meshecho-ack-evict",
            "prr-product-ack-evict-mesh": "prr-product-ack-evict",
            "minhop-mesh": "minhop",
        }
        options = [
            ("--scenario", scenario),
            ("--nodes", args.nodes),
            ("--area-m", args.area_m),
            ("--duration-s", args.duration_s),
            ("--rate-per-min", args.rate_per_min),
            ("--traffic", args.traffic),
            ("--pair-mode", args.pair_mode),
            ("--pair-count", args.pair_count),
            ("--pair-schedule", getattr(args, "pair_schedule", "poisson")),
            ("--edge-prr-threshold", args.edge_prr_threshold),
            ("--min-graph-hops", args.min_graph_hops),
            ("--max-graph-hops", args.max_graph_hops),
            ("--meshcore-discovery-window-s", getattr(args, "meshcore_discovery_window_s", 2.0)),
            ("--min-selected-pair-mean-graph-hops", getattr(args, "min_selected_pair_mean_graph_hops", 2.0)),
            ("--min-direct-prr-below-0-99", getattr(args, "min_direct_prr_below_0_99", 0.10)),
            ("--sf", args.sf),
            ("--tx-power-dbm", args.tx_power_dbm),
            ("--path-loss-exp", args.path_loss_exp),
            ("--shadow-sigma-db", args.shadow_sigma_db),
            ("--max-hops", getattr(args, "max_hops", 7)),
            ("--max-timeout-retries", timeout_retries),
            ("--seeds", len(by_seed)),
            ("--seed0", min(by_seed)),
        ]
        command_parts = ["python3 tools/run_fair_multihop_probe.py"]
        command_parts.extend(
            f"{flag} {shlex.quote(str(value))}" for flag, value in options
        )
        if getattr(args, "matched_rreq_timing", False):
            command_parts.append("--matched-rreq-timing")
        command_parts.extend(
            f"--protocol {protocol_cli_names.get(name, name)}" for name in grouped
        )
        command_parts.append(
            f"--csv {shlex.quote(str(getattr(args, 'csv', DEFAULT_OUT)))}"
        )
        command_parts.append(f"--report {shlex.quote(str(path))}")
        reproduction = " \\\n  ".join(command_parts)
    lines.extend(
        [
            "",
            "## Reading the Result",
            "",
            f"- Direct-link fractions below 0.99 PRR: "
            f"{statistics.fmean(direct_below_099):.3f}; below 0.50 PRR: "
            f"{statistics.fmean(direct_below_050):.3f}.",
            (
                "- This workload intentionally cycles over four connected "
                "pairs; route-cache hits and legacy repair events are part of "
                "the estimand."
                if is_cache_reuse
                else (
                    "- Random-pair traffic removes the main cache-reuse "
                    "advantage of the original eight-pair workload."
                    if args.pair_mode == "random"
                    else "- Connected-multihop traffic uses a shared pair pool "
                    "selected from the same static link-budget graph for every "
                    "protocol."
                )
            ),
            comparison_note,
            (
                "- PRR-product ranks observed routes by multiplying each "
                "hop's model-derived PRR from received RREQ SINR, using the "
                "same link observation as ETX. The standard comparator has "
                "no retry or fallback; "
                "under concurrent traffic, candidate sets can still differ "
                "after protocol-specific control/data transmissions."
                if "prr-product-mesh" in grouped
                else ""
            ),
            (
                "- PRR-product with matched fallback retains the same path "
                "score but enables MeshEcho's TTL-2 route-miss recovery "
                "without a same-flow timeout retry."
                if "prr-product-fallback-mesh" in grouped
                else ""
            ),
            *variant_notes,
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
            reproduction,
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
        "--pair-schedule",
        choices=["poisson", "fixed-once"],
        default="poisson",
        help="Poisson traffic or one evenly spaced unicast per selected pair",
    )
    parser.add_argument(
        "--edge-prr-threshold",
        type=float,
        default=0.70,
        help="minimum static link-budget PRR for connected-multihop pair selection",
    )
    parser.add_argument("--min-graph-hops", type=int, default=2)
    parser.add_argument("--max-graph-hops", type=int, default=4)
    parser.add_argument(
        "--meshcore-discovery-window-s",
        type=float,
        default=2.0,
        help="matched MeshCore-like route-discovery collection window",
    )
    parser.add_argument(
        "--matched-rreq-timing",
        action="store_true",
        help="use the same deterministic RREQ relay delay across routing policies",
    )
    parser.add_argument(
        "--min-direct-prr-below-0-99",
        type=float,
        default=0.10,
        help=(
            "minimum fraction of direct links below 0.99 PRR for the "
            "connected-multihop quality gate"
        ),
    )
    parser.add_argument(
        "--min-selected-pair-mean-graph-hops",
        type=float,
        default=2.0,
        help=(
            "minimum mean graph distance for the connected pair pool "
            "quality gate"
        ),
    )
    parser.add_argument("--sf", type=int, default=7)
    parser.add_argument("--bw-hz", type=int, default=125_000)
    parser.add_argument("--cr", type=int, default=1)
    parser.add_argument("--payload-bytes", type=int, default=32)
    parser.add_argument("--tx-power-dbm", type=float, default=17.0)
    parser.add_argument("--path-loss-exp", type=float, default=2.75)
    parser.add_argument("--shadow-sigma-db", type=float, default=4.0)
    parser.add_argument(
        "--temporal-fading-sigma-db",
        type=float,
        default=0.0,
        help="paired block-fading standard deviation in dB",
    )
    parser.add_argument(
        "--temporal-fading-interval-s",
        type=float,
        default=60.0,
        help="paired block-fading interval in seconds",
    )
    parser.add_argument("--capture-threshold-db", type=float, default=6.0)
    parser.add_argument("--max-hops", type=int, default=7)
    parser.add_argument(
        "--max-timeout-retries",
        "--smart-max-timeout-retries",
        dest="smart_max_timeout_retries",
        type=int,
        default=2,
        metavar="N",
        help=(
            "timeout-retry budget; use 0 for a one-shot, budget-matched "
            "MeshEcho mechanism comparison"
        ),
    )
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument(
        "--protocol",
        action="append",
        choices=FAIR_PROBE_PROTOCOLS,
        help="repeat to select protocols; defaults to the five ICC configurations",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocols = tuple(args.protocol or DEFAULT_PROTOCOLS)
    unknown = [name for name in protocols if name not in FAIR_PROBE_PROTOCOLS]
    if unknown:
        raise ValueError(f"unsupported protocol(s): {unknown}")
    rows = [
        run_one_probe(args, protocol_name, args.seed0 + offset)
        for offset in range(args.seeds)
        for protocol_name in protocols
    ]
    validate_non_degenerate_regime(rows, args)
    write_csv(args.csv, rows)
    write_report(args.report, rows, args)
    print(f"Wrote {args.csv}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
