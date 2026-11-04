#!/usr/bin/env python3
"""Inspect every immutable formal run and prospective claim gate; never simulate."""
from collections import Counter, defaultdict, deque
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parent / "repo"
PAIR_IDENTITIES = ("scheduled_trace_sha256", "topology_sha256", "radio_sha256", "pair_pool_sha256", "environment_sha256")
CONTROL_COMPONENTS = {"meshecho-cpr-noackcancel": ("cancel_on_ack", "cancel_successes"),
                      "meshecho-cpr-norepeat": ("enable_repeat", "source_repeats"),
                      "meshecho-cpr-norecovery": ("enable_recovery", "source_recoveries")}


def lines(path):
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def edge(a, b):
    return tuple(sorted((a, b)))


def intended(tx):
    path, index = tx["path"], tx["path_index"]
    if tx["packet_kind"] in {"DATA", "RREP"} and 0 <= index < len(path) - 1:
        return path[index + 1]
    if tx["packet_kind"] == "ACK" and 0 <= index < len(path):
        return path[index]
    return None


def q(values, quantile):
    if not values:
        return None
    values = sorted(values)
    pos = quantile * (len(values) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def shortest(env, source, destination, time):
    removed = {edge(*e) for fault in env.get("faults", [])
               if fault["start_s"] <= time < fault["end_s"] and fault["attenuation_db"] >= 60
               for e in fault["edges"]}
    graph = defaultdict(list)
    for a, b in env["neighbor_edges"]:
        if edge(a, b) not in removed:
            graph[a].append(b)
            graph[b].append(a)
    queue, seen = deque([(source, 0)]), {source}
    while queue:
        node, hops = queue.popleft()
        if node == destination:
            return hops
        for other in graph[node]:
            if other not in seen:
                seen.add(other)
                queue.append((other, hops + 1))
    return None


def inspect(spec, attempt):
    completion = json.loads((attempt / "completion.json").read_text())
    identity = json.loads((attempt / "evidence.identities.json").read_text())[str(spec["seed"])]
    env = identity["common_environment"]
    faults = env.get("faults", [])
    flows = {f["flow_id"]: f for f in lines(attempt / "evidence.flows.jsonl")}
    txs = {t["tx_id"]: t for t in lines(attempt / "evidence.transmissions.jsonl")}
    actions = list(lines(attempt / "evidence.actions.jsonl"))
    requests = list(lines(attempt / "evidence.requests.jsonl"))
    acks = list(lines(attempt / "evidence.acks.jsonl"))
    with (attempt / "evidence.runs.csv").open() as stream:
        raw = next(csv.DictReader(stream))
    cutoff = float(raw["drain_until_s"])
    assert all(t["start"] <= cutoff and t["end"] >= t["start"] for t in txs.values())
    airtime = sum(t["end"] - t["start"] for t in txs.values())
    assert abs(airtime - float(raw["tx_ledger_airtime_s"])) < 1e-7
    assert len(txs) == int(raw["started_request_count"])
    by_flow, source_txs = defaultdict(list), []
    for tx in txs.values():
        by_flow[tx["flow_id"]].append(tx)
        if tx["sender"] == flows[tx["flow_id"]]["src"] and tx["packet_kind"] in {"DATA", "FLOOD", "FALLBACK"}:
            source_txs.append(tx)
    initial = {}
    for tx in sorted(source_txs, key=lambda t: (t["start"], t["tx_id"])):
        initial.setdefault(tx["flow_id"], tx)
    fault_active, fault_enqueued, initial_before, initial_exposed = set(), set(), set(), set()
    active_alt_hops = Counter()
    for fid, flow in flows.items():
        stop = min(cutoff, flow["deadline_at"], flow["accepted_ack_at"] if flow["accepted_ack_at"] is not None else math.inf)
        first = initial.get(fid)
        for fault in faults:
            start, end = fault["start_s"], fault["end_s"]
            if start <= flow["enqueued_at"] < end:
                fault_enqueued.add(fid)
            if max(start, flow["enqueued_at"]) < min(end, stop):
                fault_active.add(fid)
                hops = shortest(env, flow["src"], flow["dst"], max(start, flow["enqueued_at"]))
                active_alt_hops[str(hops)] += 1
                if first and first["start"] < start:
                    initial_before.add(fid)
            if first and first["packet_kind"] == "DATA" and start <= first["start"] < end:
                path_edges = {edge(a, b) for a, b in zip(first["path"], first["path"][1:])}
                if path_edges & {edge(*e) for e in fault["edges"]}:
                    initial_exposed.add(fid)
    fault_txs, fault_data_flows, fault_before_flows = {}, set(), set()
    frame_overlap_only = []
    for tx in txs.values():
        receiver = intended(tx)
        if receiver is None:
            continue
        for fault in faults:
            if edge(tx["sender"], receiver) not in {edge(*e) for e in fault["edges"]}:
                continue
            if fault["start_s"] <= tx["start"] < fault["end_s"]:
                record = {k: tx[k] for k in ("tx_id", "flow_id", "packet_kind", "sender", "start", "end", "repair_index", "path", "path_index")}
                record["intended_receiver"] = receiver
                record["initial_source_tx_at"] = initial.get(tx["flow_id"], {}).get("start")
                record["initial_source_before_fault"] = record["initial_source_tx_at"] is not None and record["initial_source_tx_at"] < fault["start_s"]
                fault_txs[tx["tx_id"]] = record
                if tx["packet_kind"] == "DATA":
                    fault_data_flows.add(tx["flow_id"])
                    if record["initial_source_before_fault"]:
                        fault_before_flows.add(tx["flow_id"])
            elif max(tx["start"], fault["start_s"]) < min(tx["end"], fault["end_s"]):
                frame_overlap_only.append(tx["tx_id"])
    neighbors = {edge(*e) for e in env["neighbor_edges"]}
    all_rx, intended_rx, neighbor_rx, fault_rx = Counter(), Counter(), Counter(), Counter()
    intended_by_kind = defaultdict(Counter)
    for rx in lines(attempt / "evidence.rx_attempts.jsonl"):
        tx = txs[rx["tx_id"]]
        if rx["receiver"] == tx["sender"]:
            continue
        all_rx[rx["reason"]] += 1
        if edge(tx["sender"], rx["receiver"]) in neighbors:
            neighbor_rx[rx["reason"]] += 1
        if rx["receiver"] == intended(tx):
            intended_rx[rx["reason"]] += 1
            intended_by_kind[tx["packet_kind"]][rx["reason"]] += 1
            if tx["tx_id"] in fault_txs:
                fault_rx[rx["reason"]] += 1
                fault_txs[tx["tx_id"]]["rx_reason"] = rx["reason"]
                fault_txs[tx["tx_id"]]["rx_decoded"] = rx["decoded"]
    protocol = spec["arm"]["protocol"]
    is_cpr = protocol.startswith("meshecho-cpr")
    pre_fault_cache_evidence = []
    if is_cpr:
        parameters = identity.get("protocol_parameters_by_arm", {}).get(protocol, {})
        for fault in faults:
            start = fault["start_s"]
            for src, dst in sorted({(f["src"], f["dst"]) for f in flows.values()}):
                relevant = [a for a in actions if a.get("src") == src and a.get("dst") == dst and a["time"] < start]
                confirmed = [a for a in relevant if a["event"] == "ack-accept"
                             and a.get("cache_update") in {"refreshed-same-path", "installed-matching-epoch"}]
                latest = max(confirmed, key=lambda a:(a["time"],a["action_ordinal"])) if confirmed else None
                invalidations = [a for a in relevant if latest and (a["time"],a["action_ordinal"]) > (latest["time"],latest["action_ordinal"])
                                 and a["event"] == "timeout" and a.get("cache_timeout_effect") in {"evicted","quarantined"}]
                last_invalidation = max(invalidations,key=lambda a:(a["time"],a["action_ordinal"])) if invalidations else None
                path = latest["path"] if latest else []
                expires = latest["time"] + parameters["route_ttl_s"] if latest else None
                pre_fault_cache_evidence.append({"src":src,"dst":dst,"fault_start_s":start,
                    "last_logged_cache_confirmation_at":latest["time"] if latest else None,
                    "last_confirmed_path":path,"inferred_expires_at":expires,
                    "last_later_timeout_effect":last_invalidation["cache_timeout_effect"] if last_invalidation else None,
                    "ready_from_logged_confirmation_and_timeout_events":bool(latest and expires > start and not last_invalidation),
                    "last_confirmed_path_intersects_fault":bool({edge(a,b) for a,b in zip(path,path[1:])} & {edge(*e) for e in fault["edges"]})})
    repeats = [t for t in source_txs if is_cpr and t["packet_kind"] == "DATA" and t["repair_index"] == 1]
    recoveries = [t for t in source_txs if is_cpr and t["packet_kind"] == "FLOOD" and t["repair_index"] == 2]
    timely_acks = [f["accepted_ack_at"] - f["enqueued_at"] for f in flows.values() if f["ack_by_deadline"]]
    timely_deliveries = [f["first_delivery_at"] - f["enqueued_at"] for f in flows.values() if f["delivery_by_deadline"]]
    cost = Counter()
    for tx in txs.values():
        kind = tx["packet_kind"]
        stage = "discovery" if kind in {"RREQ", "RREP"} else {None:"initial",1:"repeat",2:"recovery"}.get(tx["repair_index"],"other") if is_cpr else "fallback" if kind == "FALLBACK" else "initial"
        cost[f"{kind}/{stage}"] += tx["end"] - tx["start"]
    assert abs(sum(cost.values()) - airtime) < 1e-7
    event_counts = Counter(a["event"] for a in actions)
    event_action_reason_counts = Counter((str(a.get("event")), str(a.get("action")), str(a.get("reason"))) for a in actions)
    flow_action_reason_counts = Counter((str(f.get("initial_action")), str(f.get("decision_reason"))) for f in flows.values())
    capacity = [a for a in actions if a["event"] == "state-eviction" and a.get("reason") == "capacity"]
    waits = [r["queue_wait_s"] for r in requests if r.get("queue_wait_s") is not None]
    accepted = [a for a in acks if a["accepted"]]
    ack_by_flow = {a["flow_id"]:a for a in accepted}
    exposed_flow_outcomes = []
    for fid in sorted(fault_data_flows):
        flow, ack = flows[fid], ack_by_flow.get(fid)
        exposed_flow_outcomes.append({"flow_id":fid,"src":flow["src"],"dst":flow["dst"],
            "initial_source_tx_at":initial.get(fid,{}).get("start"),
            "enqueued_at":flow["enqueued_at"],"first_delivery_at":flow["first_delivery_at"],
            "accepted_ack_at":flow["accepted_ack_at"],"delivery_by_deadline":flow["delivery_by_deadline"],
            "ack_by_deadline":flow["ack_by_deadline"],"source_repeat":any(t["flow_id"] == fid for t in repeats),
            "source_recovery":any(t["flow_id"] == fid for t in recoveries),
            "accepted_ack_stage":ack["repair_index"] if ack else None,
            "accepted_ack_path":ack["reverse_path"] if ack else None})
    structural_pairs = [{"fault_start_s":fault["start_s"],"src":src,"dst":dst,
                         "hops":shortest(env,src,dst,fault["start_s"])}
                        for fault in faults for src,dst in spec["case"]["environment"]["endpoint_pairs"]]
    return {"run_key":spec["run_key"],"case_id":spec["case_id"],"scenario":spec["case"]["scenario"],
            "configuration":spec["case"]["configuration"],"arm_id":spec["arm_id"],"protocol":protocol,"seed":spec["seed"],
            "deadline_s":spec["case"]["deadline_s"],"cutoff_s":cutoff,"pair_identities":{key:raw[key] for key in PAIR_IDENTITIES},
            "wall_seconds":completion["wall_seconds"],"peak_rss_native":completion["audit"]["peak_rss_native"],
            "peak_rss_unit":completion["audit"]["peak_rss_unit"],
            "attempt_bytes":sum(p.stat().st_size for p in attempt.iterdir() if p.is_file()),
            "event_jsonl_bytes":sum(p.stat().st_size for p in attempt.glob('evidence.*.jsonl')),
            "flow_count":len(flows),"timely_ack_count":len(timely_acks),"timely_delivery_count":len(timely_deliveries),
            "timely_data_and_ack":sum(f["delivery_by_deadline"] and f["ack_by_deadline"] for f in flows.values()),
            "timely_data_without_ack":sum(f["delivery_by_deadline"] and not f["ack_by_deadline"] for f in flows.values()),
            "no_timely_data":sum(not f["delivery_by_deadline"] for f in flows.values()),
            "timely_ack_without_timely_data":sum(f["ack_by_deadline"] and not f["delivery_by_deadline"] for f in flows.values()),
            "source_routed_initial_tx_count":sum(t["packet_kind"] == "DATA" and t["repair_index"] is None for t in source_txs) if is_cpr else None,
            "ack_pdr":len(timely_acks)/len(flows),"delivery_pdr":len(timely_deliveries)/len(flows),
            "airtime_s":airtime,"physical_tx_count":len(txs),"airtime_per_delivery_s":airtime/len(timely_deliveries) if timely_deliveries else None,
            "ack_latency_p50_s":q(timely_acks,.5),"ack_latency_p95_s":q(timely_acks,.95),
            "delivery_latency_p50_s":q(timely_deliveries,.5),"delivery_latency_p95_s":q(timely_deliveries,.95),
            "initial_actions":dict(Counter(str(f.get("initial_action")) for f in flows.values())),
            "flow_action_reason_counts":[{"action":a,"reason":r,"count":n} for (a,r),n in sorted(flow_action_reason_counts.items())],
            "event_action_reason_counts":[{"event":e,"action":a,"reason":r,"count":n} for (e,a,r),n in sorted(event_action_reason_counts.items())],
            "accepted_ack_hops":dict(Counter(str(len(a["reverse_path"])-1) for a in accepted)),
            "source_repeats":len(repeats),"source_recoveries":len(recoveries),
            "repeat_flow_ids":[t["flow_id"] for t in repeats],"recovery_flow_ids":[t["flow_id"] for t in recoveries],
            "recovery_after_destination_delivery":sum(flows[t["flow_id"]]["first_delivery_at"] is not None and flows[t["flow_id"]]["first_delivery_at"] < t["start"] for t in recoveries),
            "accepted_ack_stage":dict(Counter(str(a["repair_index"]) for a in accepted)),
            "event_counts":dict(event_counts),"capacity_evictions":len(capacity),
            "capacity_evictions_by_node":dict(Counter(str(a.get("node")) for a in capacity)),"ledger_peak_occupancy":None,
            "capacity_pending_canceled":sum(bool(a.get("pending_canceled")) for a in capacity),
            "cancel_checks":event_counts["cpr-cancel-check"],"cancel_successes":event_counts["cpr-cancel"],
            "request_status":dict(Counter(r["status"] for r in requests)),
            "request_no_start_reason":dict(Counter(str(r.get("no_start_reason")) for r in requests if r["status"] != "started")),
            "queue_wait_mean_s":statistics.fmean(waits) if waits else None,"queue_wait_p95_s":q(waits,.95),
            "all_listener_rx":dict(all_rx),"neighbor_listener_rx":dict(neighbor_rx),"intended_rx":dict(intended_rx),
            "intended_rx_by_kind":dict(intended_by_kind),"fault_intended_rx":dict(fault_rx),
            "fault_enqueued_flows":len(fault_enqueued),"fault_active_flows":len(fault_active),
            "fault_active_initial_before_flows":len(initial_before),"fault_initial_carried_path_exposed_flows":len(initial_exposed),
            "fault_physical_intended_tx":len(fault_txs),"fault_physical_data_flows":len(fault_data_flows),
            "fault_physical_data_flows_initial_before":len(fault_before_flows),"fault_edge_tx_details":list(fault_txs.values()),
            "fault_frame_overlap_but_start_outside_tx_ids":frame_overlap_only,"fault_active_structural_hops":dict(active_alt_hops),
            "fault_exposed_flow_outcomes":exposed_flow_outcomes,"fault_structural_endpoint_pairs":structural_pairs,
            "pre_fault_cache_evidence":pre_fault_cache_evidence,
            "cost_partition_airtime_s":dict(cost),"effective_parameters":identity.get("protocol_parameters_by_arm",{})}


def evaluate_population(plan, rows):
    """Apply frozen claim gates to the whole population, never select successes."""
    expected = {(s["case_id"],s["arm_id"],s["seed"]):s for s in plan["runs"]}
    actual = {(r["case_id"],r["arm_id"],r["seed"]):r for r in rows}
    if len(actual) != len(rows) or set(actual) != set(expected):
        raise ValueError("diagnostic population differs from complete frozen run keys")
    seeds = plan["matrix"]["seeds"]
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)
    comparisons, control_checks, criteria = [], [], []
    for case in plan["matrix"]["cases"]:
        arms = [a for a in plan["matrix"]["arms"] if a["id"] in case["arms"]]
        focus_arms = [a for a in arms if a["protocol"] == "meshecho-cpr"]
        if len(focus_arms) != 1:
            raise ValueError("formal case requires exactly one declared CPR reference")
        focus = focus_arms[0]
        for arm in arms:
            if arm == focus:
                continue
            component = CONTROL_COMPONENTS.get(arm["protocol"])
            pairs, parameter_differences = [], []
            clean_control, intended_toggle = True, True
            for seed in seeds:
                left = actual[(case["id"],focus["id"],seed)]
                right = actual[(case["id"],arm["id"],seed)]
                identities_match = left["pair_identities"] == right["pair_identities"]
                denominator_match = left["flow_count"] == right["flow_count"]
                if not identities_match or not denominator_match:
                    raise ValueError("comparison exogenous identities or scheduled denominators differ")
                pairs.append({"seed":seed,"reference_run_key":left["run_key"],"comparator_run_key":right["run_key"],
                    "scheduled_denominator":left["flow_count"],"ack_difference":left["ack_pdr"]-right["ack_pdr"],
                    "delivery_difference":left["delivery_pdr"]-right["delivery_pdr"],
                    "airtime_log_ratio":math.log(left["airtime_s"]/right["airtime_s"]) if left["airtime_s"]>0 and right["airtime_s"]>0 else None,
                    "reference_component_events":left[component[1]] if component else None,
                    "control_disabled_component_events":right[component[1]] if component else None})
                if component:
                    lp = left["effective_parameters"].get(focus["protocol"])
                    rp = right["effective_parameters"].get(arm["protocol"])
                    if not isinstance(lp,dict) or not isinstance(rp,dict):
                        clean_control = intended_toggle = False
                        parameter_differences.append({"seed":seed,"field":"missing-resolved-parameters"})
                        continue
                    intended_toggle &= lp.get(component[0]) is True and rp.get(component[0]) is False
                    for field in sorted(set(lp)|set(rp)):
                        if (field in lp)!=(field in rp) or lp.get(field)!=rp.get(field):
                            allowed = field in {"name",component[0]}
                            clean_control &= allowed
                            parameter_differences.append({"seed":seed,"field":field,"reference":lp.get(field),"control":rp.get(field),"allowed":allowed})
            comparisons.append({"case_id":case["id"],"scenario":case["scenario"],"configuration":case["configuration"],
                "reference_arm":focus["id"],"comparator_arm":arm["id"],
                "kind":"component-control" if component else "behavioral-baseline", "paired_seed_count":len(pairs),"pairs":pairs})
            if component:
                ref_events = sum(p["reference_component_events"] for p in pairs)
                disabled_events = sum(p["control_disabled_component_events"] for p in pairs)
                control_checks.append({"case_id":case["id"],"control_arm":arm["id"],"component_parameter":component[0],
                    "event_metric":component[1],"reference_events":ref_events,"reference_zero_exposure":ref_events==0,
                    "reference_zero_exposure_seeds":[p["seed"] for p in pairs if p["reference_component_events"]==0],
                    "control_disabled_component_events":disabled_events,"disabled_activity_is_zero":disabled_events==0,
                    "resolved_noncomponent_parameters_match":bool(clean_control),"intended_true_to_false_toggle":bool(intended_toggle),
                    "parameter_differences":parameter_differences,
                    "eligible_for_component_interpretation":bool(ref_events>0 and disabled_events==0 and clean_control and intended_toggle),
                    "all_pairs_retained":True,"paired_seeds":pairs})
        reference_rows = [actual[(case["id"],focus["id"],seed)] for seed in seeds]
        primary_rows = [r for r in by_case[case["id"]] if r["protocol"] not in CONTROL_COMPONENTS]
        if case["scenario"] == "S1":
            by_seed = [{"seed":r["seed"],"physical_routed_initial_tx":r["source_routed_initial_tx_count"],
                        "accepted_multihop_ack_count":sum(n for h,n in r["accepted_ack_hops"].items() if int(h)>=2),
                        "initial_actions":r["initial_actions"],"accepted_ack_hops":r["accepted_ack_hops"]} for r in reference_rows]
            criteria.append({"criterion":"S1-cached-multihop","case_id":case["id"],"scope":"CPR reference within regime",
                "passed":sum(x["physical_routed_initial_tx"] for x in by_seed)>0 and sum(x["accepted_multihop_ack_count"] for x in by_seed)>0,
                "by_seed":by_seed,"failure_interpretation":"Withhold cached-multihop claim; retain every seed."})
        if case["scenario"] == "S2":
            structural = [{"seed":r["seed"],**pair} for r in reference_rows for pair in r["fault_structural_endpoint_pairs"]]
            maximum_hops = int(case["case"].get("max_hops",6))
            structural_ok = bool(structural) and all(x["hops"] is not None and x["hops"]<=maximum_hops for x in structural)
            attempts = sum(r["fault_physical_intended_tx"] for r in primary_rows)
            routed_intersections = sum(r["fault_initial_carried_path_exposed_flows"] for r in reference_rows)
            criteria.append({"criterion":"S2-cached-route-disruption","case_id":case["id"],
                "scope":"all primary models for intended-edge attempts; CPR reference for initial-route intersection",
                "passed":attempts>0 and routed_intersections>0 and structural_ok,
                "primary_physical_intended_fault_tx":attempts,"cpr_routed_initial_intersecting_flows":routed_intersections,
                "all_endpoint_structural_alternatives_within_hop_budget":structural_ok,"hop_budget":maximum_hops,
                "structural_endpoint_records":structural,
                "reference_by_seed":[{k:r[k] for k in ("seed","fault_enqueued_flows","fault_active_flows","fault_initial_carried_path_exposed_flows","fault_physical_intended_tx","source_repeats","source_recoveries")} for r in reference_rows],
                "failure_interpretation":"Inadequate realized disruption exposure; no seed replacement or filtering."})
        if case["scenario"] == "S3":
            candidates = [c for c in plan["matrix"]["cases"] if c["scenario"]=="S1" and c["configuration"]==case["configuration"]]
            if len(candidates)!=1:
                raise ValueError("S3 requires unique corresponding-regime S1 case")
            s1 = candidates[0]
            count_checks = []
            for row in primary_rows:
                reference = actual[(s1["id"],row["arm_id"],row["seed"])]
                count_checks.append({"arm_id":row["arm_id"],"seed":row["seed"],"S1_flow_count":reference["flow_count"],
                                     "S3_flow_count":row["flow_count"],"increased":row["flow_count"]>reference["flow_count"]})
            contention = sum(r["intended_rx"].get("capture_collision",0)+r["intended_rx"].get("half_duplex",0) for r in primary_rows)
            criteria.append({"criterion":"S3-load-and-contention","case_id":case["id"],
                "scope":"each primary arm/seed against corresponding-regime S1; primary-model intended-hop receiver opportunities",
                "passed":all(x["increased"] for x in count_checks) and contention>0,"flow_count_checks":count_checks,
                "intended_hop_collision_or_half_duplex":contention,
                "failure_interpretation":"Withhold elevated-contention claim; do not infer queue/ledger saturation or omit seeds."})
    expected_comparisons = sum(len(c["arms"])-1 for c in plan["matrix"]["cases"])
    if len(comparisons)!=expected_comparisons or sum(len(c["pairs"]) for c in comparisons)!=expected_comparisons*len(seeds):
        raise ValueError("incomplete comparison inventory")
    return {"rules_are_claim_gates_not_filters":True,"all_run_keys_retained":True,
            "expected_runs":len(expected),"observed_runs":len(actual),
            "expected_comparison_cells":expected_comparisons,"observed_comparison_cells":len(comparisons),
            "paired_seed_records":sum(len(c["pairs"]) for c in comparisons),
            "comparisons":comparisons,"component_exposure_and_identity_checks":control_checks,
            "prospective_scene_criteria":criteria,
            "deadline_response_rows":[{k:r[k] for k in ("run_key","case_id","arm_id","protocol","seed","deadline_s","cutoff_s","ack_pdr","delivery_pdr","airtime_s")}
                                      for r in rows if r["scenario"]=="R-deadline" or r["case_id"]=="S2-matched" and r["protocol"] not in CONTROL_COMPONENTS],
            "deadline_response_limitation":"Deadline/drain change together; no unregistered across-deadline inferential contrast.",
            "unobserved_claims":["Exact ledger peak occupancy", "Calibrated RF/hardware performance", "Cache-TTL-expiry behavior"]}


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="exclusive new JSON output")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root; required when relocating this script")
    args = parser.parse_args()
    ROOT = args.root.resolve()
    plan_path = (args.plan if args.plan.is_absolute() else ROOT / args.plan).resolve()
    output_path = args.out.resolve()
    if output_path.exists():
        raise FileExistsError(output_path)
    plan = json.loads(plan_path.read_text())
    expected_runs = len(plan["runs"])
    assert expected_runs > 0 and expected_runs == plan["matrix"]["budget"]["expected_runs"]
    assert len({s["run_key"] for s in plan["runs"]}) == expected_runs
    attempts = []
    for spec in plan["runs"]:
        root = ROOT / "results/secon2027/runs" / spec["run_key"]
        complete = list(root.glob("attempt-*/completion.json"))
        if len(complete) != 1:
            raise SystemExit(f"Full coverage not yet established for {spec['run_key']}: {len(complete)} completed attempts")
        attempts.append((spec, complete[0].parent))
    # Full frozen-plan audit is allowed only after the simple completeness gate.
    sys.path.insert(0,str(ROOT))
    from tools.secon2027_experiment import audit_plan
    audit = audit_plan(plan_path,ROOT)
    assert audit["status"] == "complete" and len(audit["completed"]) == expected_runs
    rows = [inspect(spec, attempt) for spec,attempt in attempts]
    result = {"schema":"formal-mechanism-inspection-v1","scope":"frozen-formal-population-descriptive-no-confirmatory-inference",
              "plan_sha256":plan["plan_sha256"],"source_snapshot":plan["source_snapshot"],
              "expected_runs":expected_runs,"observed_runs":len(rows),"all_seeds_retained":plan["matrix"]["seeds"],
              "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"audit":audit,"runs":rows,
              "population_review":evaluate_population(plan,rows)}
    with output_path.open("x") as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write("\n")
    print(json.dumps({"completed_runs":len(rows),"output":str(output_path)}))


if __name__ == "__main__":
    main()
