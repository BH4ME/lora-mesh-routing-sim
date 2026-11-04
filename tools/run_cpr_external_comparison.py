#!/usr/bin/env python3
"""Run the paired four-protocol MeshEcho family comparison."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_cpr_experiment as cpr


DEFAULT_PROTOCOLS = ("meshecho-cpr", "meshecho", "meshtastic", "meshcore")
SUMMARY_METRICS = (
    "ack_pdr_deadline",
    "delivery_pdr_deadline",
    "tx_ledger_airtime_s",
    "tx_ledger_energy_j",
    "started_request_count",
)


@dataclass(frozen=True)
class ComparisonResult:
    runs: Tuple[Dict[str, Any], ...]
    paired: Tuple[Dict[str, Any], ...]
    summary: Tuple[Dict[str, Any], ...]


def _summary(runs: Sequence[Dict[str, Any]]) -> Tuple[Dict[str, Any], ...]:
    grouped: Dict[str, list[Dict[str, Any]]] = {}
    for row in runs:
        grouped.setdefault(str(row["protocol"]), []).append(row)
    rows = []
    for protocol, protocol_rows in grouped.items():
        for metric in SUMMARY_METRICS:
            values = [float(row[metric]) for row in protocol_rows]
            rows.append({
                "protocol": protocol,
                "metric": metric,
                "seed_count": len(values),
                "mean": statistics.fmean(values),
                "min": min(values),
                "max": max(values),
            })
    return tuple(rows)


def run_comparison(
    *,
    case_profile: str = "exposure",
    protocols: Sequence[str] = DEFAULT_PROTOCOLS,
    seeds: Sequence[int] = (92300,),
    deadline_s: float = 30.0,
    split: str = "custom",
) -> ComparisonResult:
    """Run external protocol baselines on the exact CPR identity contract.

    The CPR population runner intentionally rejects non-CPR arms. This wrapper
    temporarily extends that validation only for this separate comparison
    experiment and restores it before returning.
    """

    selected = tuple(protocols)
    if selected[0] != "meshecho-cpr":
        raise ValueError("the candidate must be the first comparison arm")
    original = cpr.CPR_PROTOCOLS
    cpr.CPR_PROTOCOLS = tuple(dict.fromkeys((*original, *selected)))
    try:
        bundle = cpr.run_matrix(
            cpr.CASE_PROFILES[case_profile], selected, tuple(seeds),
            deadline_s, split,
        )
    finally:
        cpr.CPR_PROTOCOLS = original
    return ComparisonResult(
        runs=tuple(bundle.runs),
        paired=tuple(bundle.paired),
        summary=_summary(bundle.runs),
    )


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-profile", choices=tuple(cpr.CASE_PROFILES), default="exposure")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--protocol", action="append", dest="protocols")
    parser.add_argument("--deadline-s", type=float, default=30.0)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args(argv)
    seeds = tuple(args.seeds or tuple(range(92300, 92320)))
    protocols = tuple(args.protocols or DEFAULT_PROTOCOLS)
    result = run_comparison(
        case_profile=args.case_profile,
        protocols=protocols,
        seeds=seeds,
        deadline_s=args.deadline_s,
        split="custom",
    )
    _write_csv(Path(f"{args.out_prefix}.runs.csv"), list(result.runs))
    _write_csv(Path(f"{args.out_prefix}.paired.csv"), list(result.paired))
    _write_csv(Path(f"{args.out_prefix}.summary.csv"), list(result.summary))
    print(f"wrote {args.out_prefix}.runs.csv")
    print(f"wrote {args.out_prefix}.paired.csv")
    print(f"wrote {args.out_prefix}.summary.csv")


if __name__ == "__main__":
    main()
