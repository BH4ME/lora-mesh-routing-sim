#!/usr/bin/env python3
"""Controlled route-conflict experiment for MeshEcho.

The topology contains two candidate routes from node 0 to node 5:

* short route: 0-1-2-5, with an optionally weakened link;
* long route: 0-3-4-6-5, with stronger links.

The experiment disables online learning and timeout recovery so that the
comparison isolates route-candidate admission:

* MeshEcho: select the highest-confidence candidate;
* MeshEcho no-confidence: select the shortest candidate.

This is a controlled mechanism experiment, not a replacement for the random
50-node ICC matrix.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (
    AdaptiveProfile,
    Node,
    RadioConfig,
    Simulator,
    SmartCalmMesh,
)


SRC = 0
DST = 5
SHORT_PATH = (0, 1, 2, 5)
LONG_PATH = (0, 3, 4, 6, 5)
ALLOWED_EDGES = {
    frozenset((0, 1)),
    frozenset((1, 2)),
    frozenset((2, 5)),
    frozenset((0, 3)),
    frozenset((3, 4)),
    frozenset((4, 6)),
    frozenset((6, 5)),
}

# The 1-2 link remains usable but has materially lower SNR margin. Positive
# shadowing increases path loss in the simulator.
SHORT_WEAK_EDGE = (1, 2)
LONG_WEAK_EDGE = (4, 6)
WEAK_EDGE_OPTIONS = {
    "none": None,
    "short": SHORT_WEAK_EDGE,
    "long": LONG_WEAK_EDGE,
}

CONFLICT_PROFILE = AdaptiveProfile(
    name="conflict-balanced",
    # The longest default run ends at 751 s. Keeping the cache valid longer
    # ensures every flow evaluates the same, first candidate set.
    route_ttl_s=1_200.0,
    discovery_window_s=12.0,
    fallback_confidence_threshold=0.0,
    fallback_ttl=1,
    fallback_delay_margin_s=0.6,
    hop_penalty_per_hop=0.025,
    route_age_penalty=0.1,
)


def conflict_nodes() -> List[Node]:
    """Return a fixed geometry; the edge gate below defines the test graph."""

    return [
        Node(0, 0.0, 0.0),
        Node(1, 8000.0, 0.0),
        Node(2, 16000.0, 0.0),
        Node(3, 0.0, 9000.0),
        Node(4, 8000.0, 9000.0),
        Node(5, 24000.0, 0.0),
        Node(6, 16000.0, 6000.0),
    ]


class RouteConflictSimulator(Simulator):
    """Simulator with an explicit seven-edge test graph."""

    def __init__(
        self,
        nodes: Sequence[Node],
        radio: RadioConfig,
        protocol: SmartCalmMesh,
        seed: int,
        max_hops: int,
        weak_link_shadowing_db: float,
        weak_edge: Optional[Tuple[int, int]],
    ) -> None:
        super().__init__(nodes, radio, protocol, seed=seed, max_hops=max_hops)
        for edge in ALLOWED_EDGES:
            self.link_shadowing_db[tuple(sorted(edge))] = (
                weak_link_shadowing_db
                if weak_edge is not None and tuple(sorted(edge)) == weak_edge
                else 0.0
            )

    def try_receive(self, tx, receiver):
        edge = frozenset((tx.sender, receiver))
        if receiver != tx.sender and edge not in ALLOWED_EDGES:
            # Non-edges are outside the controlled graph and are not counted as
            # reception attempts, keeping PRR focused on usable links.
            return None
        return super().try_receive(tx, receiver)


class RecordingConflictMesh(SmartCalmMesh):
    """Smart-CALM core with candidate traces for the controlled experiment."""

    def __init__(self, protocol_name: str, confidence_enabled: bool) -> None:
        super().__init__(
            protocol_name=protocol_name,
            route_ttl_s=CONFLICT_PROFILE.route_ttl_s,
            discovery_window_s=CONFLICT_PROFILE.discovery_window_s,
            flood_base_delay_s=3.0,
            flood_jitter_s=0.0,
            fallback_ttl=CONFLICT_PROFILE.fallback_ttl,
            fallback_confidence_threshold=CONFLICT_PROFILE.fallback_confidence_threshold,
            fallback_delay_margin_s=CONFLICT_PROFILE.fallback_delay_margin_s,
            hop_penalty_per_hop=CONFLICT_PROFILE.hop_penalty_per_hop,
            route_age_penalty=CONFLICT_PROFILE.route_age_penalty,
            update_interval_s=9999.0,
            flow_timeout_s=60.0,
            max_timeout_retries=0,
            profiles=(CONFLICT_PROFILE,),
            learning_enabled=False,
            fallback_enabled=True,
            confidence_enabled=confidence_enabled,
            fixed_profile_index=0,
        )
        self.candidate_trace: List[Tuple[Tuple[int, ...], float]] = []
        self.first_selected_path: Tuple[int, ...] = ()
        self.first_selected_confidence = 0.0
        self.route_discovery_attempts = 0

    def flood_delay(self, receiver=None, rx=None) -> float:
        # Stagger the two branches so the controlled candidate collection
        # measures route admission instead of an avoidable RREQ collision.
        return {
            1: 1.0,
            2: 1.0,
            3: 2.0,
            4: 1.0,
            6: 1.0,
        }.get(receiver, 1.0)

    def route_miss_recovery_ttl(self, flow_id: Optional[int] = None) -> int:
        # Keep route discovery failure from turning this into a fallback test.
        return 0

    def start_route_discovery(self, src: int, dst: int, flow_id: int) -> None:
        self.route_discovery_attempts += 1
        super().start_route_discovery(src, dst, flow_id)

    def finish_route_discovery(self, key: Tuple[int, int, int]) -> None:
        candidates = list(self.rreq_candidates.get(key, []))
        if candidates and not self.candidate_trace:
            self.candidate_trace = candidates
            self.first_selected_path, self.first_selected_confidence = (
                self.select_route_candidate(candidates, key[2])
            )
        super().finish_route_discovery(key)


def path_label(path: Optional[Tuple[int, ...]]) -> str:
    if not path:
        return ""
    return "-".join(str(node) for node in path)


def candidate_confidence(
    candidates: Iterable[Tuple[Tuple[int, ...], float]],
    path: Tuple[int, ...],
) -> float:
    for candidate_path, confidence in candidates:
        if candidate_path == path:
            return confidence
    return 0.0


def run_case(
    seed: int,
    confidence_enabled: bool,
    flow_count: int,
    flow_interval_s: float,
    weak_link_shadowing_db: float = 7.5,
    weak_edge: Optional[Tuple[int, int]] = SHORT_WEAK_EDGE,
) -> Dict[str, object]:
    if flow_count <= 0:
        raise ValueError("flow_count must be positive")
    if flow_interval_s <= 0.0:
        raise ValueError("flow_interval_s must be positive")

    protocol_name = "meshecho-confidence" if confidence_enabled else "meshecho-no-confidence"
    protocol = RecordingConflictMesh(protocol_name, confidence_enabled)
    sim = RouteConflictSimulator(
        conflict_nodes(),
        RadioConfig(
            sf=9,
            bw_hz=125_000,
            cr=1,
            payload_bytes=32,
            tx_power_dbm=17.0,
            path_loss_exp=2.7,
            shadow_sigma_db=0.0,
            capture_threshold_db=6.0,
        ),
        protocol,
        seed=seed,
        max_hops=6,
        weak_link_shadowing_db=weak_link_shadowing_db,
        weak_edge=weak_edge,
    )

    start_time = 1.0
    for index in range(flow_count):
        sim.schedule(
            start_time + index * flow_interval_s,
            "app_send",
            (SRC, DST, index + 1),
        )
    last_flow_time = start_time + (flow_count - 1) * flow_interval_s
    duration_s = last_flow_time + protocol.flow_timeout_s
    metrics = sim.run(duration_s)
    route = protocol.route_cache.get(SRC, {}).get(DST)
    final_cached_path = route.path if route is not None else ()
    final_cached_confidence = route.confidence if route is not None else 0.0
    selected_path = protocol.first_selected_path
    selected_confidence = protocol.first_selected_confidence
    short_seen = any(path == SHORT_PATH for path, _ in protocol.candidate_trace)
    long_seen = any(path == LONG_PATH for path, _ in protocol.candidate_trace)

    summary = metrics.summarize(protocol.name, seed, duration_s)
    row: Dict[str, object] = dict(summary)
    row.update(
        {
            "selected_path": path_label(selected_path),
            "final_cached_path": path_label(final_cached_path),
            "weak_link_shadowing_db": round(weak_link_shadowing_db, 6),
            "weak_edge": (
                ""
                if weak_edge is None
                else "-".join(str(node) for node in weak_edge)
            ),
            "route_discovery_attempts": protocol.route_discovery_attempts,
            "selected_confidence": round(selected_confidence, 6),
            "final_cached_confidence": round(final_cached_confidence, 6),
            "candidate_count": len(protocol.candidate_trace),
            "short_candidate_seen": int(short_seen),
            "long_candidate_seen": int(long_seen),
            "short_candidate_confidence": round(
                candidate_confidence(protocol.candidate_trace, SHORT_PATH),
                6,
            ),
            "long_candidate_confidence": round(
                candidate_confidence(protocol.candidate_trace, LONG_PATH),
                6,
            ),
            "selected_route_class": (
                "short"
                if selected_path == SHORT_PATH
                else "long"
                if selected_path == LONG_PATH
                else "other"
            ),
        }
    )
    return row


def ci95(rows: Sequence[Dict[str, object]], key: str) -> Tuple[float, float]:
    values = [float(row[key]) for row in rows]
    if len(values) < 2:
        return (statistics.fmean(values) if values else 0.0, 0.0)
    # Critical values are sufficient for the intended 20-100 seed runs.
    critical = {
        10: 2.262,
        20: 2.093,
        30: 2.045,
        50: 2.010,
        100: 1.984,
    }
    nearest = min(critical, key=lambda size: abs(size - len(values)))
    half_width = critical[nearest] * statistics.stdev(values) / math.sqrt(len(values))
    return statistics.fmean(values), half_width


def proportion(rows: Sequence[Dict[str, object]], key: str, expected: object) -> float:
    return (
        sum(row[key] == expected for row in rows) / len(rows)
        if rows
        else 0.0
    )


def write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    rows: Sequence[Dict[str, object]],
    seeds: int,
    flow_count: int,
    flow_interval_s: float,
    weak_link_shadowing_db: float,
    weak_edge: Optional[Tuple[int, int]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MeshEcho Route-Conflict Experiment",
        "",
        "This controlled experiment isolates candidate-route admission. The "
        "short path is `0-1-2-5` and the longer path is `0-3-4-6-5`; an "
        "optional extra-shadowing condition weakens one selected branch. "
        "Online learning, timeout retry, and route-miss fallback are disabled.",
        "",
        f"- Seeds: `{seeds}`",
        f"- Unicast flows per seed: `{flow_count}`",
        f"- Flow interval: `{flow_interval_s:.1f} s`",
        f"- Extra shadowing on `{path_label(weak_edge) or 'none'}`: "
        f"`{weak_link_shadowing_db:.1f} dB`",
        f"- Route cache TTL: `{CONFLICT_PROFILE.route_ttl_s:.0f} s` (one RREQ attempt per run)",
        "- MeshEcho selects the highest-confidence candidate.",
        "- MeshEcho no-confidence selects the shortest candidate.",
        "",
        "| Variant | Selected short | Selected long | Both candidates seen | ACK PDR (95% CI) | Destination PDR (95% CI) | P95 ACK delay (95% CI, s) | Airtime (95% CI, s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    both_by_variant: Dict[str, List[Dict[str, object]]] = {}
    for variant in ("meshecho-confidence", "meshecho-no-confidence"):
        variant_rows = [row for row in rows if row["protocol"] == variant]
        selected_short = proportion(variant_rows, "selected_route_class", "short")
        selected_long = proportion(variant_rows, "selected_route_class", "long")
        both_rows = [
            row
            for row in variant_rows
            if bool(row["short_candidate_seen"]) and bool(row["long_candidate_seen"])
        ]
        both_by_variant[variant] = both_rows
        both = len(both_rows) / len(variant_rows) if variant_rows else 0.0
        pdr, pdr_half = ci95(variant_rows, "unicast_pdr")
        destination_pdr, destination_half = ci95(
            variant_rows,
            "destination_unicast_pdr",
        )
        delay, delay_half = ci95(variant_rows, "p95_unicast_ack_delay_s")
        airtime, airtime_half = ci95(variant_rows, "total_airtime_s")
        lines.append(
            f"| {variant} | {selected_short:.3f} | {selected_long:.3f} | "
            f"{both:.3f} | {pdr:.3f} +/- {pdr_half:.3f} | "
            f"{destination_pdr:.3f} +/- {destination_half:.3f} | "
            f"{delay:.3f} +/- {delay_half:.3f} | "
            f"{airtime:.3f} +/- {airtime_half:.3f} |"
        )
    confidence_both = both_by_variant["meshecho-confidence"]
    no_confidence_both = both_by_variant["meshecho-no-confidence"]
    lines.extend(
        [
            "",
            "## Paired Difference",
            "",
            "Rows are paired by seed. Differences are MeshEcho confidence "
            "minus MeshEcho no-confidence.",
            "",
            "| Metric | Mean difference | 95% CI |",
            "| --- | ---: | ---: |",
        ]
    )
    confidence_by_seed = {
        int(row["seed"]): row for row in rows if row["protocol"] == "meshecho-confidence"
    }
    no_confidence_by_seed = {
        int(row["seed"]): row
        for row in rows
        if row["protocol"] == "meshecho-no-confidence"
    }
    paired_rows = [
        (confidence_by_seed[seed], no_confidence_by_seed[seed])
        for seed in sorted(confidence_by_seed.keys() & no_confidence_by_seed.keys())
    ]
    for key, label in (
        ("unicast_pdr", "ACK PDR"),
        ("destination_unicast_pdr", "Destination PDR"),
        ("total_airtime_s", "Total airtime (s)"),
    ):
        differences = [
            float(confidence_row[key]) - float(no_confidence_row[key])
            for confidence_row, no_confidence_row in paired_rows
        ]
        if len(differences) > 1:
            half_width = 1.984 * statistics.stdev(differences) / math.sqrt(len(differences))
            delta = statistics.fmean(differences)
        else:
            delta = differences[0] if differences else 0.0
            half_width = 0.0
        lines.append(f"| {label} | {delta:.3f} | +/- {half_width:.3f} |")
    if confidence_both and no_confidence_both:
        confidence_correct = sum(
            row["selected_route_class"] == "long" for row in confidence_both
        ) / len(confidence_both)
        no_confidence_short = sum(
            row["selected_route_class"] == "short" for row in no_confidence_both
        ) / len(no_confidence_both)
        lines.extend(
            [
                "",
                f"When both candidates were observed, confidence selected the "
                f"long reliable path in `{confidence_correct:.3f}` of seeds, "
                f"while no-confidence selected the short path in "
                f"`{no_confidence_short:.3f}` of seeds.",
            ]
        )
    lines.extend(
        [
            "",
        "The route-selection result should be interpreted together with "
        "`selected_path`, `candidate_*_confidence`, and the candidate "
        "capture columns in the raw CSV. This experiment is deliberately "
        "controlled: the confidence estimate and subsequent forwarding use "
        "the same static-link model. It should complement, not replace, the "
        "random-topology ICC matrix or a time-varying-channel study.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument("--flows", type=int, default=24)
    parser.add_argument("--flow-interval-s", type=float, default=30.0)
    parser.add_argument(
        "--weak-link-shadowing-db",
        type=float,
        default=7.5,
        help="Additional path loss on the selected weak edge.",
    )
    parser.add_argument(
        "--weak-edge",
        choices=tuple(WEAK_EDGE_OPTIONS),
        default="short",
        help="Which candidate branch receives the extra shadowing.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("results/meshecho_route_conflict.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/results/meshecho_route_conflict.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weak_edge = WEAK_EDGE_OPTIONS[args.weak_edge]
    rows: List[Dict[str, object]] = []
    for offset in range(args.seeds):
        seed = args.seed0 + offset
        rows.append(
            run_case(
                seed,
                True,
                args.flows,
                args.flow_interval_s,
                args.weak_link_shadowing_db,
                weak_edge,
            )
        )
        rows.append(
            run_case(
                seed,
                False,
                args.flows,
                args.flow_interval_s,
                args.weak_link_shadowing_db,
                weak_edge,
            )
        )
    write_csv(args.csv, rows)
    write_report(
        args.report,
        rows,
        args.seeds,
        args.flows,
        args.flow_interval_s,
        args.weak_link_shadowing_db,
        weak_edge,
    )
    print(f"Wrote {args.csv}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
