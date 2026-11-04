#!/usr/bin/env python3
"""Read-only S1/S3 primary-CPR exposure review; no simulator or repository imports.

Reads 80 predeclared runs, not the full 760-run audit. Streaming RX inspection
counts designated-hop opportunities only and checks accepted-ACK provenance.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import datetime
import hashlib
import json
import statistics


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_json(path):
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def rows(path, hashes):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for line in stream:
            h.update(line)
            if line.strip():
                yield json.loads(line)
    hashes[path.name] = h.hexdigest()


def hist(values):
    return dict(sorted(Counter(map(str, values)).items()))


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def intended_receiver(tx):
    path, index = tx["path"], tx["path_index"]
    if tx["packet_kind"] == "ACK" and 0 <= index < len(path):
        return path[index]
    if tx["packet_kind"] in {"DATA", "RREP"} and 0 <= index + 1 < len(path):
        return path[index + 1]
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo"))
    parser.add_argument("--out", type=Path, default=Path(__file__).with_suffix(".json"))
    args = parser.parse_args()
    root = args.root.resolve()
    plan_path = root / "results/secon2027/plans/formal-v1.json"
    plan, plan_file_sha = read_json(plan_path)
    contract_path = root / plan["snapshot_path"] / "source" / plan["matrix"]["contract_path"]
    contract_bytes = contract_path.read_bytes()
    contract_sha = hashlib.sha256(contract_bytes).hexdigest()
    cases = ("S1-default", "S1-matched", "S3-default", "S3-matched")
    selected = [run for run in plan["runs"] if run["case_id"] in cases and run["arm"]["protocol"] == "meshecho-cpr"]
    seeds = plan["matrix"]["seeds"]
    issues, checks, reports = [], Counter(), []

    def check(ok, kind, where):
        checks[kind] += 1
        if not ok:
            issues.append({"kind": kind, "where": where})

    check(digest({k: v for k, v in plan.items() if k != "plan_sha256"}) == plan["plan_sha256"], "plan-logical-hash", "plan")
    check(contract_sha == plan["contract_sha256"], "frozen-contract-hash", "contract")
    check(len(selected) == 80 and len({(r["case_id"], r["seed"]) for r in selected}) == 80
          and {(r["case_id"], r["seed"]) for r in selected} == {(c, seed) for c in cases for seed in seeds}, "exact-80-run-scope", "selection")

    for ordinal, spec in enumerate(selected, 1):
        key, seed, cid = spec["run_key"], spec["seed"], spec["case_id"]
        tag = f"{cid}/{seed}"
        attempts = sorted((root / "results/secon2027/runs" / key).glob("attempt-*"))
        completed = [path for path in attempts if (path / "completion.json").is_file()]
        check(len(completed) == 1, "one-completed-attempt", tag)
        if len(completed) != 1:
            continue
        attempt = completed[0]
        completion, completion_sha = read_json(attempt / "completion.json")
        check(completion["run_key"] == key and completion["plan_sha256"] == plan["plan_sha256"]
              and completion["source_snapshot"] == plan["source_snapshot"], "completion-binding", tag)
        ident, ident_sha = read_json(attempt / "evidence.identities.json")
        ident = ident[str(seed)]
        hashes = {"evidence.identities.json": ident_sha}
        flows = list(rows(attempt / "evidence.flows.jsonl", hashes))
        fi = {flow["flow_id"]: flow for flow in flows}
        check(len(flows) == len(fi) == len(ident["application_trace"])
              and set(fi) == {flow["flow_id"] for flow in ident["application_trace"]}, "scheduled-population", tag)
        txs = list(rows(attempt / "evidence.transmissions.jsonl", hashes))
        ti = {tx["tx_id"]: tx for tx in txs}
        requests = list(rows(attempt / "evidence.requests.jsonl", hashes))
        qi = {request["tx_request_id"]: request for request in requests}
        actions = list(rows(attempt / "evidence.actions.jsonl", hashes))
        acks = list(rows(attempt / "evidence.acks.jsonl", hashes))
        accepted = [ack for ack in acks if ack["accepted"]]
        accepted_rx_ids = {ack["ack_rx_attempt_id"] for ack in accepted}
        ack_rx, designated, designated_by_kind = {}, Counter(), Counter()
        rx_count = 0
        for rx in rows(attempt / "evidence.rx_attempts.jsonl", hashes):
            rx_count += 1
            tx = ti.get(rx["tx_id"])
            check(tx is not None, "RX-has-TX", tag)
            if tx is None:
                continue
            if intended_receiver(tx) == rx["receiver"]:
                designated[rx["reason"]] += 1
                designated_by_kind[(tx["packet_kind"], rx["reason"])] += 1
                check(rx["sender"] == tx["sender"] and rx["path"] == tx["path"]
                      and rx["path_index"] == tx["path_index"] and rx["packet_kind"] == tx["packet_kind"], "intended-RX-TX-role-join", tag)
            if rx["rx_attempt_id"] in accepted_rx_ids:
                ack_rx[rx["rx_attempt_id"]] = rx

        stage_counts = {stage: 0 for stage in ("R_INITIAL", "F_INITIAL", "R_REPEAT", "F_RECOVERY")}
        initial_routed_hops, stage_flows = [], defaultdict(set)
        source_stage_examples = {}
        cutoff = spec["case"]["case"]["duration_s"] + spec["case"]["deadline_s"]
        for tx in txs:
            flow = fi[tx["flow_id"]]
            if tx["sender"] != flow["src"] or tx["packet_kind"] not in {"DATA", "FLOOD"}:
                continue
            if tx["repair_index"] is None:
                stage = "R_INITIAL" if tx["packet_kind"] == "DATA" else "F_INITIAL"
            elif tx["packet_kind"] == "DATA" and tx["repair_index"] == 1:
                stage = "R_REPEAT"
            elif tx["packet_kind"] == "FLOOD" and tx["repair_index"] == 2:
                stage = "F_RECOVERY"
            else:
                check(False, "recognized-source-stage", tag)
                continue
            request = qi.get(tx["tx_request_id"], {})
            check(tx["start"] <= cutoff and request.get("status") == "started"
                  and request.get("tx_id") == tx["tx_id"], "physical-source-TX-request-join", tag)
            stage_counts[stage] += 1
            stage_flows[stage].add(tx["flow_id"])
            source_stage_examples.setdefault(stage, {"flow_id": tx["flow_id"], "tx_id": tx["tx_id"], "tx_request_id": tx["tx_request_id"], "start": tx["start"], "path": tx["path"]})
            if stage == "R_INITIAL":
                initial_routed_hops.append(len(tx["path"]) - 1)

        ack_hops, ack_hops_initial = [], defaultdict(list)
        ack_stage = Counter()
        ack_example = None
        for ack in accepted:
            flow = fi[ack["flow_id"]]
            tx, rx = ti.get(ack["ack_tx_id"], {}), ack_rx.get(ack["ack_rx_attempt_id"], {})
            good = (tx.get("packet_kind") == "ACK" and rx.get("decoded") is True
                    and rx.get("tx_id") == ack["ack_tx_id"] and rx.get("receiver") == ack["receiver"] == flow["src"]
                    and tx.get("path") == ack["reverse_path"] and ack["reverse_path"][0] == flow["src"]
                    and ack["reverse_path"][-1] == flow["dst"] and abs(rx.get("end", -1) - ack["accepted_at"]) < 1e-7)
            check(good, "accepted-ACK-physical-provenance", tag)
            hops = len(ack["reverse_path"]) - 1
            ack_hops.append(hops)
            ack_hops_initial[str(flow["initial_action"])].append(hops)
            ack_stage["initial" if ack["repair_index"] is None else "repeat" if ack["repair_index"] == 1 else "recovery" if ack["repair_index"] == 2 else "other"] += 1
            if good and hops >= 2 and ack_example is None:
                ack_example = {"flow_id": ack["flow_id"], "ack_tx_id": ack["ack_tx_id"], "ack_rx_attempt_id": ack["ack_rx_attempt_id"], "accepted_at": ack["accepted_at"], "path": ack["reverse_path"], "hops": hops}

        for name, measured_hash in hashes.items():
            check(completion["files"].get(name) == measured_hash, "selected-input-hash-matches-completion", tag + "/" + name)
        events = Counter(action["event"] for action in actions)
        decisions = Counter((str(action.get("action")), str(action.get("reason"))) for action in actions if action["event"] == "decision")
        source_refusals = sum(action["event"] == "decision" and action.get("reason") == "state-capacity-drop" for action in actions)
        flow_refusals = sum(flow.get("decision_reason") == "state-capacity-drop" for flow in flows)
        check(source_refusals == flow_refusals, "source-capacity-action-flow-agreement", tag)
        waits = [request["queue_wait_s"] for request in requests if request.get("queue_wait_s") is not None]
        statuses = Counter(request["status"] for request in requests)
        no_start = Counter((request["status"], str(request.get("no_start_reason"))) for request in requests if request["status"] != "started")
        cancel_count = events["cpr-cancel"]
        check(cancel_count == sum(action["event"] == "cpr-cancel-check" and action.get("canceled", False) for action in actions), "ACK-cancel-event-check-agreement", tag)
        reports.append({
            "case_id": cid, "scenario": spec["case"]["scenario"], "regime": spec["case"]["configuration"], "arm_id": spec["arm_id"],
            "seed": seed, "run_key": key, "attempt": attempt.relative_to(root).as_posix(), "completion_sha256": completion_sha, "selected_input_sha256": hashes,
            "scheduled_N": len(flows), "initial_action_counts": dict(Counter(str(flow["initial_action"]) for flow in flows)),
            "physical_source_stage_TX": stage_counts, "source_stage_distinct_flows": {stage: len(stage_flows[stage]) for stage in stage_counts},
            "physical_routed_initial_path_hops": hist(initial_routed_hops), "accepted_ACK_hops": hist(ack_hops),
            "accepted_ACK_hops_by_initial_action": {mode: hist(hops) for mode, hops in sorted(ack_hops_initial.items())},
            "accepted_ACK_stage_association": dict(ack_stage), "accepted_ACK_count": len(accepted), "accepted_ACK_at_least_two_hops": sum(hops >= 2 for hops in ack_hops),
            "source_stage_examples": source_stage_examples, "multihop_accepted_ACK_example": ack_example,
            "intended_hop_RX_count": sum(designated.values()), "intended_hop_RX_reasons": {reason: designated[reason] for reason in ("success", "capture_collision", "half_duplex", "prr_fail")},
            "intended_hop_RX_all_reasons": dict(designated), "intended_hop_RX_kind_reason": [{"kind": k, "reason": reason, "count": value} for (k, reason), value in sorted(designated_by_kind.items())],
            "all_listener_RX_count": rx_count, "request_status_counts": {status: statuses[status] for status in ("started", "canceled", "protocol-no-start", "committed_future_start")},
            "request_all_status_counts": dict(statuses), "request_no_start_status_reason": [{"status": status, "reason": reason, "count": count} for (status, reason), count in sorted(no_start.items())],
            "request_queue_wait_s": {"count": len(waits), "positive_count": sum(wait > 1e-9 for wait in waits), "mean": statistics.fmean(waits) if waits else None, "p50": percentile(waits, .5), "p95": percentile(waits, .95), "max": max(waits) if waits else None},
            "source_state_capacity_refusal_count": source_refusals, "protocol_rejection_request_count": statuses["protocol-no-start"],
            "relay_capacity_eviction_count": events["state-eviction"], "relay_capacity_pending_cancel_count": sum(action["event"] == "state-eviction" and bool(action.get("pending_canceled")) for action in actions),
            "ACK_cancel_success_count": cancel_count, "decoded_ACK_cancel_check_count": events["cpr-cancel-check"],
            "decision_action_reason_counts": [{"action": action, "reason": reason, "count": count} for (action, reason), count in sorted(decisions.items())],
            "no_initial_physical_source_TX_flow_count": len(flows) - stage_counts["R_INITIAL"] - stage_counts["F_INITIAL"],
        })
        if ordinal % 10 == 0:
            print(f"Exposure records read: {ordinal}/80", flush=True)

    by_id = {(row["case_id"], row["seed"]): row for row in reports}
    load_comparisons, gates, aggregates = [], {}, {}
    for regime in ("default", "matched"):
        s1 = [by_id[("S1-" + regime, seed)] for seed in seeds]
        s3 = [by_id[("S3-" + regime, seed)] for seed in seeds]
        for seed in seeds:
            low, high = by_id[("S1-" + regime, seed)]["scheduled_N"], by_id[("S3-" + regime, seed)]["scheduled_N"]
            load_comparisons.append({"regime": regime, "seed": seed, "S1_N": low, "S3_N": high, "S3_exceeds_S1": high > low, "ratio": high / low if low else None})
        gates[regime] = {
            "S1_has_physical_routed_initial": sum(row["physical_source_stage_TX"]["R_INITIAL"] for row in s1) > 0,
            "S1_has_accepted_ACK_at_least_two_hops": sum(row["accepted_ACK_at_least_two_hops"] for row in s1) > 0,
            "S3_offered_N_exceeds_S1_for_every_seed": all(by_id[("S3-" + regime, seed)]["scheduled_N"] > by_id[("S1-" + regime, seed)]["scheduled_N"] for seed in seeds),
            "S3_has_intended_hop_collision": sum(row["intended_hop_RX_reasons"]["capture_collision"] for row in s3) > 0,
            "S3_has_intended_hop_half_duplex": sum(row["intended_hop_RX_reasons"]["half_duplex"] for row in s3) > 0,
            "S3_reference_repeat_exposed": sum(row["physical_source_stage_TX"]["R_REPEAT"] for row in s3) > 0,
            "S3_reference_recovery_exposed": sum(row["physical_source_stage_TX"]["F_RECOVERY"] for row in s3) > 0,
            "S3_reference_ACK_cancel_exposed": sum(row["ACK_cancel_success_count"] for row in s3) > 0,
        }
        for scenario, population in (("S1", s1), ("S3", s3)):
            aggregate = {"runs": len(population), "seed_count": len(seeds), "scheduled_N": sum(row["scheduled_N"] for row in population)}
            for field in ("accepted_ACK_count", "accepted_ACK_at_least_two_hops", "source_state_capacity_refusal_count", "protocol_rejection_request_count", "relay_capacity_eviction_count", "relay_capacity_pending_cancel_count", "ACK_cancel_success_count", "decoded_ACK_cancel_check_count", "no_initial_physical_source_TX_flow_count"):
                aggregate[field] = sum(row[field] for row in population)
            for field in ("initial_action_counts", "physical_source_stage_TX", "accepted_ACK_hops", "physical_routed_initial_path_hops", "intended_hop_RX_reasons", "request_status_counts"):
                counter = Counter()
                for row in population:
                    counter.update(row[field])
                aggregate[field] = dict(counter)
            aggregate["equal_seed_mean_queue_wait_s"] = statistics.fmean(row["request_queue_wait_s"]["mean"] for row in population)
            aggregate["equal_seed_mean_queue_wait_p95_s"] = statistics.fmean(row["request_queue_wait_s"]["p95"] for row in population)
            aggregates[scenario + "-" + regime] = aggregate

    output = {
        "status": "passed" if not issues and all(all(v.values()) for v in gates.values()) else "issues-or-unmet-claim-gate",
        "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "execution_root": str(root), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "plan_file_sha256": plan_file_sha, "plan_sha256": plan["plan_sha256"], "source_snapshot": plan["source_snapshot"], "contract_sha256": contract_sha,
        "scope": "Only the 80 S1/S3 primary CPR runs in both regimes, all 20 planned seeds; no full 760-run integrity audit repeated, no simulation or source import.",
        "definitions": {
            "physical_source_stage": "TX sender equals scheduled source. Unmarked DATA is R_INITIAL, unmarked FLOOD is F_INITIAL, DATA marker1 is R_REPEAT, FLOOD marker2 is F_RECOVERY. Each is joined to a started request within the frozen cutoff.",
            "accepted_ACK_hops": "len(reverse_path)-1 for accepted ACK records, joined to the actual decoded ACK RX/TX and scheduled source/destination; distributions retain each seed and initial decision mode.",
            "intended_hop_opportunity": "DATA/RREP path[path_index+1] or ACK path[path_index], matched to receiver. Broadcast/FLOOD listener outcomes are not designated hops. These are correlated receiver opportunities, not independent flows or a unique causal failure attribution.",
            "queue_wait": "All recorded non-null request queue_wait_s; means and linearly interpolated p50/p95 are per run. Aggregate means are equal-seed means, not pooled requests.",
            "source_state_capacity_refusal": "decision action events with reason state-capacity-drop, reconciled to the same reason in initial flow rows; distinct from relay state-eviction.",
            "protocol_rejection": "Request status protocol-no-start; decision action/reason combinations are separately retained and do not all mean deadline infeasibility.",
            "ACK_cancel": "cpr-cancel events reconciled to canceled=true cpr-cancel-check events. Decoded check count includes ineligible checks and is not an eligible-opportunity denominator.",
        },
        "checks": dict(checks), "issues": issues, "claim_gates": gates, "aggregates": aggregates, "load_comparisons": load_comparisons, "runs": reports,
        "limitations": ["Default and matched CPR are reported independently but are not extra independent seeds; never pool them as n=40.", "Passing an exposure gate supports examining the mechanism, not a positive causal benefit or superiority claim.", "Source-state refusal and relay-ledger eviction are different populations; zero eviction does not establish peak occupancy below capacity. Exact peak ledger occupancy is not observed.", "S1/S3 is a two-point offered-load comparison, not a saturation threshold. Zero or adverse rows remain included.", "S2 and its reference component exposure are reviewed separately by the parent; this file does not certify those outcomes or the entire formal batch."]
    }
    args.out.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": output["status"], "runs": len(reports), "issues": len(issues), "claim_gates": gates, "aggregates": aggregates}, indent=2))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
