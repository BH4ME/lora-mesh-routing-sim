#!/usr/bin/env python3
"""Audit frozen SECON plans and derive descriptive statistics and figures.

No simulator is run. Incomplete plans produce an inventory, never a selective
performance summary. Statistical resampling is independent of simulation seeds.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "secon2027-analysis-v1"
DEFAULT_ANALYSIS_SEED = 20271104
RESAMPLES = 10000
PAIR_IDENTITIES = ("scheduled_trace_sha256", "topology_sha256", "radio_sha256", "pair_pool_sha256", "environment_sha256")
LABELS = {"meshecho-cpr": "CPR", "meshecho": "Legacy ME", "meshtastic": "MT-like", "meshcore": "MC-like",
          "meshecho-cpr-noackcancel": "No ACK cancel", "meshecho-cpr-norepeat": "No repeat",
          "meshecho-cpr-norecovery": "No recovery", "meshecho-cpr-nocancel": "No ledger"}
COLORS = {"meshecho-cpr": "#0072B2", "meshecho": "#D55E00", "meshtastic": "#009E73", "meshcore": "#CC79A7",
          "meshecho-cpr-noackcancel": "#E69F00", "meshecho-cpr-norepeat": "#56B4E9", "meshecho-cpr-norecovery": "#666666"}
ABLATION_TOGGLES = {"meshecho-cpr-noackcancel": "cancel_on_ack", "meshecho-cpr-norepeat": "enable_repeat",
                    "meshecho-cpr-norecovery": "enable_recovery"}
CORE_METRICS = ("ack_pdr_deadline", "delivery_pdr_deadline", "tx_ledger_airtime_s", "started_request_count",
                "airtime_per_timely_delivery_s", "unfinished_ack_fraction", "unfinished_delivery_fraction",
                "timely_ack_latency_p50_s", "timely_ack_latency_p95_s", "timely_delivery_latency_p50_s",
                "timely_delivery_latency_p95_s", "accepted_ack_hops_mean", "timely_ack_one_hop_fraction",
                "source_repeat_tx_count", "source_recovery_tx_count", "ack_cancel_success_count",
                "ack_cancel_check_count", "ack_cancel_success_per_decoded_ack_check", "capacity_eviction_count",
                "capacity_canceled_count", "canceled_request_count", "route_cache_hits", "route_cache_misses",
                "initial_routed_flow_count", "initial_flood_flow_count", "source_path_fault_exposed_flows",
                "fault_period_active_flows", "fault_period_enqueued_flows", "fault_period_active_with_initial_before_window_flows",
                "fault_exposed_with_structural_alternative_flows", "fault_exposed_with_budget_feasible_alternative_flows", "delivery_without_timely_ack_flows",
                "unreachable_at_enqueue_flows", "in_flight_at_cutoff_count", "mean_queue_wait_s")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def jsonl(path: Path) -> Iterable[dict]:
    with path.open() as stream:
        for ordinal, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"non-object JSONL row: {path}:{ordinal}")
                yield value


def scalar(value: str) -> Any:
    if value == "":
        return None
    if value in {"True", "False"}:
        return value == "True"
    try:
        return json.loads(value)
    except ValueError:
        return value


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linearly interpolated quantile; empty success sets stay undefined."""
    if not 0 <= q <= 1:
        raise ValueError("quantile outside [0, 1]")
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    if not all(math.isfinite(v) for v in ordered):
        raise ValueError("nonfinite observation")
    pos = q * (len(ordered) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def bootstrap_mean(values: Sequence[float | None], *, seed: int = DEFAULT_ANALYSIS_SEED,
                   resamples: int = RESAMPLES) -> dict:
    """Seed-level mean and percentile interval; never drop undefined seeds."""
    if not values or resamples < 1:
        raise ValueError("nonempty observations and positive resampling count required")
    defined = [float(v) for v in values if v is not None]
    if not all(math.isfinite(v) for v in defined):
        raise ValueError("nonfinite observation")
    missing = len(values) - len(defined)
    base = {"n": len(values), "undefined_n": missing, "mean": None, "ci_low": None, "ci_high": None,
            "ci_type": "descriptive-unadjusted-percentile-bootstrap-95", "small_sample_unstable": len(values) < 10}
    if missing:
        return {**base, "status": "undefined-all-seed-estimand"}
    if len(defined) == 1:
        return {**base, "status": "single-seed-no-interval", "mean": defined[0]}
    import numpy as np
    rng = np.random.default_rng(seed)
    data = np.asarray(defined, dtype=float)
    samples = data[rng.integers(0, len(data), size=(resamples, len(data)))].mean(axis=1)
    bounds = np.quantile(samples, [0.025, 0.975], method="linear")
    return {**base, "status": "descriptive", "mean": statistics.fmean(defined),
            "ci_low": float(bounds[0]), "ci_high": float(bounds[1])}


def paired_effect(focus: Mapping[int, float | None], comparator: Mapping[int, float | None], *,
                  transform: str, seed: int = DEFAULT_ANALYSIS_SEED, resamples: int = RESAMPLES) -> tuple[dict, list]:
    if set(focus) != set(comparator) or not focus:
        raise ValueError("paired seed populations differ or are empty")
    if transform not in {"difference", "log_ratio"}:
        raise ValueError("unknown effect transform")
    pairs = []
    for sim_seed in sorted(focus):
        left, right = focus[sim_seed], comparator[sim_seed]
        reason, value = None, None
        if left is None or right is None:
            reason = "undefined-input"
        elif not math.isfinite(left) or not math.isfinite(right):
            raise ValueError("nonfinite pair")
        elif transform == "log_ratio" and (left <= 0 or right <= 0):
            reason = "nonpositive-airtime-log-ratio-undefined"
        else:
            value = left - right if transform == "difference" else math.log(left / right)
        pairs.append({"seed": sim_seed, "focus_value": left, "comparator_value": right,
                      "effect": value, "undefined_reason": reason})
    result = bootstrap_mean([p["effect"] for p in pairs], seed=seed, resamples=resamples)
    if transform == "log_ratio":
        for name in ("mean", "ci_low", "ci_high"):
            value = result[name]
            result["ratio_" + name] = math.exp(value) if value is not None else None
    return {**result, "transform": transform}, pairs


def structural_hops(environment: Mapping[str, Any] | None, src: int, dst: int, when: float) -> int | None:
    if not environment or "neighbor_edges" not in environment:
        return None
    removed = {tuple(sorted(edge)) for fault in environment.get("faults", [])
               if fault["start_s"] <= when < fault["end_s"] and fault["attenuation_db"] >= 60
               for edge in fault["edges"]}
    graph: dict[int, list[int]] = defaultdict(list)
    for a, b in environment["neighbor_edges"]:
        if tuple(sorted((a, b))) not in removed:
            graph[a].append(b)
            graph[b].append(a)
    queue, seen = deque([(src, 0)]), {src}
    while queue:
        node, hops = queue.popleft()
        if node == dst:
            return hops
        for other in graph[node]:
            if other not in seen:
                seen.add(other)
                queue.append((other, hops + 1))
    return None


def repair_stage(tx: Mapping[str, Any], protocol: str) -> str:
    if tx["packet_kind"] in {"RREQ", "RREP"}:
        return "discovery"
    if protocol.startswith("meshecho-cpr"):
        marker = tx.get("repair_index")
        if marker not in {None, 1, 2}:
            raise ValueError("unknown CPR stage marker")
        return {None: "initial", 1: "repeat", 2: "recovery"}[marker]
    return "fallback" if tx["packet_kind"] == "FALLBACK" else "initial"


def summarize_run(*, raw: dict, flows: Sequence[dict], transmissions: Sequence[dict],
                  actions: Sequence[dict], requests: Sequence[dict], acks: Sequence[dict],
                  rx_attempts: Iterable[dict], identity: dict, cancel_checks_observable: bool = True,
                  max_hops: int = 6) -> dict:
    """Reconstruct physical metrics without trusting legacy reserved-TX aliases."""
    if not flows or len({f["flow_id"] for f in flows}) != len(flows):
        raise ValueError("empty/duplicate scheduled population")
    if len({tx["tx_id"] for tx in transmissions}) != len(transmissions):
        raise ValueError("duplicate physical TX")
    flow_by_id = {f["flow_id"]: f for f in flows}
    tx_by_id = {tx["tx_id"]: tx for tx in transmissions}
    cutoff = float(raw["drain_until_s"])
    costs: dict[tuple, dict] = {}
    by_flow: dict[int, list] = defaultdict(list)
    total_airtime = 0.0
    for tx in transmissions:
        if tx["start"] > cutoff or tx["end"] < tx["start"] or tx["flow_id"] not in flow_by_id:
            raise ValueError("future/negative/unjoined physical TX")
        toa = float(tx["end"]) - float(tx["start"])
        if abs(toa - float(tx["toa_s"])) > 1e-8:
            raise ValueError("TX ToA mismatch")
        total_airtime += toa
        by_flow[tx["flow_id"]].append(tx)
        key = (tx["packet_kind"], repair_stage(tx, raw["protocol"]))
        cost = costs.setdefault(key, {"packet_kind": key[0], "stage": key[1], "tx_count": 0, "airtime_s": 0.0})
        cost["tx_count"] += 1
        cost["airtime_s"] += toa
    if abs(total_airtime - float(raw["tx_ledger_airtime_s"])) > 1e-7 or len(transmissions) != int(raw["started_request_count"]):
        raise ValueError("physical evidence differs from ledger summary")
    accepted = {}
    for ack in acks:
        if ack.get("accepted"):
            if ack["flow_id"] in accepted:
                raise ValueError("multiple accepted ACKs")
            accepted[ack["flow_id"]] = ack
    details = []
    ack_latencies, delivered_latencies, timely_hops = [], [], []
    environment = identity.get("common_environment")
    for flow in flows:
        fid = flow["flow_id"]
        ack_time, delivered = flow.get("accepted_ack_at"), flow.get("first_delivery_at")
        ack_ok = ack_time is not None and ack_time <= flow["deadline_at"]
        delivery_ok = delivered is not None and delivered <= flow["deadline_at"]
        if ack_ok != flow["ack_by_deadline"] or delivery_ok != flow["delivery_by_deadline"]:
            raise ValueError("deadline flag differs from raw timestamps")
        if (ack_time is not None) != (fid in accepted):
            raise ValueError("ACK metric has no matching provenance")
        ack = accepted.get(fid)
        if ack and abs(float(ack["accepted_at"]) - ack_time) > 1e-8:
            raise ValueError("ACK provenance timestamp mismatch")
        hops = len(ack["reverse_path"]) - 1 if ack else None
        ack_latency = ack_time - flow["enqueued_at"] if ack_ok else None
        delivery_latency = delivered - flow["enqueued_at"] if delivery_ok else None
        if ack_latency is not None:
            if ack_latency < 0:
                raise ValueError("negative ACK latency")
            ack_latencies.append(ack_latency)
            timely_hops.append(hops)
        if delivery_latency is not None:
            if delivery_latency < 0:
                raise ValueError("negative delivery latency")
            delivered_latencies.append(delivery_latency)
        source = [tx for tx in by_flow[fid] if tx["sender"] == flow["src"] and tx["packet_kind"] in {"DATA", "FLOOD", "FALLBACK"}]
        initial = min(source, key=lambda tx: tx["start"]) if source else None
        # These time-overlap populations are broader than carried-path exposure.
        # An ACK-completed flow is no longer active; destination-only delivery
        # leaves the source awaiting its ACK until the fixed deadline/cutoff.
        faults = environment.get("faults", []) if environment else []
        active_until = min(float(flow["deadline_at"]), cutoff, float(ack_time) if ack_time is not None else math.inf)
        overlapping_faults = [fault for fault in faults
                              if max(flow["enqueued_at"], fault["start_s"]) < min(active_until, fault["end_s"])]
        enqueued_during_fault = any(fault["start_s"] <= flow["enqueued_at"] < fault["end_s"] for fault in faults)
        fault_edges = set()
        if environment and initial and initial["packet_kind"] == "DATA":
            path = initial["path"]
            edges = {tuple(sorted(edge)) for edge in zip(path, path[1:])}
            for fault in environment.get("faults", []):
                if fault["start_s"] <= initial["start"] < fault["end_s"]:
                    fault_edges.update(edges & {tuple(sorted(edge)) for edge in fault["edges"]})
        alternative = structural_hops(environment, flow["src"], flow["dst"], initial["start"]) if initial else None
        details.append({"flow_id": fid, "src": flow["src"], "dst": flow["dst"], "enqueued_at": flow["enqueued_at"],
                        "deadline_at": flow["deadline_at"], "ack_by_deadline": ack_ok, "delivery_by_deadline": delivery_ok,
                        "timely_ack_latency_s": ack_latency, "timely_delivery_latency_s": delivery_latency,
                        "accepted_ack_hops": hops, "source_physical_data_count": len(source),
                        "initial_action": flow.get("initial_action"), "source_path_fault_edges": len(fault_edges),
                        "source_initial_tx_at": initial["start"] if initial else None, "active_until_s": active_until,
                        "fault_period_active": bool(overlapping_faults), "fault_period_enqueued": enqueued_during_fault,
                        "fault_period_active_with_initial_before_window": bool(initial and any(initial["start"] < fault["start_s"] for fault in overlapping_faults)),
                        "structural_hops_at_enqueue": structural_hops(environment, flow["src"], flow["dst"], flow["enqueued_at"]),
                        "structural_hops_at_initial_tx": alternative,
                        "fault_exposed_with_structural_alternative": bool(fault_edges and alternative is not None),
                        "fault_exposed_with_budget_feasible_alternative": bool(fault_edges and alternative is not None and alternative <= max_hops),
                        "delivery_without_timely_ack": delivery_ok and not ack_ok})
    rx_counts = Counter()
    for rx in rx_attempts:
        tx = tx_by_id.get(rx["tx_id"])
        if tx is None:
            raise ValueError("RX without physical TX")
        relation = "other_listener"
        path, index = tx.get("path", []), tx.get("path_index", 0)
        if tx["packet_kind"] == "ACK" and 0 <= index < len(path) and rx["receiver"] == path[index]:
            relation = "designated_next_hop"
        elif tx["packet_kind"] in {"DATA", "RREP"} and 0 <= index < len(path) - 1 and rx["receiver"] == path[index + 1]:
            relation = "designated_next_hop"
        elif tx["packet_kind"] in {"FLOOD", "FALLBACK", "RREQ"} or (tx["packet_kind"] == "DATA" and index + 1 >= len(path)):
            relation = "broadcast_listener"
        if rx["receiver"] == tx["sender"]:
            relation = "self"
        rx_counts[(tx["packet_kind"], relation, rx["reason"], bool(rx["decoded"]))] += 1
    events = Counter(e.get("event") for e in actions)
    checks = [e for e in actions if e.get("event") == "cpr-cancel-check"]
    successful_checks = sum(bool(e.get("canceled")) for e in checks)
    successes = events["cpr-cancel"]
    if cancel_checks_observable and successful_checks != successes:
        raise ValueError("ACK cancellation checks/success events disagree")
    capacity = [e for e in actions if e.get("event") == "state-eviction" and e.get("reason") == "capacity"]
    is_cpr = raw["protocol"].startswith("meshecho-cpr")
    source_txs = [t for t in transmissions if t["sender"] == flow_by_id[t["flow_id"]]["src"]]
    ack_count, delivery_count = len(ack_latencies), len(delivered_latencies)
    queue_wait = [float(r["queue_wait_s"]) for r in requests if r.get("queue_wait_s") is not None]
    metrics = {
        "scheduled_unicast_flows": len(flows), "ack_by_deadline": ack_count, "delivery_by_deadline": delivery_count,
        "ack_pdr_deadline": ack_count / len(flows), "delivery_pdr_deadline": delivery_count / len(flows),
        "tx_ledger_airtime_s": total_airtime, "started_request_count": len(transmissions),
        "airtime_per_timely_delivery_s": total_airtime / delivery_count if delivery_count else None,
        "unfinished_ack_fraction": 1 - ack_count / len(flows), "unfinished_delivery_fraction": 1 - delivery_count / len(flows),
        "timely_ack_latency_p50_s": percentile(ack_latencies, .5), "timely_ack_latency_p95_s": percentile(ack_latencies, .95),
        "timely_delivery_latency_p50_s": percentile(delivered_latencies, .5), "timely_delivery_latency_p95_s": percentile(delivered_latencies, .95),
        "accepted_ack_hops_mean": statistics.fmean(len(a["reverse_path"]) - 1 for a in accepted.values()) if accepted else None,
        "timely_ack_one_hop_fraction": sum(h == 1 for h in timely_hops) / len(timely_hops) if timely_hops else None,
        "source_repeat_tx_count": sum(t["packet_kind"] == "DATA" and t.get("repair_index") == 1 for t in source_txs) if is_cpr else 0,
        "source_recovery_tx_count": sum(t["packet_kind"] == "FLOOD" and t.get("repair_index") == 2 for t in source_txs) if is_cpr else 0,
        "repeat_request_count": events["repeat-request"], "recovery_request_count": events["recovery-request"],
        "ack_cancel_success_count": successes, "ack_cancel_check_count": len(checks) if cancel_checks_observable else None,
        "ack_cancel_success_per_decoded_ack_check": successful_checks / len(checks) if checks else None,
        "capacity_eviction_count": len(capacity), "capacity_canceled_count": sum(bool(e.get("pending_canceled")) for e in capacity),
        "canceled_request_count": sum(r["status"] == "canceled" for r in requests),
        "route_cache_hits": raw.get("route_cache_hits"), "route_cache_misses": raw.get("route_cache_misses"),
        "initial_routed_flow_count": sum(f.get("initial_action") == "R_INITIAL" for f in flows) if is_cpr else None,
        "initial_flood_flow_count": sum(f.get("initial_action") == "F_INITIAL" for f in flows) if is_cpr else None,
        "source_path_fault_exposed_flows": sum(d["source_path_fault_edges"] > 0 for d in details),
        "fault_period_active_flows": sum(d["fault_period_active"] for d in details),
        "fault_period_enqueued_flows": sum(d["fault_period_enqueued"] for d in details),
        "fault_period_active_with_initial_before_window_flows": sum(d["fault_period_active_with_initial_before_window"] for d in details),
        "fault_exposed_with_structural_alternative_flows": sum(d["fault_exposed_with_structural_alternative"] for d in details),
        "fault_exposed_with_budget_feasible_alternative_flows": sum(d["fault_exposed_with_budget_feasible_alternative"] for d in details),
        "delivery_without_timely_ack_flows": sum(d["delivery_without_timely_ack"] for d in details),
        "unreachable_at_enqueue_flows": sum(d["structural_hops_at_enqueue"] is None for d in details) if environment else None,
        "in_flight_at_cutoff_count": sum(t["end"] > cutoff for t in transmissions),
        "mean_queue_wait_s": statistics.fmean(queue_wait) if queue_wait else None,
    }
    for metric in ("ack_pdr_deadline", "delivery_pdr_deadline"):
        if abs(metrics[metric] - float(raw[metric])) > 1e-10:
            raise ValueError("reconstructed reliability differs from CSV")
    return {"metrics": metrics, "flows": details, "costs": list(costs.values()),
            "rx": [{"packet_kind": k[0], "receiver_relation": k[1], "reason": k[2], "decoded": k[3], "count": n}
                   for k, n in sorted(rx_counts.items())],
            "requests": [{"status": status, "count": n} for status, n in sorted(Counter(r["status"] for r in requests).items())],
            "actions": [{"event": event, "count": n} for event, n in sorted(events.items())],
            "ack_outcomes": [{"accepted": key[0], "reason": key[1], "count": n} for key, n in
                             sorted(Counter((bool(a.get("accepted")), a.get("rejection_reason") or "accepted") for a in acks).items())]}


def scoped_seed(analysis_seed: int, scope: Any) -> int:
    return int(digest([analysis_seed, scope])[:16], 16)


def comparison_policy(left: Mapping[int, dict], right: Mapping[int, dict], protocol: str) -> dict:
    """Validate component isolation using resolved, pre-attach parameters."""
    if not protocol.startswith("meshecho-cpr-"):
        return {"comparison_kind": "baseline"}
    toggle = ABLATION_TOGGLES.get(protocol)
    differences, unexpected, reasons = [], set(), set()
    for seed in sorted(left):
        focus = left[seed].get("resolved_protocol_parameters")
        control = right[seed].get("resolved_protocol_parameters")
        if not isinstance(focus, dict) or not isinstance(control, dict):
            reasons.add("missing-resolved-protocol-parameters")
            unexpected.add("__missing_resolved_parameters__")
            continue
        for field in sorted(set(focus) | set(control)):
            if (field in focus) != (field in control) or focus.get(field) != control.get(field):
                differences.append({"seed": seed, "field": field, "focus_value": focus.get(field),
                                    "comparator_value": control.get(field), "focus_present": field in focus,
                                    "comparator_present": field in control})
                if field not in {"name", toggle}:
                    unexpected.add(field)
        if toggle and (focus.get(toggle) is not True or control.get(toggle) is not False):
            reasons.add("expected-component-toggle-true-to-false-missing")
    if protocol == "meshecho-cpr-nocancel":
        kind = "component-policy"
        reasons.add("legacy-nocancel-disables-whole-ledger-policy")
    elif toggle is None:
        kind = "mixed-policy"
        reasons.add("no-isolated-component-contract-for-protocol")
    else:
        kind = "mixed-policy" if unexpected or reasons else "ablation"
    return {"comparison_kind": kind, "resolved_parameter_differences": differences,
            "unexpected_parameter_fields": sorted(unexpected), "comparison_validation_reasons": sorted(reasons),
            "allowed_parameter_differences": ["name", toggle] if toggle else []}


def aggregate_runs(runs: Sequence[dict], plans: Mapping[str, dict], *, analysis_seed: int, resamples: int) -> tuple[list, list, list]:
    grouped = defaultdict(list)
    for run in runs:
        grouped[(run["plan_sha256"], run["case_id"], run["arm_id"])].append(run)
    summaries = []
    for (plan_hash, case_id, arm_id), rows in sorted(grouped.items()):
        expected = set(plans[plan_hash]["matrix"]["seeds"])
        if {r["seed"] for r in rows} != expected or len(rows) != len(expected):
            raise ValueError("summary has missing/duplicated planned seeds")
        rows.sort(key=lambda r: r["seed"])
        meta = {k: rows[0][k] for k in ("plan_sha256", "experiment_id", "stage", "case_id", "scenario", "configuration", "arm_id", "protocol")}
        for metric in CORE_METRICS:
            result = bootstrap_mean([r[metric] for r in rows], seed=scoped_seed(analysis_seed, [plan_hash, case_id]), resamples=resamples)
            summaries.append({**meta, "metric": metric, **result})
    contrasts, pairs = [], []
    for plan_hash, plan in plans.items():
        for case in plan["matrix"]["cases"]:
            arms = [a for a in plan["matrix"]["arms"] if "arms" not in case or a["id"] in case["arms"]]
            focus = [a for a in arms if a["protocol"] == "meshecho-cpr"]
            if not focus:
                continue
            if len(focus) != 1:
                raise ValueError("ambiguous CPR reference in a case")
            left = {r["seed"]: r for r in grouped[(plan_hash, case["id"], focus[0]["id"]) ]}
            for arm in arms:
                if arm == focus[0]:
                    continue
                right = {r["seed"]: r for r in grouped[(plan_hash, case["id"], arm["id"]) ]}
                if set(left) != set(right) or not left:
                    raise ValueError("missing paired run")
                for sim_seed in left:
                    if any(left[sim_seed][key] != right[sim_seed][key] for key in PAIR_IDENTITIES):
                        raise ValueError("paired runs do not share exogenous identities")
                meta = {"plan_sha256": plan_hash, "experiment_id": plan["matrix"]["experiment_id"], "stage": plan["matrix"]["stage"],
                        "case_id": case["id"], "scenario": case["scenario"], "configuration": case["configuration"],
                        "focus_arm": focus[0]["id"], "comparator_arm": arm["id"], "comparator_protocol": arm["protocol"],
                        **comparison_policy(left, right, arm["protocol"])}
                for metric, transform in (("ack_pdr_deadline", "difference"), ("delivery_pdr_deadline", "difference"), ("tx_ledger_airtime_s", "log_ratio")):
                    effect, raw_pairs = paired_effect({s: r[metric] for s, r in left.items()}, {s: r[metric] for s, r in right.items()},
                                                     transform=transform, seed=scoped_seed(analysis_seed, [plan_hash, case["id"]]), resamples=resamples)
                    contrasts.append({**meta, "metric": metric, **effect})
                    pairs.extend({**meta, "metric": metric, **pair} for pair in raw_pairs)
    return summaries, contrasts, pairs


def write_csv(path: Path, rows: Sequence[dict]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("x", newline="") as stream:
        if fields:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list, tuple)) else v for k, v in row.items()})


def write_json(path: Path, value: Any) -> None:
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def summarize_costs(cost_rows: Sequence[dict], runs: Sequence[dict]) -> list:
    """Use all seeds in the denominator, including zero occurrences of a cell."""
    grouped = defaultdict(list)
    for run in runs:
        grouped[(run["plan_sha256"], run["case_id"], run["arm_id"])].append(run)
    output = []
    for group, seed_runs in grouped.items():
        selected = [r for r in cost_rows if (r["plan_sha256"], r["case_id"], r["arm_id"]) == group]
        cells = sorted({(r["packet_kind"], r["stage"]) for r in selected})
        total = sum(r["tx_ledger_airtime_s"] for r in seed_runs)
        if abs(sum(r["airtime_s"] for r in selected) - total) > 1e-7:
            raise ValueError("cost partition does not add to complete airtime")
        for kind, stage in cells:
            rows = [r for r in selected if (r["packet_kind"], r["stage"]) == (kind, stage)]
            value = sum(r["airtime_s"] for r in rows)
            output.append({"plan_sha256": group[0], "case_id": group[1], "arm_id": group[2],
                           "protocol": seed_runs[0]["protocol"], "packet_kind": kind, "stage": stage,
                           "seed_count": len(seed_runs), "mean_airtime_s": value / len(seed_runs),
                           "mean_tx_count": sum(r["tx_count"] for r in rows) / len(seed_runs),
                           "fraction_of_complete_airtime": value / total if total else None})
    return output


def load_series(summaries: Sequence[dict], runs: Sequence[dict], plans: Mapping[str, dict]) -> list[dict]:
    """Match effective per-seed parameters; never select a protocol's first arm."""
    def normalized(value):
        if isinstance(value, dict):
            return {key: normalized(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalized(item) for item in value]
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    run_groups, summary_index, families = defaultdict(list), {}, defaultdict(list)
    for run in runs:
        run_groups[(run["plan_sha256"], run["case_id"], run["arm_id"])].append(run)
    for row in summaries:
        key = (row["plan_sha256"], row["case_id"], row["arm_id"], row["metric"])
        if key in summary_index:
            raise ValueError("duplicate load summary for one case/arm/metric")
        summary_index[key] = row
    for ph, plan in plans.items():
        expected_seeds = set(plan["matrix"]["seeds"])
        for case in plan["matrix"]["cases"]:
            if case["scenario"] not in {"S1", "S3"} or case["environment"].get("faults"):
                continue
            clean = {k: v for k, v in case["case"].items() if k not in {"key", "rate_per_min"}}
            config = digest(normalized([ph, case["configuration"], clean, case["environment"], case["deadline_s"]]))
            for arm in plan["matrix"]["arms"]:
                if "arms" in case and arm["id"] not in case["arms"]:
                    continue
                key = (ph, case["id"], arm["id"])
                evidence = sorted(run_groups[key], key=lambda row: row["seed"])
                if (len(evidence) != len(expected_seeds) or {r["seed"] for r in evidence} != expected_seeds
                        or any(not isinstance(r.get("resolved_protocol_parameters"), dict) for r in evidence)):
                    continue  # Missing effective identity cannot establish an all-else-fixed line.
                effective = digest(normalized([[r["seed"], r["resolved_protocol_parameters"]] for r in evidence]))
                metrics = {metric: summary_index.get((*key, metric))
                           for metric in ("ack_pdr_deadline", "tx_ledger_airtime_s")}
                if any(row is None for row in metrics.values()):
                    continue
                families[(config, arm["protocol"], effective)].append(
                    {"plan_sha256": ph, "case_id": case["id"], "arm_id": arm["id"],
                     "configuration": case["configuration"], "rate_per_min": case["case"]["rate_per_min"],
                     "metrics": metrics})
    output = []
    for (config, protocol, effective), points in sorted(families.items()):
        # Equivalent defaults/overrides may have different IDs at different loads.
        # Multiple arms at a load remain distinct instead of pooling or picking one.
        if len({p["rate_per_min"] for p in points}) == len(points):
            candidates = [points]
        else:
            by_arm = defaultdict(list)
            for point in points:
                by_arm[point["arm_id"]].append(point)
            candidates = list(by_arm.values())
        for selected in candidates:
            rates = [p["rate_per_min"] for p in selected]
            if len(set(rates)) < 2:
                continue
            if len(set(rates)) != len(rates):
                raise ValueError("ambiguous duplicate load point for one effective arm")
            arms = sorted({p["arm_id"] for p in selected})
            output.append({"configuration_identity": config, "protocol": protocol,
                           "effective_parameter_identity": effective, "arm_ids": arms,
                           "label": " / ".join(arms), "points": sorted(selected, key=lambda p: p["rate_per_min"])})
    return output


def make_plots(out_dir: Path, summaries: list, contrasts: list, flow_rows: list, cost_rows: list,
               plans: Mapping[str, dict], runs: Sequence[dict] = ()) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})
    files = []
    def save(fig, name):
        for ext in ("pdf", "svg"):
            path = out_dir / (name + "." + ext)
            fig.savefig(path, bbox_inches="tight", metadata={"Creator": "SECON reproducible analysis", "Title": name})
            files.append(path.name)
        plt.close(fig)
    cases = list(dict.fromkeys((r["plan_sha256"], r["case_id"]) for r in summaries))
    fig, axes = plt.subplots(len(cases), 2, figsize=(10, max(3, 2.3 * len(cases))), squeeze=False, constrained_layout=True)
    for index, key in enumerate(cases):
        for col, metric in enumerate(("ack_pdr_deadline", "tx_ledger_airtime_s")):
            rows = [r for r in summaries if (r["plan_sha256"], r["case_id"]) == key and r["metric"] == metric]
            primary = [r for r in rows if r["protocol"] in {"meshecho-cpr", "meshecho", "meshtastic", "meshcore"}]
            rows = primary or rows
            ax = axes[index, col]
            for pos, row in enumerate(rows):
                value = row["mean"]
                if value is None:
                    continue
                err = [[max(0, value - row["ci_low"])], [max(0, row["ci_high"] - value)]] if row["ci_low"] is not None else None
                ax.errorbar(pos, value, yerr=err, fmt="o", capsize=3, color=COLORS.get(row["protocol"], "#555555"))
            ax.set_xticks(range(len(rows)), [LABELS.get(r["protocol"], r["arm_id"]) for r in rows], rotation=25, ha="right")
            ax.set_ylabel("Timely ACK fraction" if col == 0 else "Whole-network TX airtime (s)")
            ax.set_title(f"{rows[0]['experiment_id']} · {key[1]} · n={rows[0]['n']} seeds", fontsize=9)
            ax.grid(axis="y", alpha=.2)
            if col == 0:
                ax.set_ylim(-.03, 1.03)
    fig.suptitle("Seed means and descriptive, unadjusted 95% intervals; n<10 unstable", fontsize=11)
    save(fig, "main_results")
    for kind, name in (("baseline", "paired_effects"), ("ablation", "ablation_effects")):
        chosen = [r for r in contrasts if r["comparison_kind"] == kind]
        if not chosen:
            continue
        fig, axes = plt.subplots(1, 2, figsize=(11, max(3, .30 * len(chosen) / 3 + 1.5)), constrained_layout=True)
        for col, metric in enumerate(("ack_pdr_deadline", "tx_ledger_airtime_s")):
            rows = [r for r in chosen if r["metric"] == metric]
            ax = axes[col]
            for pos, row in enumerate(rows):
                scale = 100 if col == 0 else 1
                value = row["mean"]
                if value is None:
                    ax.text(0, pos, "undefined (zero airtime)", fontsize=8)
                    continue
                lo, hi = row["ci_low"], row["ci_high"]
                err = [[max(0, value - lo) * scale], [max(0, hi - value) * scale]] if lo is not None else None
                ax.errorbar(value * scale, pos, xerr=err, fmt="o", capsize=2, color=COLORS.get(row["comparator_protocol"], "#555555"))
            ax.set_yticks(range(len(rows)), [r["case_id"] + " / " + LABELS.get(r["comparator_protocol"], r["comparator_arm"]) for r in rows], fontsize=8)
            ax.axvline(0, color="#888888", linewidth=.7)
            ax.invert_yaxis()
            ax.set_xlabel("CPR − control timely ACK (percentage points)" if col == 0 else "Mean log(CPR airtime / control airtime)")
            ax.grid(axis="x", alpha=.2)
        fig.suptitle("Paired by seed; descriptive unadjusted 95% intervals", fontsize=11)
        save(fig, name)
    fig, axes = plt.subplots(len(cases), 1, figsize=(10, max(3, 2.7 * len(cases))), squeeze=False, constrained_layout=True)
    for i, key in enumerate(cases):
        ax = axes[i, 0]
        selected = [f for f in flow_rows if (f["plan_sha256"], f["case_id"]) == key]
        for arm in dict.fromkeys(f["arm_id"] for f in selected):
            rows = [f for f in selected if f["arm_id"] == arm]
            delays = sorted(f["timely_ack_latency_s"] for f in rows if f["timely_ack_latency_s"] is not None)
            protocol = rows[0]["protocol"]
            unfinished = 1 - len(delays) / len(rows)
            label = f"{LABELS.get(protocol, arm)}; unfinished {unfinished:.1%}"
            if delays:
                ax.step(delays, np.arange(1, len(delays) + 1) / len(delays), where="post", label=label, color=COLORS.get(protocol))
            else:
                ax.plot([], [], label=label, color=COLORS.get(protocol))
        ax.set(title=key[1], xlabel="Timely ACK latency (s)", ylabel="Success-only empirical CDF", ylim=(0, 1.02))
        ax.legend(fontsize=7, ncols=2, loc="lower right")
    fig.suptitle("Pooled descriptive successful-flow CDF; failures retained in unfinished fractions", fontsize=10)
    save(fig, "latency")
    # Each segment is one disjoint packet-kind × stage cell; never add two partitions.
    groups = list(dict.fromkeys((r["plan_sha256"], r["case_id"], r["arm_id"]) for r in cost_rows))
    cells = sorted({(r["packet_kind"], r["stage"]) for r in cost_rows})
    fig, ax = plt.subplots(figsize=(11, max(3, .27 * len(groups) + 1.5)), constrained_layout=True)
    bottom = np.zeros(len(groups))
    for kind, stage in cells:
        values = []
        for key in groups:
            n = len(plans[key[0]]["matrix"]["seeds"])
            values.append(sum(r["airtime_s"] for r in cost_rows if (r["plan_sha256"], r["case_id"], r["arm_id"]) == key
                              and (r["packet_kind"], r["stage"]) == (kind, stage)) / n)
        ax.barh(range(len(groups)), values, left=bottom, label=f"{kind}/{stage}")
        bottom += values
    ax.set_yticks(range(len(groups)), [f"{k[1]} / {k[2]}" for k in groups], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Mean complete TX airtime per seed (s)")
    ax.legend(fontsize=7, ncols=3)
    save(fig, "cost_decomposition")
    load_groups = defaultdict(list)
    for series in load_series(summaries, runs, plans):
        load_groups[series["configuration_identity"]].append(series)
    if load_groups:
        fig, axes = plt.subplots(len(load_groups), 2, figsize=(10, 3 * len(load_groups)), squeeze=False, constrained_layout=True)
        for i, family in enumerate(load_groups.values()):
            for col, metric in enumerate(("ack_pdr_deadline", "tx_ledger_airtime_s")):
                ax = axes[i, col]
                for series in family:
                    points = [(p["rate_per_min"], p["metrics"][metric]["mean"]) for p in series["points"]]
                    # NaN breaks a line at an undefined all-seed estimand.
                    ax.plot([p[0] for p in points], [p[1] if p[1] is not None else np.nan for p in points],
                            "o-", label=series["label"], color=COLORS.get(series["protocol"]))
                ax.set(xlabel="Offered flows/min", ylabel="Timely ACK fraction" if col == 0 else "TX airtime (s)", title=family[0]["points"][0]["configuration"])
                ax.legend(fontsize=7)
        fig.suptitle("Matched load points; each line holds effective arm parameters fixed", fontsize=11)
        save(fig, "load_curve")
    return files


def analyze_plans(plan_paths: Sequence[Path], out_dir: Path, *, root: Path = ROOT) -> dict:
    from tools import secon2027_experiment as experiment
    root = root.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    report = {"schema": SCHEMA, "status": "auditing", "created_at": started_at,
              "analysis_source_sha256": file_sha(Path(__file__)), "plans": [], "failures": []}
    try:
        plans, audits, inventory = {}, [], []
        for supplied in plan_paths:
            path = (supplied if supplied.is_absolute() else root / supplied).resolve()
            audit = experiment.audit_plan(path, root)
            plan = json.loads(path.read_text())
            ph = plan["plan_sha256"]
            if ph in plans:
                raise ValueError("duplicate plan input")
            plans[ph] = plan
            audits.append(audit)
            report["plans"].append({"path": str(path.relative_to(root)), "sha256": file_sha(path), "plan_sha256": ph,
                                    "source_snapshot": plan["source_snapshot"], "tested_version": plan["tested_version"], "audit": audit})
            success = {r["run_key"]: r for r in audit["completed"]}
            for spec in plan["runs"]:
                inventory.append({"plan_sha256": ph, "experiment_id": plan["matrix"]["experiment_id"], "case_id": spec["case_id"],
                                  "arm_id": spec["arm_id"], "seed": spec["seed"], "run_key": spec["run_key"],
                                  "status": "completed" if spec["run_key"] in success else "failed-or-pending" if spec["run_key"] in audit["failed"] else "missing",
                                  "attempt_path": success.get(spec["run_key"], {}).get("attempt_path")})
                for failed in sorted((root / "results/secon2027/runs" / spec["run_key"]).glob("attempt-*/failure.json")):
                    report["failures"].append({"path": str(failed.relative_to(root)), "sha256": file_sha(failed), "record": json.loads(failed.read_text())})
        write_csv(out_dir / "planned_runs.csv", inventory)
        if any(a["status"] != "complete" for a in audits):
            report.update(status="incomplete", performance_summary_created=False,
                          reason="All requested planned arms/seeds are required; no partial performance aggregation.")
            write_json(out_dir / "analysis.json", report)
            return report
        settings = {(p["matrix"]["statistics"].get("analysis_seed", DEFAULT_ANALYSIS_SEED),
                     p["matrix"]["statistics"].get("bootstrap_resamples", RESAMPLES)) for p in plans.values()}
        if len(settings) != 1:
            raise ValueError("plans specify incompatible analysis resampling settings; analyze separately")
        analysis_seed, resamples = settings.pop()
        if type(analysis_seed) is not int or type(resamples) is not int or resamples != RESAMPLES:
            raise ValueError("expected integer analysis-only seed and exactly 10000 bootstrap resamples")
        runs, flow_rows, cost_rows, rx_rows, request_rows, action_rows, ack_rows = [], [], [], [], [], [], []
        for ph, plan in plans.items():
            audit = next(a for a in audits if a["plan_sha256"] == ph)
            complete = {r["run_key"]: r for r in audit["completed"]}
            source = root / plan["snapshot_path"] / "source/lora_mesh_sim.py"
            observable = "cpr-cancel-check" in source.read_text()
            for spec in plan["runs"]:
                attempt = root / complete[spec["run_key"]]["attempt_path"]
                with (attempt / "evidence.runs.csv").open(newline="") as stream:
                    raw_rows = list(csv.DictReader(stream))
                if len(raw_rows) != 1:
                    raise ValueError("run key does not contain exactly one CSV row")
                raw = {k: scalar(v) for k, v in raw_rows[0].items()}
                identity = json.loads((attempt / "evidence.identities.json").read_text())[str(spec["seed"])]
                data = summarize_run(raw=raw, identity=identity, cancel_checks_observable=observable,
                                     max_hops=int(spec["case"]["case"].get("max_hops", 6)),
                                     **{key: list(jsonl(attempt / ("evidence." + suffix + ".jsonl")))
                                        for key, suffix in (("flows", "flows"), ("transmissions", "transmissions"), ("actions", "actions"),
                                                            ("requests", "requests"), ("acks", "acks"))},
                                     rx_attempts=jsonl(attempt / "evidence.rx_attempts.jsonl"))
                meta = {"plan_sha256": ph, "experiment_id": plan["matrix"]["experiment_id"], "stage": plan["matrix"]["stage"],
                        "case_id": spec["case_id"], "scenario": spec["case"]["scenario"], "configuration": spec["case"]["configuration"],
                        "arm_id": spec["arm_id"], "protocol": spec["arm"]["protocol"], "seed": spec["seed"], "run_key": spec["run_key"]}
                runs.append({**meta, **data["metrics"], **{k: raw[k] for k in PAIR_IDENTITIES},
                             "resolved_protocol_parameters": identity.get("protocol_parameters_by_arm", {}).get(spec["arm"]["protocol"]),
                             "attempt_path": str(attempt.relative_to(root)), "manifest_sha256": file_sha(attempt / "evidence.manifest.json"),
                             "source_snapshot": plan["source_snapshot"], "tested_version": plan["tested_version"],
                             "wall_seconds": complete[spec["run_key"]]["wall_seconds"],
                             "evidence_bytes": sum(p.stat().st_size for p in attempt.iterdir() if p.is_file())})
                for target, key in ((flow_rows, "flows"), (cost_rows, "costs"), (rx_rows, "rx"), (request_rows, "requests"), (action_rows, "actions"), (ack_rows, "ack_outcomes")):
                    target.extend({**meta, **r} for r in data[key])
        summaries, contrasts, pairs = aggregate_runs(runs, plans, analysis_seed=analysis_seed, resamples=resamples)
        tables = {"runs": runs, "summary": summaries, "paired_effects": contrasts, "paired_seed_effects": pairs,
                  "flow_diagnostics": flow_rows, "cost_kind_stage": cost_rows, "rx_outcomes": rx_rows,
                  "cost_summary": summarize_costs(cost_rows, runs),
                  "request_statuses": request_rows, "action_counts": action_rows, "ack_outcomes": ack_rows}
        for name, rows in tables.items():
            write_csv(out_dir / (name + ".csv"), rows)
        plot_files = make_plots(out_dir, summaries, contrasts, flow_rows, cost_rows, plans, runs)
        import matplotlib
        import numpy as np
        report.update(status="complete", performance_summary_created=True, completed_runs=len(runs),
                      analysis_seed=analysis_seed, bootstrap_resamples=resamples, ci="descriptive-unadjusted-95-percentile-bootstrap",
                      bootstrap_rng="numpy.random.default_rng(sha256(analysis_seed,plan_sha256,case_id)[:64bits])",
                      unit="seed", no_confirmatory_or_noninferiority_claim=True,
                      small_sample_unstable=any(len(p["matrix"]["seeds"]) < 10 for p in plans.values()),
                      source_versions=sorted({p["tested_version"] for p in plans.values()}),
                      environment={"python": platform.python_version(), "numpy": np.__version__, "matplotlib": matplotlib.__version__},
                      tables={name: len(rows) for name, rows in tables.items()}, plots=plot_files,
                      limitations=["Plan/case/snapshot scopes are never pooled across plans.",
                                   "No undefined seed is silently removed from a mean or paired interval.",
                                   "Latency CDF pools timely successes descriptively; unfinished fractions include every scheduled flow.",
                                   "RX losses count receiver opportunities, not independent packets or proof of flow-level cause.",
                                   "Cancellation rate uses decoded-ACK checks, including ineligible checks; it is not an eligible-opportunity success rate.",
                                   "Structural alternatives are offline topology descriptions, not realized RF reachability.",
                                   "Fault-period activity/enqueue counts are time-overlap populations; they do not imply an attempted fault edge.",
                                   "Only comparisons with resolved parameters differing solely in the declared component toggle/name enter the clean ablation panel; mixed and whole-component policies remain in CSV tables.",
                                   "Only observed matching load configurations are connected in a load curve."])
        report["files"] = {p.name: {"sha256": file_sha(p), "bytes": p.stat().st_size} for p in sorted(out_dir.iterdir()) if p.is_file()}
        write_json(out_dir / "analysis.json", report)
        return report
    except BaseException as error:
        report.update(status="failed", error=repr(error), performance_summary_created=False)
        if not (out_dir / "analysis.json").exists():
            write_json(out_dir / "analysis.json", report)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, action="append", required=True, help="frozen plan; repeat to audit several without pooling them")
    parser.add_argument("--out-dir", type=Path, required=True, help="new exclusive analysis directory (existing paths are rejected)")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root containing plans and immutable evidence")
    args = parser.parse_args(argv)
    report = analyze_plans(args.plan, args.out_dir, root=args.root.resolve())
    print(json.dumps({"status": report["status"], "out_dir": str(args.out_dir.resolve()), "completed_runs": report.get("completed_runs")}, sort_keys=True))
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
