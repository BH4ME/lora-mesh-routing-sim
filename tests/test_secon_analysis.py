"""Synthetic statistical and bookkeeping checks; never run a simulation."""
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import analyze_secon2027 as analysis


def resolved_parameters(protocol):
    parameters = dict(name=protocol, app_deadline_s=30., fixed_guard_s=15., route_ttl_s=600.,
                      cancel_on_ack=True, enable_repeat=True, enable_recovery=True,
                      relay_ledger_enabled=True, relay_capacity=8, evict_pending_on_capacity=True)
    if protocol in analysis.ABLATION_TOGGLES:
        parameters[analysis.ABLATION_TOGGLES[protocol]] = False
    return parameters


def fixture():
    flows = [
        dict(flow_id=1, src=0, dst=2, enqueued_at=0., deadline_at=10., accepted_ack_at=3.,
             first_delivery_at=2., ack_by_deadline=True, delivery_by_deadline=True, initial_action="R_INITIAL"),
        dict(flow_id=2, src=0, dst=2, enqueued_at=0., deadline_at=10., accepted_ack_at=None,
             first_delivery_at=9., ack_by_deadline=False, delivery_by_deadline=True, initial_action="R_INITIAL"),
        dict(flow_id=3, src=0, dst=2, enqueued_at=0., deadline_at=10., accepted_ack_at=None,
             first_delivery_at=None, ack_by_deadline=False, delivery_by_deadline=False, initial_action="F_INITIAL"),
    ]
    txs = [
        dict(tx_id=1, flow_id=1, sender=0, packet_kind="DATA", start=0., end=1., toa_s=1., path=[0,1,2], path_index=0, repair_index=None),
        dict(tx_id=2, flow_id=1, sender=2, packet_kind="ACK", start=2., end=3., toa_s=1., path=[0,1,2], path_index=1, repair_index=None),
        dict(tx_id=3, flow_id=2, sender=0, packet_kind="DATA", start=4., end=5., toa_s=1., path=[0,1,2], path_index=0, repair_index=1),
        dict(tx_id=4, flow_id=2, sender=0, packet_kind="FLOOD", start=8., end=10., toa_s=2., path=[0], path_index=0, repair_index=2),
    ]
    actions = [dict(event="cpr-cancel-check", canceled=False), dict(event="cpr-cancel-check", canceled=True),
               dict(event="cpr-cancel"), dict(event="state-eviction", reason="capacity", pending_canceled=True),
               dict(event="repeat-request"), dict(event="recovery-request")]
    requests = [dict(status="started", queue_wait_s=0.) for _ in range(4)] + [dict(status="canceled", queue_wait_s=None)]
    acks = [dict(flow_id=1, accepted=True, accepted_at=3., reverse_path=[0,1,2], rejection_reason=None)]
    rx = [dict(tx_id=1, receiver=1, reason="prr_fail", decoded=False),
          dict(tx_id=2, receiver=1, reason="success", decoded=True)]
    raw = dict(protocol="meshecho-cpr", drain_until_s=10., tx_ledger_airtime_s=5., started_request_count=4,
               ack_pdr_deadline=1/3, delivery_pdr_deadline=2/3, route_cache_hits=2, route_cache_misses=1,
               # Deliberately wrong legacy reserved-start aliases must not leak into analysis.
               total_airtime_s=9999., tx_count=999, legacy_reserved_total_airtime_s=9999.)
    env = dict(neighbor_edges=[[0,1],[1,2],[0,3],[3,4],[4,2]],
               faults=[dict(start_s=0., end_s=6., attenuation_db=80., edges=[[1,2]])])
    return dict(raw=raw, flows=flows, transmissions=txs, actions=actions, requests=requests,
                acks=acks, rx_attempts=rx, identity={"common_environment":env})


class TestSeedStatistics(unittest.TestCase):
    def test_exact_constant_paired_gain_and_ratio(self):
        result, pairs = analysis.paired_effect({1:.7,2:.8,3:.9}, {1:.5,2:.6,3:.7}, transform="difference")
        self.assertAlmostEqual(result["mean"], .2)
        self.assertAlmostEqual(result["ci_low"], .2)
        self.assertAlmostEqual(result["ci_high"], .2)
        self.assertTrue(result["small_sample_unstable"])
        result, _ = analysis.paired_effect({1:2.,2:4.,3:8.}, {1:1.,2:2.,3:4.}, transform="log_ratio")
        self.assertAlmostEqual(result["mean"], math.log(2))
        self.assertAlmostEqual(result["ratio_ci_low"], 2.)
        self.assertEqual([p["seed"] for p in pairs], [1,2,3])

    def test_no_silent_undefined_or_unpaired_seed_removal(self):
        result, pairs = analysis.paired_effect({1:0.,2:4.}, {1:2.,2:2.}, transform="log_ratio")
        self.assertIsNone(result["mean"])
        self.assertIsNone(result["ci_low"])
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["undefined_n"], 1)
        self.assertIsNotNone(pairs[0]["undefined_reason"])
        with self.assertRaisesRegex(ValueError, "populations differ"):
            analysis.paired_effect({1:.5,2:.8}, {1:.3}, transform="difference")
        result = analysis.bootstrap_mean([1.,None,3.])
        self.assertIsNone(result["mean"])
        self.assertEqual(result["undefined_n"], 1)

    def test_resampling_reproducible_and_one_seed_has_no_ci(self):
        a = analysis.bootstrap_mean([.1,.4,.8,.9], seed=999)
        b = analysis.bootstrap_mean([.1,.4,.8,.9], seed=999)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a["mean"], .55)
        one = analysis.bootstrap_mean([.5])
        self.assertEqual(one["mean"], .5)
        self.assertIsNone(one["ci_low"])
        self.assertIsNone(analysis.percentile([], .5))
        self.assertEqual(analysis.percentile([1.,3.], .5), 2.)


class TestPhysicalAnalysis(unittest.TestCase):
    def test_independent_physical_count_cost_cancellation_and_paths(self):
        result = analysis.summarize_run(**fixture())
        m = result["metrics"]
        self.assertEqual(m["started_request_count"], 4)
        self.assertEqual(m["tx_ledger_airtime_s"], 5.)
        self.assertEqual(m["airtime_per_timely_delivery_s"], 2.5)
        self.assertEqual(m["source_repeat_tx_count"], 1)
        self.assertEqual(m["source_recovery_tx_count"], 1)
        self.assertEqual(m["ack_cancel_check_count"], 2)
        self.assertEqual(m["ack_cancel_success_per_decoded_ack_check"], .5)
        self.assertEqual(m["capacity_canceled_count"], 1)
        self.assertEqual(m["canceled_request_count"], 1)
        self.assertEqual(m["accepted_ack_hops_mean"], 2.)
        self.assertEqual(m["timely_ack_one_hop_fraction"], 0.)
        self.assertEqual(m["delivery_without_timely_ack_flows"], 1)
        self.assertEqual(m["initial_routed_flow_count"], 2)
        self.assertEqual(m["initial_flood_flow_count"], 1)
        self.assertEqual(m["source_path_fault_exposed_flows"], 2)
        self.assertEqual(m["fault_exposed_with_budget_feasible_alternative_flows"], 2)
        self.assertEqual(sum(c["airtime_s"] for c in result["costs"]), 5.)
        costs = {(c["packet_kind"],c["stage"]):c["airtime_s"] for c in result["costs"]}
        self.assertEqual(costs[("FLOOD","recovery")], 2.)
        self.assertEqual(costs[("ACK","initial")], 1.)
        self.assertEqual(result["rx"][0]["packet_kind"], "ACK")

    def test_exported_initial_actions_match_started_source_events(self):
        data = fixture()
        # Complete the initial physical sends in this all-started fixture.
        # Decision counts generally need not equal starts if requests expire.
        data["transmissions"].extend([
            dict(tx_id=5, flow_id=2, sender=0, packet_kind="DATA", start=1., end=2., toa_s=1., path=[0,1,2], path_index=0, repair_index=None),
            dict(tx_id=6, flow_id=3, sender=0, packet_kind="FLOOD", start=1., end=2., toa_s=1., path=[0], path_index=0, repair_index=None),
        ])
        data["raw"].update(tx_ledger_airtime_s=7., started_request_count=6)
        result = analysis.summarize_run(**data)
        source_by_flow = {f["flow_id"]: f["src"] for f in data["flows"]}
        initial = [tx for tx in data["transmissions"] if tx["sender"] == source_by_flow[tx["flow_id"]]
                   and tx["repair_index"] is None and tx["packet_kind"] in {"DATA", "FLOOD"}]
        self.assertEqual(result["metrics"]["initial_routed_flow_count"], sum(t["packet_kind"] == "DATA" for t in initial))
        self.assertEqual(result["metrics"]["initial_flood_flow_count"], sum(t["packet_kind"] == "FLOOD" for t in initial))
        self.assertEqual(result["metrics"]["initial_routed_flow_count"], 2)
        self.assertEqual(result["metrics"]["initial_flood_flow_count"], 1)

    def test_fault_window_populations_do_not_imply_carried_path_exposure(self):
        data = fixture()
        data["identity"]["common_environment"]["faults"] = [dict(start_s=5., end_s=8., attenuation_db=80., edges=[[1,2]])]
        data["flows"][2]["enqueued_at"] = 6.
        result = analysis.summarize_run(**data)
        metrics = result["metrics"]
        self.assertEqual(metrics["fault_period_active_flows"], 2)
        self.assertEqual(metrics["fault_period_enqueued_flows"], 1)
        self.assertEqual(metrics["fault_period_active_with_initial_before_window_flows"], 1)
        self.assertEqual(metrics["source_path_fault_exposed_flows"], 0)
        by_id = {f["flow_id"]: f for f in result["flows"]}
        self.assertFalse(by_id[1]["fault_period_active"])  # ACK completed before the fault.
        self.assertTrue(by_id[2]["fault_period_active_with_initial_before_window"])
        self.assertTrue(by_id[3]["fault_period_enqueued"])

    def test_rrep_next_hop_follows_path_order_and_ack_uses_reverse_index(self):
        data = fixture()
        data["transmissions"].extend([
            dict(tx_id=5, flow_id=1, sender=0, packet_kind="RREP", start=0., end=1., toa_s=1., path=[0,1,2], path_index=0, repair_index=None),
            dict(tx_id=6, flow_id=2, sender=1, packet_kind="RREP", start=1., end=2., toa_s=1., path=[2,1,0], path_index=1, repair_index=None),
        ])
        data["rx_attempts"].extend([
            dict(tx_id=5, receiver=1, reason="success", decoded=True),
            dict(tx_id=5, receiver=2, reason="success", decoded=True),
            dict(tx_id=6, receiver=0, reason="success", decoded=True),
            dict(tx_id=6, receiver=2, reason="success", decoded=True),
            dict(tx_id=2, receiver=0, reason="success", decoded=True),
        ])
        data["raw"].update(tx_ledger_airtime_s=7., started_request_count=6)
        rows = analysis.summarize_run(**data)["rx"]
        counts = {(r["packet_kind"], r["receiver_relation"]): r["count"] for r in rows}
        self.assertEqual(counts[("RREP", "designated_next_hop")], 2)
        self.assertEqual(counts[("RREP", "other_listener")], 2)
        self.assertEqual(counts[("ACK", "designated_next_hop")], 1)
        self.assertEqual(counts[("ACK", "other_listener")], 1)
        self.assertNotIn(("RREP", "broadcast_listener"), counts)

    def test_zero_success_kept_undefined_and_future_reservation_rejected(self):
        data = fixture()
        for f in data["flows"]:
            f.update(accepted_ack_at=None, first_delivery_at=None, ack_by_deadline=False, delivery_by_deadline=False)
        data["acks"] = []
        data["raw"].update(ack_pdr_deadline=0., delivery_pdr_deadline=0.)
        result = analysis.summarize_run(**data)
        self.assertIsNone(result["metrics"]["airtime_per_timely_delivery_s"])
        self.assertIsNone(result["metrics"]["timely_ack_latency_p50_s"])
        self.assertEqual(result["metrics"]["unfinished_ack_fraction"], 1.)
        self.assertEqual(len(result["flows"]), 3)
        data = fixture()
        data["transmissions"][0].update(start=11.,end=12.)
        with self.assertRaisesRegex(ValueError,"future"):
            analysis.summarize_run(**data)

    def test_no_observed_cancel_checks_are_not_an_invented_denominator(self):
        data = fixture()
        data["actions"] = [a for a in data["actions"] if a["event"] != "cpr-cancel-check"]
        result = analysis.summarize_run(**data, cancel_checks_observable=False)
        self.assertIsNone(result["metrics"]["ack_cancel_check_count"])
        self.assertIsNone(result["metrics"]["ack_cancel_success_per_decoded_ack_check"])
        with self.assertRaisesRegex(ValueError,"checks/success"):
            analysis.summarize_run(**data, cancel_checks_observable=True)

    def test_duplicate_tx_and_deadline_corruption_rejected(self):
        data = fixture()
        data["transmissions"].append(deepcopy(data["transmissions"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate physical"):
            analysis.summarize_run(**data)
        data = fixture()
        data["flows"][0]["accepted_ack_at"] = 11.
        with self.assertRaisesRegex(ValueError,"deadline flag"):
            analysis.summarize_run(**data)

    def test_cost_summary_includes_zero_cell_seeds(self):
        meta = dict(plan_sha256="p",case_id="c",arm_id="a",protocol="meshecho-cpr")
        runs = [{**meta,"seed":1,"tx_ledger_airtime_s":4.},{**meta,"seed":2,"tx_ledger_airtime_s":2.}]
        cells = [{**meta,"seed":1,"packet_kind":"FLOOD","stage":"recovery","airtime_s":4.,"tx_count":2},
                 {**meta,"seed":2,"packet_kind":"DATA","stage":"initial","airtime_s":2.,"tx_count":1}]
        summary = analysis.summarize_costs(cells,runs)
        flood = next(r for r in summary if r["packet_kind"] == "FLOOD")
        self.assertEqual(flood["mean_airtime_s"], 2.)
        self.assertAlmostEqual(sum(r["fraction_of_complete_airtime"] for r in summary),1.)
        cells[0]["airtime_s"] = 1.
        with self.assertRaisesRegex(ValueError,"partition"):
            analysis.summarize_costs(cells,runs)


class TestCompletePlanBoundary(unittest.TestCase):
    def load_fixture(self, selections, delays):
        arms = [dict(id=arm, protocol="meshecho-cpr", parameters={}) for arm in delays]
        cases = [dict(id=scenario, scenario=scenario, configuration="default",
                      case={"key":scenario,"rate_per_min":rate}, environment={"faults":[]},
                      deadline_s=30., arms=selections[scenario]) for scenario,rate in (("S1",4.),("S3",20.))]
        plans = {"p":{"matrix":{"seeds":[1,2],"arms":arms,"cases":cases}}}
        summaries, runs, flows, costs = [], [], [], []
        for ci, case in enumerate(cases):
            for ai, arm in enumerate(arms):
                if arm["id"] not in case["arms"]:
                    continue
                meta = dict(plan_sha256="p",case_id=case["id"],arm_id=arm["id"],protocol=arm["protocol"],experiment_id="synthetic")
                for metric, value in (("ack_pdr_deadline",.9-ai*.1-ci*.05),("tx_ledger_airtime_s",2.+ai+ci)):
                    summaries.append({**meta,"metric":metric,"n":2,"mean":value,"ci_low":value,"ci_high":value})
                for seed in (1,2):
                    parameters = resolved_parameters(arm["protocol"])
                    parameters["flood_base_delay_s"] = delays[arm["id"]]
                    runs.append({**meta,"seed":seed,"resolved_protocol_parameters":parameters})
                flows.append({**meta,"timely_ack_latency_s":1.})
                costs.append({**meta,"packet_kind":"DATA","stage":"initial","airtime_s":2.})
        return plans, summaries, runs, flows, costs

    def test_load_curve_rejects_different_effective_arms_and_matches_defaults(self):
        fixture_data = self.load_fixture({"S1":["implicit"],"S3":["explicit"]},{"implicit":.45,"explicit":9.})
        plans, summaries, runs, flows, costs = fixture_data
        self.assertEqual(analysis.load_series(summaries,runs,plans), [])
        with tempfile.TemporaryDirectory() as temporary:
            plots = analysis.make_plots(Path(temporary),summaries,[],flows,costs,plans,runs)
            self.assertNotIn("load_curve.svg",plots)
        # Different requested overrides with the same resolved value are equivalent.
        plans["p"]["matrix"]["arms"][1]["parameters"] = {"flood_base_delay_s":.45}
        for run in runs:
            run["resolved_protocol_parameters"]["flood_base_delay_s"] = .45
        series = analysis.load_series(summaries,runs,plans)
        self.assertEqual(len(series),1)
        self.assertEqual(series[0]["arm_ids"],["explicit","implicit"])
        self.assertEqual([p["rate_per_min"] for p in series[0]["points"]],[4.,20.])
        plans["p"]["matrix"]["cases"][1]["configuration"] = "matched"
        self.assertEqual(analysis.load_series(summaries,runs,plans), [])

    def test_load_plot_retains_three_same_protocol_arms_without_first_row_selection(self):
        arms = ["slow","medium","fast"]
        plans, summaries, runs, flows, costs = self.load_fixture({"S1":arms,"S3":arms},dict(zip(arms,[9.,2.,.45])))
        series = analysis.load_series(summaries,runs,plans)
        self.assertEqual({s["label"] for s in series},set(arms))
        import matplotlib.axes
        actual_plot = matplotlib.axes.Axes.plot
        captured = []
        def record_plot(ax, x, y, *args, **kwargs):
            if kwargs.get("label") in arms:
                captured.append((kwargs["label"],list(x),list(y)))
            return actual_plot(ax,x,y,*args,**kwargs)
        with tempfile.TemporaryDirectory() as temporary, patch.object(matplotlib.axes.Axes,"plot",record_plot):
            plots = analysis.make_plots(Path(temporary),summaries,[],flows,costs,plans,runs)
            self.assertIn("load_curve.svg",plots)
        self.assertEqual(len(captured),6)
        for ai, arm in enumerate(arms):
            lines = [line for line in captured if line[0] == arm]
            self.assertEqual(len(lines),2)
            self.assertTrue(all(line[1] == [4.,20.] for line in lines))
            self.assertEqual(lines[0][2],[.9-ai*.1,.9-ai*.1-.05])
            self.assertEqual(lines[1][2],[2.+ai,3.+ai])
        # Even equal effective parameters do not collapse simultaneous arms.
        for run in runs:
            run["resolved_protocol_parameters"]["flood_base_delay_s"] = .45
        self.assertEqual({s["label"] for s in analysis.load_series(summaries,runs,plans)},set(arms))

    def test_load_curve_requires_complete_effective_identity_for_every_seed(self):
        plans, summaries, runs, _, _ = self.load_fixture({"S1":["arm"],"S3":["arm"]},{"arm":.45})
        self.assertEqual(len(analysis.load_series(summaries,runs,plans)),1)
        runs[-1]["resolved_protocol_parameters"]["fixed_guard_s"] = 20.
        self.assertEqual(analysis.load_series(summaries,runs,plans), [])
        runs[-1].pop("resolved_protocol_parameters")
        self.assertEqual(analysis.load_series(summaries,runs,plans), [])

    def test_clean_ablation_requires_resolved_parameters_and_single_toggle(self):
        left = {seed: {"resolved_protocol_parameters": resolved_parameters("meshecho-cpr")} for seed in (1,2)}
        for protocol, toggle in analysis.ABLATION_TOGGLES.items():
            right = {seed: {"resolved_protocol_parameters": resolved_parameters(protocol)} for seed in (1,2)}
            result = analysis.comparison_policy(left, right, protocol)
            self.assertEqual(result["comparison_kind"], "ablation")
            self.assertEqual({d["field"] for d in result["resolved_parameter_differences"]}, {"name", toggle})
            for field in ("fixed_guard_s", "route_ttl_s", "relay_capacity", "relay_ledger_enabled"):
                altered = deepcopy(right)
                altered[2]["resolved_protocol_parameters"][field] = 99
                mixed = analysis.comparison_policy(left, altered, protocol)
                self.assertEqual(mixed["comparison_kind"], "mixed-policy")
                self.assertIn(field, mixed["unexpected_parameter_fields"])
                self.assertTrue(any(d["seed"] == 2 and d["field"] == field for d in mixed["resolved_parameter_differences"]))
            right[1]["resolved_protocol_parameters"][toggle] = True
            self.assertEqual(analysis.comparison_policy(left, right, protocol)["comparison_kind"], "mixed-policy")
        self.assertEqual(analysis.comparison_policy(left, {1:{},2:{}}, "meshecho-cpr-norepeat")["comparison_kind"], "mixed-policy")
        self.assertEqual(analysis.comparison_policy(left, left, "meshecho-cpr-nocancel")["comparison_kind"], "component-policy")

    def test_synthetic_complete_pipeline_emits_real_pdf_svg_and_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "snapshot/source"
            source.mkdir(parents=True)
            (source / "lora_mesh_sim.py").write_text("# synthetic fixture: cpr-cancel-check\n")
            arms = [dict(id=p,protocol=p,parameters={}) for p in
                    ("meshecho-cpr","meshecho","meshtastic","meshcore","meshecho-cpr-norepeat")]
            cases = [dict(id=scenario,scenario=scenario,configuration="default",case={"key":scenario,"rate_per_min":rate},
                          environment={"faults":[]},deadline_s=10.) for scenario,rate in (("S1",4.),("S3",20.))]
            plan = {"plan_sha256":"p","source_snapshot":"s","snapshot_path":"snapshot","tested_version":"synthetic",
                    "matrix":{"experiment_id":"synthetic-only","stage":"development","seeds":[1,2],
                              "arms":arms,"cases":cases,"statistics":{"analysis_seed":11,"bootstrap_resamples":10000}},"runs":[]}
            completed = []
            for case in cases:
                for arm in arms:
                    for seed in (1,2):
                        key = f"{case['id']}-{arm['id']}-{seed}"
                        spec = dict(run_key=key,case_id=case["id"],arm_id=arm["id"],case=case,arm=arm,seed=seed)
                        plan["runs"].append(spec)
                        rel = Path("results/secon2027/runs") / key / "attempt-001"
                        attempt = root / rel
                        attempt.mkdir(parents=True)
                        data = fixture()
                        data["identity"]["protocol_parameters_by_arm"] = {arm["protocol"]: resolved_parameters(arm["protocol"])}
                        data["raw"].update(protocol=arm["protocol"],**{k:f"shared-{seed}" for k in analysis.PAIR_IDENTITIES})
                        analysis.write_csv(attempt / "evidence.runs.csv",[data["raw"]])
                        for item in ("flows","actions","requests","transmissions","rx_attempts","acks"):
                            (attempt / f"evidence.{item}.jsonl").write_text("".join(json.dumps(r)+"\n" for r in data[item]))
                        (attempt / "evidence.identities.json").write_text(json.dumps({str(seed):data["identity"]}))
                        (attempt / "evidence.manifest.json").write_text("{}\n")
                        completed.append(dict(run_key=key,attempt_path=str(rel),wall_seconds=0.))
            path = root / "plan.json"
            path.write_text(json.dumps(plan))
            audit = dict(status="complete",plan_sha256="p",completed=completed,missing=[],failed=[])
            out = root / "analysis"
            with patch("tools.secon2027_experiment.audit_plan",return_value=audit):
                result = analysis.analyze_plans([path],out,root=root)
            self.assertEqual(result["status"],"complete")
            self.assertEqual(result["completed_runs"],20)
            self.assertTrue(result["small_sample_unstable"])
            for name in ("main_results","paired_effects","ablation_effects","latency","cost_decomposition","load_curve"):
                self.assertTrue((out / (name + ".pdf")).read_bytes().startswith(b"%PDF"))
                self.assertIn("<svg",(out / (name + ".svg")).read_text())
            self.assertTrue(result["files"]["cost_summary.csv"]["sha256"])

    def test_pairing_checks_seed_identity_and_complete_population(self):
        base = analysis.summarize_run(**fixture())["metrics"]
        runs = []
        for protocol in ("meshecho-cpr", "meshcore"):
            for seed in (1,2,3):
                runs.append({**base, "plan_sha256":"p", "experiment_id":"synthetic", "stage":"development",
                             "case_id":"c", "scenario":"S1", "configuration":"default", "arm_id":protocol,
                             "protocol":protocol, "seed":seed,
                             **{key: f"shared-{seed}" for key in analysis.PAIR_IDENTITIES}})
        plans = {"p":{"matrix":{"experiment_id":"synthetic", "stage":"development", "seeds":[1,2,3],
                 "cases":[dict(id="c",scenario="S1",configuration="default")],
                 "arms":[dict(id=p,protocol=p) for p in ("meshecho-cpr","meshcore")]}}}
        summaries, contrasts, pairs = analysis.aggregate_runs(runs,plans,analysis_seed=11,resamples=10000)
        self.assertEqual(len(contrasts),3)
        self.assertTrue(all(row["mean"] == 0 for row in contrasts))
        self.assertEqual(len(pairs),9)
        runs[-1]["environment_sha256"] = "different channel"
        with self.assertRaisesRegex(ValueError,"exogenous identities"):
            analysis.aggregate_runs(runs,plans,analysis_seed=11,resamples=10000)
        with self.assertRaisesRegex(ValueError,"planned seeds"):
            analysis.aggregate_runs(runs[:-1],plans,analysis_seed=11,resamples=10000)

    def test_incomplete_writes_inventory_only_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "plan.json"
            plan = {"plan_sha256":"p","source_snapshot":"s","tested_version":"test",
                    "matrix":{"experiment_id":"synthetic-only"},
                    "runs":[dict(run_key="r",case_id="c",arm_id="a",seed=1)]}
            path.write_text(json.dumps(plan))
            audit = dict(status="incomplete",plan_sha256="p",completed=[],missing=["r"],failed=[])
            out = root / "analysis"
            with patch("tools.secon2027_experiment.audit_plan",return_value=audit):
                result = analysis.analyze_plans([path],out,root=root)
                self.assertEqual(result["status"],"incomplete")
                self.assertFalse((out / "summary.csv").exists())
                self.assertEqual({p.name for p in out.iterdir()},{"planned_runs.csv","analysis.json"})
                with self.assertRaises(FileExistsError):
                    analysis.analyze_plans([path],out,root=root)


if __name__ == "__main__":
    unittest.main()
