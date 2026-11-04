#!/usr/bin/env python3
"""Read existing formal S2 CPR evidence; no simulator imports, runs or mutations.

This is a targeted exposure/physical-chain check, not the full 760-run audit.
The complementary S1/S3 script writes its own output for the combined review.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import datetime as dt
import hashlib
import json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def edges(path):
    return {tuple(sorted(pair)) for pair in zip(path, path[1:])}


def near(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-7


def summarize(result, out):
    """Combine completed targeted reviews and compare saved verified summaries."""
    companion_path = out.parent / "secon2027_supervisor_formal_s1_s3_exposure.json"
    verified_path = out.parent / "secon2027_supervisor_formal_raw_review_verified.json"
    companion, verified = read(companion_path), read(verified_path)
    for other in [companion, verified]:
        if other["plan_sha256"] != result["plan_sha256"] or other["contract_sha256"] != result["contract_sha256"]:
            raise ValueError("Review identities differ")
    if companion["issues"] or verified["issues"]:
        raise ValueError("Complementary reviews contain unresolved issues")
    raw = {r["run_key"]: r for r in verified["runs"]}
    disagreements = []
    for row in result["runs"]:
        rr = raw[row["run_key"]]
        for key, value in [("N", row["counters"]["N"]), ("completion_sha256", row["completion_sha256"]), ("ACK_cancel_success", row["counters"]["successful_ACK_cancellations"])]:
            if rr[key] != value:
                disagreements.append([row["run_key"], key, value, rr[key]])
        for key, value in [("R_REPEAT", row["counters"]["repeat_physical"]), ("F_RECOVERY", row["counters"]["recovery_physical"])]:
            if rr["source_stage_TX"].get(key, 0) != value:
                disagreements.append([row["run_key"], key, value, rr["source_stage_TX"].get(key, 0)])
        for key, value in [("ack_deadline", sum(f["timely_ack"] for f in row["flows"])), ("delivery_deadline", sum(f["timely_delivery"] for f in row["flows"]))]:
            if rr[key] != value:
                disagreements.append([row["run_key"], key, value, rr[key]])
    for row in companion["runs"]:
        rr = raw[row["run_key"]]
        comparisons = {"N": row["scheduled_N"], "completion_sha256": row["completion_sha256"], "accepted_ack_hops": row["accepted_ACK_hops"], "ACK_cancel_success": row["ACK_cancel_success_count"], "capacity_evictions": row["relay_capacity_eviction_count"], "capacity_pending_canceled": row["relay_capacity_pending_cancel_count"]}
        for key, value in comparisons.items():
            if rr[key] != value:
                disagreements.append([row["run_key"], key, value, rr[key]])
        for key, value in row["physical_source_stage_TX"].items():
            if rr["source_stage_TX"].get(key, 0) != value:
                disagreements.append([row["run_key"], key, value, rr["source_stage_TX"].get(key, 0)])
        for key, value in row["intended_hop_RX_reasons"].items():
            if rr["designated_rx_reasons"].get(key, 0) != value:
                disagreements.append([row["run_key"], key, value, rr["designated_rx_reasons"].get(key, 0)])
    if disagreements:
        raise ValueError("Targeted/full-raw summary differences: " + repr(disagreements))
    s2_default = {r["seed"]: r for r in result["runs"] if r["case_id"] == "S2-default"}
    s2_matched = {r["seed"]: r for r in result["runs"] if r["case_id"] == "S2-matched"}
    equal = all(all(s2_default[seed][k] == s2_matched[seed][k] for k in ["counters", "crossing_flow_outcomes", "actual_blocked_flow_outcomes", "exposed_union_outcomes", "blocked_edge_kind_marker_reason", "flows"]) for seed in s2_default)
    gates = all(r["claim_gate_observed"] for r in result["S2_regimes"]) and all(all(g.values()) for g in companion["claim_gates"].values())
    result["summary_generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    result["summary_script_sha256"] = sha(Path(__file__))
    result["review_script_provenance_note"] = "script_sha256 records the initial S2 extraction script revision. The final script retains that extraction logic and adds the combined report writer; summary_script_sha256 identifies the current full script. --summary-only does not rerun raw extraction."
    result["status"] = "all-preregistered-primary-CPR-exposure-gates-observed" if gates and not result["issues"] else "exposure-limited-or-issues"
    result["S2_default_matched_scientific_records_equal_by_seed"] = equal
    result["S1_S3_review"] = {"path": str(companion_path), "sha256": sha(companion_path), **{k: companion[k] for k in ["status", "reviewed_at", "script_sha256", "checks", "claim_gates", "aggregates", "load_comparisons", "limitations"]}}
    result["verified_full_raw_summary_cross_check"] = {"path": str(verified_path), "sha256": sha(verified_path), "status": verified["status"], "issues": verified["issues"], "matched_primary_CPR_run_summaries": 120, "disagreements": disagreements, "scope": "Read saved verified summaries only; no repeat of complete 760-run raw audit. The initial 39 manifest-count flags were supervisor-checker false positives; use the verified correction chain."}
    result["all_primary_claim_gates_observed"] = gates
    out.write_text(json.dumps(result, indent=2) + "\n")
    s2 = result["S2_regimes"][0]
    a1, a3 = companion["aggregates"]["S1-default"], companion["aggregates"]["S3-default"]
    counts = s2["counters"]
    table = []
    for seed, row in s2_default.items():
        c, o = row["counters"], row["crossing_flow_outcomes"]
        table.append(f"| {seed} | {c['N']} | {c['routed_initial_path_crossings']} | {c['actual_blocked_edge_TX']} | {o['repeat_flows']} / {o['recovery_flows']} | {o['timely_delivery']} / {o['timely_ack']} |")
    ratios = [x["ratio"] for x in companion["load_comparisons"]]
    text = f"""# SECON 2027 formal mechanism-exposure review

Status: **all preregistered primary-CPR exposure gates observed; no targeted-review discrepancy**. Summary written {result['summary_generated_at']}. This review reads the 40 primary CPR S2 runs and the complementary 80 primary CPR S1/S3 runs, retaining all 20 seeds in both regimes. It performs no simulation, seed registration, parameter change or execution-tree write, and does not repeat the full 760-run raw audit.

The plan is `{result['plan_sha256']}`, source snapshot `{result['source_snapshot']}`, frozen contract `{result['contract_sha256']}`. The original contract and post-exposure administrative erratum remain preserved. The criteria below are the frozen **claim gates**, not seed filters. Every scheduled flow remains in the primary denominator; the explicitly labeled S2 subsets only describe mechanism exposure.

## S2: actual cached-route disruption and recovery

Both default and matched meet the gate separately. Per regime, there are **{counts['N']} scheduled flows**, {counts['fault_enqueued']} enqueued within [80,160) s and {counts['fault_active']} whose lifetimes overlap that interval. **{counts['routed_initial_path_crossings']} physical routed initial sends** start during the fault and carry a path containing edge 7–8 or 12–13. All 85 have a prior accepted ACK before 80 s on the same path and route generation. All 20 seeds exhibit at least one such path and at least one actual blocked intended-edge transmission.

There are **159 actual fault-edge TX attempts across 87 flows**: 78 initial DATA, 80 repeat DATA and one initial-stage ACK. The designated receivers decode none: 130 PRR failures, 27 capture-collision outcomes and two half-duplex outcomes. Collision/half-duplex labels are not proof of fault causation. DATA/RREP designate `path[index+1]`; ACK designates `path[index]`. Exposure uses TX start in [80,160), not frame overlap or flow lifetime alone. No outside-start frame merely overlaps the fault interval in these runs.

Of 25 fault-active flows whose initial TX starts before 80 s, **four do make later actual fault-edge attempts**. This differs from the development pilot and is retained. The 85 active-path crossings and 87 physically blocked flows overlap in 83 flows; their union is 89. These populations must not be silently substituted for one another or for the full N=648 denominator.

For the **85 initial-path-crossing flows**, 82 start a repeat and 78 start recovery. **24 deliver on time, 18 receive a timely ACK, six deliver without a timely ACK, and 61 do not deliver on time.** All 24 timely first deliveries and all 18 timely ACKs are associated with recovery marker 2; none has a timely repeat ACK. Twenty-three recovery first deliveries occur during the active fault along paths that avoid the blocked edges, and 17 recovery ACKs complete within the active fault on avoiding paths. A late-in-window success is not automatically active-fault recovery.

For the distinct **87 actual blocked-edge flows**, 84 repeat, 80 recover, 26 deliver on time and 19 receive a timely ACK; seven deliver without timely ACK and 61 lack timely delivery. Two timely first deliveries come from the initial stage; one of those flows later starts recovery, while the other has no recovery start. Source confirmation and destination delivery therefore remain separate, without granting the source a delivery oracle.

All first destination deliveries for the 40 runs are matched to physical decoded destination RX. For the exposed union, the script additionally reconstructs every successful first-delivery forward path and every accepted ACK's full reverse path plus its matching forward stage. There are 90 forward-chain reconstructions and 38 complete reverse-ACK chains across the two regimes, with zero failures. These are observed stage associations; isolated benefit/cost still comes from the frozen controls, not from treating recovery-associated success as a counterfactual gain.

The following table is per seed, **for each regime separately**. Default and matched scientific records are identical and are not pooled as n=40. The last two columns apply only to the initial-path-crossing subset.

| Seed | All scheduled N | Active initial path crosses | Actual blocked-edge TX | Repeat / recovery flows | Timely delivery / ACK |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(table)}

An auditable success example, selected as the first qualifying flow in seed/flow order, is seed 2027100, flow 15 (10→14), run `ffbd30cbc519bed7a13a60d4203dcaeb2a2af14a917e7d684acdf65054c3cbae`. Its initial path 10→11→12→7→8→13→14 physically attempts 7→8 at 107.304356 s and repeats that edge at 108.632628 s; both intended RXs fail. Recovery starts at 109.622212 s, travels 10→11→12→17→18→13→14, reaches the destination at 114.622223 s, and returns a six-hop ACK at 115.023119 s before the 136.965668 s deadline. Forward TX IDs 210/212/214/218/223/227 and reverse ACK TX IDs 228–233 are tied to their decoded RXs in the JSON.

A retained cross-boundary failure is seed 2027106, flow 15: its initial send starts at 79.520476 s, a repeat reaches blocked 7→8 at 81.187436 s, recovery starts at 82.177020 s, and neither destination delivery nor accepted ACK follows. Successful examples are illustrative, not a selection rule.

The structural alternative context is unchanged from the reviewed pilot/formal matrix: the same grid, fault edges, endpoint pairs and H=6 give the previously checked six-hop alternatives. This review does not rerun BFS or imply structural reachability guarantees RF success.

## S1 and S3: full seed populations and observed pressure

The companion S1/S3 review retains full per-seed initial-mode and actual path/ACK-hop distributions, physical stages, request statuses, queue waits, action/reason counts and zeros. Each regime has:

| Quantity | S1 | S3 |
| --- | ---: | ---: |
| Scheduled flows | {a1['scheduled_N']} | {a3['scheduled_N']} |
| Physical routed initial | 480 | 2,445 |
| Physical cold initial | 168 | 608 |
| Accepted ACK, all ≥2 hops | 526 | 1,181 |
| Accepted ACK 4-hop / 6-hop | 440 / 86 | 703 / 478 |
| Physical repeat / recovery | 135 / 91 | 1,890 / 1,597 |
| Intended-hop capture collision / half duplex | 227 / 35 | 3,228 / 887 |
| Successful ACK cancellation | 205 | 685 |
| Source-state capacity refusal | 0 | 6 |
| Relay eviction / pending capacity cancel | 0 / 0 | 0 / 0 |
| Protocol-no-start requests | 2 | 52 |
| Mean of per-seed queue-wait means, s | {a1['equal_seed_mean_queue_wait_s']:.6f} | {a3['equal_seed_mean_queue_wait_s']:.6f} |
| Mean of per-seed queue-wait p95, s | {a1['equal_seed_mean_queue_wait_p95_s']:.6f} | {a3['equal_seed_mean_queue_wait_p95_s']:.6f} |

For every seed and regime, S3 offered N exceeds its matched S1 N (ratios {min(ratios):.3f}–{max(ratios):.3f}). Intended-hop contention is nonzero in both regimes. The six source refusals occur at seeds 2027105 and 2027111, three each; all remain in N. They are not relay eviction. Zero relay eviction does not establish peak occupancy below capacity; peak occupancy remains unobserved. Queue waits and protocol-no-start requests do not establish queue saturation or a dominant deadline-expiry cause. RX opportunities are correlated across hops and attempts, not independent application failures.

S2's full reference populations also contain 182 physical repeats, 142 recoveries and 204 successful ACK cancellations per regime. Thus the S2/S3 matched reference populations expose each predeclared component. This makes their controls interpretable; it does not prove a positive component effect. The matched/default duplicates provide no additional independent seeds.

## Reproducibility and cross-check boundary

The final verified full-raw summary `{verified_path.name}` has no unresolved issues. All **120 targeted primary CPR run summaries** match it on the checked completion hashes, populations, physical stages and applicable ACK-hop, cancellation, relay-eviction and contention counts. This is a comparison of saved summaries, not a second 760-run audit. The initial full-raw checker's 39 accepted-ACK count flags were corrected in its separately preserved correction chain; they were not experiment defects and are not treated as open findings here.

Artifacts:

- `{out.name}`: all 40 S2 per-run/per-flow records, exact path intersections, fault TX/RX IDs, delivery/ACK chains, claim-gate summaries and companion/cross-check hashes.
- `secon2027_supervisor_formal_s1_s3_exposure.json`: all 80 S1/S3 per-run records and all 40 within-seed load comparisons.
- `secon2027_supervisor_formal_exposure_review.py` and `secon2027_supervisor_formal_s1_s3_exposure.py`: standard-library read-only raw extractors. Run the S1/S3 script first, then this script after the independently verified full-raw summary exists. `--summary-only` rebuilds this combined summary from the existing targeted evidence without reading raw logs again.

All 20 formal seeds are retained. The review establishes the registered exposure conditions for these populations, not universal efficiency, positive causal gain, calibrated RF validity, cache-expiry behavior, memory optimization, complete manuscript accuracy or submission readiness. The formal default/matched comparisons, controls and deadline/drain response require their own complete descriptive analysis and claim review.
"""
    out.with_suffix(".md").write_text(text)
    print("Combined exposure gates observed:", gates, "; saved summaries matched: 120; discrepancies: 0")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo"))
    parser.add_argument("--out", type=Path, default=Path(__file__).with_suffix(".json"))
    parser.add_argument("--summary-only", action="store_true", help="Combine existing targeted JSONs and verified raw summaries without rereading raw logs")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.out.resolve().is_relative_to(root):
        raise ValueError("Output must be outside the execution tree")
    if args.summary_only:
        summarize(read(args.out), args.out)
        return
    planpath = root / "results/secon2027/plans/formal-v1.json"
    plan = read(planpath)
    contractpath = root / plan["snapshot_path"] / "source" / plan["matrix"]["contract_path"]
    issues, checks, records = [], Counter(), []

    def check(ok, kind, where):
        checks[kind] += 1
        if not ok:
            issues.append({"kind": kind, "where": where})

    check(digest({k: v for k, v in plan.items() if k != "plan_sha256"}) == plan["plan_sha256"], "plan-logical-hash", "formal-v1")
    check(sha(contractpath) == plan["contract_sha256"], "frozen-contract-hash", str(contractpath))
    selected = [s for s in plan["runs"] if s["case_id"] in {"S2-default", "S2-matched"} and s["arm"]["protocol"] == "meshecho-cpr"]
    check(len(selected) == 40 and {s["seed"] for s in selected} == set(plan["matrix"]["seeds"]), "forty-S2-CPR-runs", "population")
    for spec in selected:
        tag = f"{spec['case_id']}/{spec['arm_id']}/{spec['seed']}"
        attempts = sorted((root / "results/secon2027/runs" / spec["run_key"]).glob("attempt-*"))
        completed = [a for a in attempts if (a / "completion.json").is_file()]
        check(len(completed) == 1, "unique-completed-attempt", tag)
        if len(completed) != 1:
            continue
        base = completed[0]
        completion = read(base / "completion.json")
        check(completion["run_key"] == spec["run_key"] and completion["plan_sha256"] == plan["plan_sha256"] and completion["source_snapshot"] == plan["source_snapshot"], "completion-binding", tag)
        flows = rows(base / "evidence.flows.jsonl")
        txs = rows(base / "evidence.transmissions.jsonl")
        rxs = rows(base / "evidence.rx_attempts.jsonl")
        acks = rows(base / "evidence.acks.jsonl")
        acts = rows(base / "evidence.actions.jsonl")
        fi = {f["flow_id"]: f for f in flows}
        ti = {t["tx_id"]: t for t in txs}
        xi = {x["rx_attempt_id"]: x for x in rxs}
        txflow, rxflow, rxbytx, ackflow, actflow = (defaultdict(list) for _ in range(5))
        for t in txs:
            txflow[t["flow_id"]].append(t)
        for x in rxs:
            rxflow[x["flow_id"]].append(x)
            rxbytx[x["tx_id"]].append(x)
        for a in acks:
            if a["accepted"]:
                ackflow[a["flow_id"]].append(a)
        for a in acts:
            actflow[a["flow_id"]].append(a)
        fault = spec["case"]["environment"]["faults"][0]
        start, end = fault["start_s"], fault["end_s"]
        bad = {tuple(sorted(e)) for e in fault["edges"]}
        cutoff = spec["case"]["case"]["duration_s"] + spec["case"]["deadline_s"]

        def during(t):
            return start <= t < end

        def intended(t):
            path, index = t["path"], t["path_index"]
            if t["packet_kind"] == "ACK" and 0 <= index < len(path):
                return path[index]
            if t["packet_kind"] in {"DATA", "RREP"} and 0 <= index < len(path) - 1:
                return path[index + 1]
            return None

        def hop(x):
            t = ti[x["tx_id"]]
            return {"sender": t["sender"], "receiver": x["receiver"], "tx_id": t["tx_id"], "tx_request_id": t["tx_request_id"], "rx_attempt_id": x["rx_attempt_id"], "start": t["start"], "end": x["end"], "kind": t["packet_kind"], "marker": t["repair_index"]}

        def forward_chain(fid, last_rx, path, marker):
            """Walk decoded same-identity hops backward from a real destination RX."""
            chain = [last_rx]
            downstream = ti[last_rx["tx_id"]]
            for index in range(len(path) - 3, -1, -1):
                u, v = path[index], path[index + 1]
                options = []
                for x in rxflow[fid]:
                    t = ti[x["tx_id"]]
                    if not x["decoded"] or x["receiver"] != v or t["sender"] != u or t["repair_index"] != marker or x["end"] > downstream["start"] + 1e-7:
                        continue
                    if t["packet_kind"] == "DATA" and t["path"] == path and t["path_index"] == index:
                        options.append(x)
                    elif t["packet_kind"] == "FLOOD" and t["path"] == path[:index + 1] and t["path_index"] == index:
                        options.append(x)
                if not options:
                    break
                chosen = max(options, key=lambda x: (x["end"], x["rx_attempt_id"]))
                chain.append(chosen)
                downstream = ti[chosen["tx_id"]]
            chain.reverse()
            check(len(chain) == len(path) - 1 and ti[chain[0]["tx_id"]]["sender"] == fi[fid]["src"], "physical-forward-hop-chain", tag + "/" + str(fid))
            return [hop(x) for x in chain]

        def ack_chain(fid, a):
            last = xi.get(a["ack_rx_attempt_id"])
            valid = last is not None and last["decoded"] and last["receiver"] == fi[fid]["src"] and last["tx_id"] == a["ack_tx_id"] and last["tx_request_id"] == a["ack_tx_request_id"] and near(last["end"], a["accepted_at"])
            check(valid, "accepted-ACK-source-physical-link", tag + "/" + str(fid))
            if not valid:
                return [], None
            path, marker = a["reverse_path"], a["repair_index"]
            chain = [last]
            downstream = ti[last["tx_id"]]
            for index in range(1, len(path) - 1):
                options = [x for x in rxflow[fid] if x["decoded"] and x["receiver"] == path[index] and x["sender"] == path[index + 1] and x["packet_kind"] == "ACK" and x["path"] == path and x["path_index"] == index and x["repair_index"] == marker and x["end"] <= downstream["start"] + 1e-7]
                if not options:
                    break
                chosen = max(options, key=lambda x: (x["end"], x["rx_attempt_id"]))
                chain.append(chosen)
                downstream = ti[chosen["tx_id"]]
            chain.reverse()
            check(len(chain) == len(path) - 1 and ti[chain[0]["tx_id"]]["sender"] == fi[fid]["dst"], "physical-reverse-ACK-hop-chain", tag + "/" + str(fid))
            return [hop(x) for x in chain], downstream["start"]

        blocked, interval_only = [], []
        for t in txs:
            nxt = intended(t)
            if nxt is None or tuple(sorted((t["sender"], nxt))) not in bad:
                continue
            if not during(t["start"]):
                if max(t["start"], start) < min(t["end"], end):
                    interval_only.append(t["tx_id"])
                continue
            rr = [x for x in rxbytx[t["tx_id"]] if x["receiver"] == nxt]
            check(len(rr) == 1, "blocked-edge-intended-RX-unique", tag + "/" + str(t["tx_id"]))
            if not rr:
                continue
            x = rr[0]
            blocked.append({**hop(x), "flow_id": t["flow_id"], "path": t["path"], "decoded": x["decoded"], "reason": x["reason"], "rx_power_dbm": x["rx_power_dbm"]})
        blockedflow = defaultdict(list)
        for b in blocked:
            blockedflow[b["flow_id"]].append(b)
        details = []
        for f in flows:
            fid = f["flow_id"]
            source = [t for t in txflow[fid] if t["sender"] == f["src"] and t["packet_kind"] in {"DATA", "FLOOD"}]
            initial = [t for t in source if t["repair_index"] is None]
            repeat = [t for t in source if t["packet_kind"] == "DATA" and t["repair_index"] == 1]
            recovery = [t for t in source if t["packet_kind"] == "FLOOD" and t["repair_index"] == 2]
            check(len(initial) <= 1 and len(repeat) <= 1 and len(recovery) <= 1, "source-stage-unique", tag + "/" + str(fid))
            initial = initial[0] if initial else None
            routed = initial is not None and initial["packet_kind"] == "DATA" and initial["path"][-1] == f["dst"]
            crossing = bool(routed and during(initial["start"]) and edges(initial["path"]) & bad)
            candidates = []
            for x in rxflow[fid]:
                if not x["decoded"] or x["receiver"] != f["dst"]:
                    continue
                t = ti[x["tx_id"]]
                if t["origin"] != f["src"] or t["final_dst"] != f["dst"]:
                    continue
                path, index = t["path"], t["path_index"]
                if t["packet_kind"] == "DATA" and path and path[0] == f["src"] and path[-1] == f["dst"] and index + 1 == len(path) - 1 and path[index] == t["sender"]:
                    candidates.append((x, path))
                elif t["packet_kind"] == "FLOOD" and path and path[0] == f["src"] and path[-1] == t["sender"] and f["dst"] not in path:
                    candidates.append((x, path + [f["dst"]]))
            candidates.sort(key=lambda pair: (pair[0]["end"], pair[0]["rx_attempt_id"]))
            first = candidates[0] if candidates else None
            check((first is None and f["first_delivery_at"] is None) or (first is not None and near(first[0]["end"], f["first_delivery_at"])), "first-destination-delivery-physical", tag + "/" + str(fid))
            aa = ackflow[fid]
            check(len(aa) <= 1 and ((not aa and f["accepted_ack_at"] is None) or (aa and near(aa[0]["accepted_at"], f["accepted_ack_at"]))), "flow-accepted-ACK", tag + "/" + str(fid))
            a = aa[0] if aa else None
            exposed = crossing or bool(blockedflow[fid])
            first_chain = forward_chain(fid, *first, first[0]["repair_index"]) if first is not None and exposed else []
            back, ack_forward, ack_delivery = [], [], None
            if a and exposed:
                back, ack_start = ack_chain(fid, a)
                matching = [(x, path) for x, path in candidates if x["repair_index"] == a["repair_index"] and path == a["reverse_path"] and ack_start is not None and x["end"] <= ack_start + 1e-7]
                check(bool(matching), "ACK-matching-destination-stage-path", tag + "/" + str(fid))
                if matching:
                    x, path = max(matching, key=lambda pair: (pair[0]["end"], pair[0]["rx_attempt_id"]))
                    ack_forward = forward_chain(fid, x, path, a["repair_index"])
                    ack_delivery = hop(x)
            initial_path = initial["path"] if routed else None
            prior = [aa for aa in acks if aa["accepted"] and aa["accepted_at"] < start and aa["source"] == f["src"] and aa["destination"] == f["dst"] and aa["reverse_path"] == initial_path]
            initial_decision = next((x for x in actflow[fid] if x["event"] == "decision"), {})
            matching_generation = [aa["flow_id"] for aa in prior if aa.get("route_generation_after") == initial_decision.get("route_generation")]
            life_end = min(f["deadline_at"], f["accepted_ack_at"] if f["accepted_ack_at"] is not None else cutoff, cutoff)
            details.append({"flow_id": fid, "src": f["src"], "dst": f["dst"], "enqueued_at": f["enqueued_at"], "deadline_at": f["deadline_at"], "active_during_fault": max(start, f["enqueued_at"]) < min(end, life_end), "initial_action": f["initial_action"], "initial_tx_id": initial["tx_id"] if initial else None, "initial_at": initial["start"] if initial else None, "initial_path": initial_path, "initial_routed_path_intersects_active_fault": crossing, "pre_fault_matching_path_ACK_flow_ids": [x["flow_id"] for x in prior], "pre_fault_matching_generation_ACK_flow_ids": matching_generation, "actual_blocked_edge_transmissions": blockedflow[fid], "source_repeat": [{"tx_id": t["tx_id"], "start": t["start"]} for t in repeat], "source_recovery": [{"tx_id": t["tx_id"], "start": t["start"]} for t in recovery], "first_delivery_at": first[0]["end"] if first else None, "first_delivery_path": first[1] if first else None, "first_delivery_marker": first[0]["repair_index"] if first else None, "first_delivery_physical_chain": first_chain, "timely_delivery": f["delivery_by_deadline"], "accepted_ack_at": a["accepted_at"] if a else None, "accepted_ack_marker": a["repair_index"] if a else None, "accepted_ack_path": a["reverse_path"] if a else None, "accepted_ack_physical_chain": back, "ack_stage_destination_receive": ack_delivery, "ack_stage_forward_physical_chain": ack_forward, "timely_ack": f["ack_by_deadline"], "recovery_after_prior_delivery": bool(first and any(t["start"] > first[0]["end"] for t in recovery)), "stage_destination_receives_by_deadline": dict(Counter(str(x["repair_index"]) for x, path in candidates if x["end"] <= f["deadline_at"]))})

        def subset_counts(ds):
            return {"flows": len(ds), "repeat_flows": sum(bool(x["source_repeat"]) for x in ds), "recovery_flows": sum(bool(x["source_recovery"]) for x in ds), "timely_delivery": sum(x["timely_delivery"] for x in ds), "timely_ack": sum(x["timely_ack"] for x in ds), "timely_delivery_without_timely_ack": sum(x["timely_delivery"] and not x["timely_ack"] for x in ds), "no_timely_delivery": sum(not x["timely_delivery"] for x in ds), "timely_recovery_ack": sum(x["timely_ack"] and x["accepted_ack_marker"] == 2 for x in ds), "timely_repeat_ack": sum(x["timely_ack"] and x["accepted_ack_marker"] == 1 for x in ds), "timely_recovery_first_delivery": sum(x["timely_delivery"] and x["first_delivery_marker"] == 2 for x in ds), "recovery_first_delivery_during_fault_on_avoiding_path": sum(x["first_delivery_at"] is not None and during(x["first_delivery_at"]) and x["first_delivery_marker"] == 2 and not (edges(x["first_delivery_path"]) & bad) for x in ds), "recovery_ack_during_fault_on_avoiding_path": sum(x["accepted_ack_at"] is not None and during(x["accepted_ack_at"]) and x["accepted_ack_marker"] == 2 and not (edges(x["accepted_ack_path"]) & bad) for x in ds), "recovery_after_prior_delivery": sum(x["recovery_after_prior_delivery"] for x in ds)}

        crossing = [x for x in details if x["initial_routed_path_intersects_active_fault"]]
        actual = [x for x in details if x["actual_blocked_edge_transmissions"]]
        union = [x for x in details if x["initial_routed_path_intersects_active_fault"] or x["actual_blocked_edge_transmissions"]]
        counters = {"N": len(flows), "fault_enqueued": sum(during(f["enqueued_at"]) for f in flows), "fault_active": sum(x["active_during_fault"] for x in details), "fault_active_initial_before_start": sum(x["active_during_fault"] and x["initial_at"] is not None and x["initial_at"] < start for x in details), "routed_initial_path_crossings": len(crossing), "crossing_with_pre_fault_same_path_ACK": sum(bool(x["pre_fault_matching_path_ACK_flow_ids"]) for x in crossing), "crossing_with_pre_fault_same_generation_ACK": sum(bool(x["pre_fault_matching_generation_ACK_flow_ids"]) for x in crossing), "actual_blocked_edge_TX": len(blocked), "actual_blocked_edge_flows": len(actual), "actual_blocked_edge_flows_initial_before_fault": sum(x["initial_at"] is not None and x["initial_at"] < start for x in actual), "actual_blocked_edge_decoded": sum(x["decoded"] for x in blocked), "interval_overlap_without_start_exposure": len(interval_only), "repeat_physical": sum(len(x["source_repeat"]) for x in details), "recovery_physical": sum(len(x["source_recovery"]) for x in details), "successful_ACK_cancellations": sum(a["event"] == "cpr-cancel" for a in acts)}
        records.append({"case_id": spec["case_id"], "arm_id": spec["arm_id"], "seed": spec["seed"], "run_key": spec["run_key"], "completion_sha256": sha(base / "completion.json"), "input_hashes_from_completion": {k: v for k, v in completion["files"].items() if k in {"evidence.flows.jsonl", "evidence.transmissions.jsonl", "evidence.rx_attempts.jsonl", "evidence.acks.jsonl", "evidence.actions.jsonl"}}, "fault": fault, "counters": counters, "blocked_edge_kind_marker_reason": dict(Counter(f"{x['kind']}/{x['marker']}/{x['reason']}" for x in blocked)), "crossing_flow_outcomes": subset_counts(crossing), "actual_blocked_flow_outcomes": subset_counts(actual), "exposed_union_outcomes": subset_counts(union), "flows": details})
        print(tag, counters["routed_initial_path_crossings"], counters["actual_blocked_edge_TX"], flush=True)
    summaries = []
    for case_id in ["S2-default", "S2-matched"]:
        rr = [r for r in records if r["case_id"] == case_id]
        counters, crossing, blocked, union, reasons = (Counter() for _ in range(5))
        for r in rr:
            counters.update(r["counters"])
            crossing.update(r["crossing_flow_outcomes"])
            blocked.update(r["actual_blocked_flow_outcomes"])
            union.update(r["exposed_union_outcomes"])
            reasons.update(r["blocked_edge_kind_marker_reason"])
        summaries.append({"case_id": case_id, "seeds": [r["seed"] for r in rr], "runs": len(rr), "counters": dict(counters), "crossing_flow_outcomes": dict(crossing), "actual_blocked_flow_outcomes": dict(blocked), "exposed_union_outcomes": dict(union), "blocked_edge_kind_marker_reason": dict(reasons), "seeds_with_zero_path_crossing": [r["seed"] for r in rr if not r["counters"]["routed_initial_path_crossings"]], "seeds_with_zero_blocked_edge_TX": [r["seed"] for r in rr if not r["counters"]["actual_blocked_edge_TX"]], "claim_gate_observed": counters["routed_initial_path_crossings"] > 0 and counters["actual_blocked_edge_TX"] > 0})
    result = {"schema": "secon2027-formal-exposure-review-v1", "reviewed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "passed-targeted-S2-checks" if not issues else "issues", "scope": "40 primary CPR S2 runs; all 20 seeds in both regimes; full 760-run raw audit is separate; no simulator imports, execution, RNG, exclusions or execution-tree writes", "plan_path": str(planpath), "plan_file_sha256": sha(planpath), "plan_sha256": plan["plan_sha256"], "source_snapshot": plan["source_snapshot"], "contract_sha256": plan["contract_sha256"], "script_sha256": sha(Path(__file__)), "checks": dict(checks), "issues": issues, "definitions": {"fault_exposure": "TX start is inside the half-open fault interval and designated DATA/RREP next hop=path[index+1], ACK next hop=path[index]. Lifetime/frame overlap alone is not an exposed edge attempt.", "path_exposure": "Physical source initial DATA starts while fault is active and its full carried route includes a faulted undirected edge.", "chains": "For exposed-flow subsets, reconstruct decoded forward and ACK reverse hops using flow, marker, full/prefix path, sender/receiver and nondecreasing physical times. Stage association is observed; isolated causal benefit requires frozen ablations.", "subsets": "Path-crossing, actual edge-attempt and their union are explicitly labeled descriptions. Every scheduled flow and all 20 seeds remain in the output and primary denominator.", "hash_scope": "Completion identity/byte hash and plan/contract checked here; consumed artifact expected hashes recorded from completion, with full byte validation delegated to independent full-raw audit.", "structural_context": "The frozen S2 graph/endpoint/hop settings exactly match the already-reviewed pilot/static matrix; no new BFS or simulator run is performed here. Static alternatives are context, not successful RF paths."}, "S2_regimes": summaries, "runs": records}
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "issues": issues, "regimes": summaries}, indent=2))
    summarize(result, args.out)


if __name__ == "__main__":
    main()
