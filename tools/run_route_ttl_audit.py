#!/usr/bin/env python3
"""Run a paired route-cache lifetime sensitivity audit for MeshEcho.

The audit keeps topology, traffic, PHY parameters, and seed values fixed while
comparing the native MeshCore-like route-cache lifetime with a 600 s lifetime
matched to the CALM/MeshEcho line. The matched comparison is still a
protocol-bundle comparison because discovery timing and recovery behavior
remain different.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import run_one  # noqa: E402


DEFAULT_OUT = Path("results/meshecho_route_ttl_audit.csv")
DEFAULT_REPORT = Path("docs/results/meshecho_route_ttl_audit.md")


def make_args(args: argparse.Namespace, meshcore_ttl_s: float) -> argparse.Namespace:
    return argparse.Namespace(
        nodes=args.nodes,
        area_m=args.area_m,
        duration_s=args.duration_s,
        rate_per_min=args.rate_per_min,
        traffic=args.traffic,
        pair_count=args.pair_count,
        repeater_ratio=0.0,
        sf=args.sf,
        bw_hz=args.bw_hz,
        cr=args.cr,
        payload_bytes=args.payload_bytes,
        tx_power_dbm=args.tx_power_dbm,
        tx_current_ma=120.0,
        rx_current_ma=10.3,
        supply_voltage_v=3.3,
        path_loss_exp=args.path_loss_exp,
        shadow_sigma_db=args.shadow_sigma_db,
        capture_threshold_db=args.capture_threshold_db,
        max_hops=args.max_hops,
        independent_rng_streams=True,
        meshcore_route_ttl_s=meshcore_ttl_s,
        calm_route_ttl_s=600.0,
        calm_discovery_window_s=2.0,
        calm_flood_base_delay_s=0.45,
        calm_flood_jitter_s=0.65,
        calm_fallback_ttl=2,
        calm_fallback_confidence_threshold=0.0,
        calm_fallback_delay_margin_s=0.6,
        calm_hop_penalty_per_hop=0.025,
        calm_route_age_penalty=0.1,
        calm_disable_route_miss_fallback=False,
        smart_update_interval_s=30.0,
        smart_learning_rate=0.45,
        smart_exploration=0.02,
        smart_flow_timeout_s=15.0,
        smart_max_timeout_retries=0,
        smart_retry_after_fallback=False,
        smart_route_miss_fallback_ttl=0,
        smart_timeout_fallback_min_ttl=1,
        smart_prior_json=None,
    )


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


def mean_ci(values: Sequence[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0
    critical = 2.093 if len(values) == 20 else 1.96
    return (
        statistics.fmean(values),
        critical * statistics.stdev(values) / math.sqrt(len(values)),
    )


def paired_delta(
    by_seed: Dict[int, Dict[str, Dict[str, Any]]],
    first: str,
    second: str,
    metric: str,
) -> Tuple[float, float]:
    deltas = [
        float(values[first][metric]) - float(values[second][metric])
        for values in by_seed.values()
        if first in values and second in values
    ]
    return mean_ci(deltas)


def write_report(
    path: Path,
    rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_seed: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        variant = str(row["evaluation_variant"])
        grouped[variant].append(row)
        by_seed[int(row["seed"])][variant] = row

    lines = [
        "# MeshEcho Route-Cache Lifetime Sensitivity Audit",
        "",
        "This paired audit isolates the effect of the source-route cache "
        "lifetime in the current harness. Topology, application trace, PHY "
        "settings, and seed values are shared across variants. The matched "
        "comparison equalizes cache lifetime only; it does not equalize "
        "discovery timing or recovery behavior.",
        "",
        f"- Seeds: `{args.seeds}`",
        f"- Main scenario: `{args.nodes} nodes / {args.area_m:.0f} m square / "
        f"{args.duration_s:.0f} s / {args.traffic} / "
        f"{args.pair_count} fixed pairs`",
        f"- Offered load: `{args.rate_per_min:.1f} flows/min`",
        "- Independent channel-reception stream: enabled",
        "",
        "## Variant Results",
        "",
        "| Variant | Route TTL (s) | ACK PDR | Destination PDR | "
        "Airtime (s) | Route-cache hits | Route-cache misses |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in (
        "meshcore-native-ttl-300",
        "meshcore-matched-ttl-600",
        "meshecho-ttl-600",
    ):
        variant_rows = grouped.get(variant, [])
        lines.append(
            f"| {variant} | {mean(variant_rows, 'route_ttl_s'):.0f} | "
            f"{mean(variant_rows, 'unicast_pdr'):.3f} | "
            f"{mean(variant_rows, 'destination_unicast_pdr'):.3f} | "
            f"{mean(variant_rows, 'total_airtime_s'):.1f} | "
            f"{mean(variant_rows, 'route_cache_hits'):.1f} | "
            f"{mean(variant_rows, 'route_cache_misses'):.1f} |"
        )

    lines.extend(
        [
            "",
            "## Paired Differences",
            "",
            "Values are first variant minus second variant, paired by seed; "
            "the interval is a two-sided 95% t interval.",
            "",
            "| Comparison | ACK-PDR delta | Destination-PDR delta | "
            "Airtime delta (s) |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    comparisons = (
        ("meshcore-matched-ttl-600", "meshcore-native-ttl-300"),
        ("meshecho-ttl-600", "meshcore-matched-ttl-600"),
        ("meshecho-ttl-600", "meshcore-native-ttl-300"),
    )
    for first, second in comparisons:
        pdr, pdr_ci = paired_delta(by_seed, first, second, "unicast_pdr")
        destination, destination_ci = paired_delta(
            by_seed,
            first,
            second,
            "destination_unicast_pdr",
        )
        airtime, airtime_ci = paired_delta(
            by_seed,
            first,
            second,
            "total_airtime_s",
        )
        lines.append(
            f"| {first} minus {second} | "
            f"{pdr:+.3f} +/- {pdr_ci:.3f} | "
            f"{destination:+.3f} +/- {destination_ci:.3f} | "
            f"{airtime:+.1f} +/- {airtime_ci:.1f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The 300 s versus 600 s MeshCore-like comparison estimates the "
            "effect of cache lifetime without changing its routing logic.",
            "- The 600 s CALM/MeshEcho versus 600 s MeshCore-like comparison "
            "removes the route-lifetime mismatch from the headline comparison, "
            "but remains a protocol-bundle comparison.",
            "- This audit does not remove the fixed-pair, high-PRR/one-hop, "
            "or native-recovery limitations of the main matrix.",
            "",
            "## Reproduction",
            "",
            "```sh",
            "python3 tools/run_route_ttl_audit.py",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=50)
    parser.add_argument("--area-m", type=float, default=3000.0)
    parser.add_argument("--duration-s", type=float, default=1200.0)
    parser.add_argument("--rate-per-min", type=float, default=6.0)
    parser.add_argument("--traffic", choices=["unicast", "broadcast", "mixed"], default="mixed")
    parser.add_argument("--pair-count", type=int, default=8)
    parser.add_argument("--sf", type=int, default=9)
    parser.add_argument("--bw-hz", type=int, default=125_000)
    parser.add_argument("--cr", type=int, default=1)
    parser.add_argument("--payload-bytes", type=int, default=32)
    parser.add_argument("--tx-power-dbm", type=float, default=17.0)
    parser.add_argument("--path-loss-exp", type=float, default=2.7)
    parser.add_argument("--shadow-sigma-db", type=float, default=4.0)
    parser.add_argument("--capture-threshold-db", type=float, default=6.0)
    parser.add_argument("--max-hops", type=int, default=7)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument("--csv", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: List[Dict[str, Any]] = []
    variants = (
        ("meshcore", "meshcore-native-ttl-300", 300.0),
        ("meshcore", "meshcore-matched-ttl-600", 600.0),
        ("calm", "meshecho-ttl-600", 600.0),
    )
    for offset in range(args.seeds):
        seed = args.seed0 + offset
        for protocol_name, variant, route_ttl_s in variants:
            row = run_one(
                make_args(args, route_ttl_s),
                protocol_name,
                seed,
            )
            row["route_ttl_s"] = route_ttl_s
            row["evaluation_variant"] = variant
            row["scenario"] = "main_mixed_route_ttl_audit"
            rows.append(row)
    write_csv(args.csv, rows)
    write_report(args.report, rows, args)
    print(f"Wrote {args.csv}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
