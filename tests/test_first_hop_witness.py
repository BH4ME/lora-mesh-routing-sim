import unittest

from lora_mesh_sim import Node, Packet, RadioConfig, Transmission, build_protocol
from tools.diagnose_sr_observability import ObservabilitySimulator
from tools.diagnose_first_hop_witness import (
    WitnessSimulator,
    analyze_first_hop_witness,
    run_diagnostic,
    summarize_ack_query_stratum,
)
from tools.run_sr_experiment import SR_CASES, run_one_sr


class FirstHopWitnessTest(unittest.TestCase):
    def test_replay_matches_frozen_runner_trace_and_outcomes(self):
        observed = run_diagnostic(12001)
        frozen = run_one_sr(SR_CASES["recurring_fading"], "meshecho-dhr", 12001).row

        self.assertEqual(observed["scheduled_trace_sha256"],
                         frozen["scheduled_trace_sha256"])
        self.assertEqual(observed["scheduled_flows"],
                         frozen["scheduled_unicast_flows"])
        self.assertEqual(observed["ack_by_deadline"], frozen["ack_by_deadline"])
        self.assertEqual(observed["delivery_by_deadline"],
                         frozen["delivery_by_deadline"])

    def test_flood_decode_tap_preserves_phy_random_stream(self):
        nodes = [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
                 Node(2, 20.0, 0.0), Node(3, 15.0, 5.0)]
        radio = RadioConfig(sf=7, shadow_sigma_db=0.0,
                            temporal_fading_sigma_db=0.0)
        observed = WitnessSimulator(
            nodes, radio, build_protocol("meshecho-dhr"), seed=12001,
            max_hops=6, independent_random_streams=True,
        )
        baseline = ObservabilitySimulator(
            nodes, radio, build_protocol("meshecho-dhr"), seed=12001,
            max_hops=6, independent_random_streams=True,
        )
        flood = Packet("FLOOD", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                       request_id=1, path=(0, 3))
        tx = Transmission(1, 3, flood, 1.0, 1.1)
        for sim in (observed, baseline):
            sim.protocol.flow_data_actions[1] = "F"

        tapped = observed.try_receive(tx, 1)
        control = baseline.try_receive(tx, 1)

        self.assertEqual(tapped is not None, control is not None)
        self.assertEqual(observed.channel_random.getstate(),
                         baseline.channel_random.getstate())
        self.assertEqual(observed.metrics.rx_success, baseline.metrics.rx_success)
        self.assertIn(1, observed.successful_decodes[tx.tx_id])

    def test_runner_rejects_seeds_outside_fresh_exploratory_set(self):
        with self.assertRaisesRegex(ValueError, "fresh exploratory seeds"):
            run_diagnostic(12004)

    def make_sim(self):
        sim = WitnessSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
             Node(2, 20.0, 0.0), Node(3, 15.0, 5.0),
             Node(4, 15.0, -5.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0,
                        temporal_fading_sigma_db=0.0),
            build_protocol("meshecho-dhr"), seed=12001, max_hops=6,
            independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 2, 0.0)
        sim.metrics.register_flow(2, 0, 2, 2.5)
        sim.protocol.flow_data_actions.update({1: "F", 2: "R"})
        return sim

    def test_prior_local_flood_decode_nominates_one_current_data_witness(self):
        sim = self.make_sim()
        flood = Packet("FLOOD", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                       request_id=1, path=(0, 3))
        ack = Packet("ACK", 1, 2, 0, 6, 0.0, "meshecho-dhr",
                     request_id=1, path=(0, 1, 2), path_index=0,
                     app_payload=False)
        data = Packet("DATA", 2, 0, 2, 6, 2.5, "meshecho-dhr",
                      request_id=2, path=(0, 1, 2))
        sim.tx_history = [
            Transmission(1, 3, flood, 1.0, 1.1),
            Transmission(2, 1, ack, 2.0, 2.1),
            Transmission(3, 0, data, 3.0, 3.1),
        ]
        sim.successful_decodes = {1: {1: 0.0}, 2: {0: 0.0}, 3: {3: 0.0}}
        sim.protocol.action_events = [
            {"event": "commit", "time": 2.1, "flow_id": 1,
             "src": 0, "dst": 2, "path": (0, 1, 2)},
        ]

        result = analyze_first_hop_witness(sim, cutoff_s=30.0)

        self.assertEqual(len(result["hops"]), 1)
        hop = result["hops"][0]
        self.assertFalse(hop["intended_next_hop_decoded"])
        self.assertEqual(hop["off_path_decoders"], [3])
        self.assertEqual(hop["nominated_candidate"], 3)
        self.assertTrue(hop["nominated_candidate_decoded_current"])
        self.assertTrue(hop["guard_oracle_eligible"])

    def test_commit_after_current_flow_enqueue_cannot_supply_nomination(self):
        sim = self.make_sim()
        sim.metrics.flows[2].created_at = 1.5
        flood = Packet("FLOOD", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                       request_id=1, path=(0, 3))
        ack = Packet("ACK", 1, 2, 0, 6, 0.0, "meshecho-dhr",
                     request_id=1, path=(0, 1, 2), path_index=0,
                     app_payload=False)
        data = Packet("DATA", 2, 0, 2, 6, 1.5, "meshecho-dhr",
                      request_id=2, path=(0, 1, 2))
        sim.tx_history = [
            Transmission(1, 3, flood, 1.0, 1.1),
            Transmission(2, 1, ack, 2.0, 2.1),
            Transmission(3, 0, data, 3.0, 3.1),
        ]
        sim.successful_decodes = {1: {1: 0.0}, 2: {0: 0.0}, 3: {3: 0.0}}
        sim.protocol.action_events = [
            {"event": "commit", "time": 2.1, "flow_id": 1,
             "src": 0, "dst": 2, "path": (0, 1, 2)},
        ]

        hop = analyze_first_hop_witness(sim, cutoff_s=30.0)["hops"][0]

        self.assertIsNone(hop["route_commit_flow_id"])
        self.assertIsNone(hop["nominated_candidate"])

    def test_nomination_uses_latest_local_history_not_current_oracle_decoder(self):
        sim = self.make_sim()
        def flood(flow_id, sender):
            return Packet("FLOOD", flow_id, 0, 2, 6, 0.0, "meshecho-dhr",
                          request_id=flow_id, path=(0, sender))
        ack = Packet("ACK", 1, 2, 0, 6, 0.0, "meshecho-dhr",
                     request_id=1, path=(0, 1, 2), path_index=0,
                     app_payload=False)
        data = Packet("DATA", 2, 0, 2, 6, 2.5, "meshecho-dhr",
                      request_id=2, path=(0, 1, 2))
        sim.tx_history = [
            Transmission(1, 3, flood(1, 3), 1.0, 1.1),
            Transmission(2, 4, flood(1, 4), 1.5, 1.6),
            Transmission(3, 1, ack, 2.0, 2.1),
            Transmission(4, 0, data, 3.0, 3.1),
        ]
        sim.successful_decodes = {
            1: {1: 0.0}, 2: {1: 0.0}, 3: {0: 0.0}, 4: {3: 0.0},
        }
        sim.protocol.action_events = [
            {"event": "commit", "time": 2.1, "flow_id": 1,
             "src": 0, "dst": 2, "path": (0, 1, 2)},
        ]

        hop = analyze_first_hop_witness(sim, cutoff_s=30.0)["hops"][0]

        self.assertEqual(hop["nominated_candidate"], 4)
        self.assertEqual(hop["off_path_decoders"], [3])
        self.assertFalse(hop["nominated_candidate_decoded_current"])
        self.assertFalse(hop["guard_oracle_eligible"])

    def test_ack_query_stratum_separates_destination_truth_and_relay_ack_decode(self):
        sim = self.make_sim()
        sim.metrics.register_flow(3, 0, 2, 2.5)
        sim.protocol.flow_data_actions[3] = "R"
        def data(flow_id, index):
            return Packet("DATA", flow_id, 0, 2, 6, 2.5, "meshecho-dhr",
                          request_id=flow_id, path=(0, 1, 2),
                          path_index=index)
        ack = Packet("ACK", 2, 2, 0, 6, 3.3, "meshecho-dhr",
                     request_id=2, path=(0, 1, 2), path_index=1,
                     app_payload=False)
        sim.tx_history = [
            Transmission(1, 0, data(2, 0), 3.0, 3.1),
            Transmission(2, 1, data(2, 1), 3.2, 3.3),
            Transmission(3, 2, ack, 3.4, 3.5),
            Transmission(4, 1, ack.retreat_path(), 3.6, 3.7),
            Transmission(5, 0, data(3, 0), 4.0, 4.1),
            Transmission(6, 1, data(3, 1), 4.2, 4.3),
        ]
        sim.successful_decodes = {
            1: {1: 0.0}, 2: {0: 0.0, 2: 0.0}, 3: {1: 0.0},
            5: {1: 0.0}, 6: {0: 0.0},
        }
        sim.metrics.flows[2].delivered_at = 3.3

        result = summarize_ack_query_stratum(sim, cutoff_s=40.0)

        self.assertEqual(result["summary"]["source_observed_unacked_r_flows"], 2)
        self.assertEqual(result["by_destination_delivery"]["delivered"]["flows"], 1)
        self.assertEqual(result["by_destination_delivery"]["delivered"]["relay_ack_decoded"], 1)
        self.assertEqual(result["by_destination_delivery"]["not_delivered"]["no_ack_emitted"], 1)

    def test_direct_r_hop_is_separate_from_multihop_relay_progress(self):
        sim = self.make_sim()
        data = Packet("DATA", 2, 0, 2, 6, 2.5, "meshecho-dhr",
                      request_id=2, path=(0, 2))
        sim.tx_history = [Transmission(1, 0, data, 3.0, 3.1)]
        sim.successful_decodes = {1: {2: 0.0, 3: 0.0}}

        result = analyze_first_hop_witness(sim, cutoff_s=40.0)

        self.assertEqual(result["hops"][0]["first_hop_type"], "direct")
        self.assertEqual(result["summary"]["direct_first_hops"], 1)
        self.assertEqual(result["summary"]["multihop_first_hops"], 0)
        self.assertEqual(
            summarize_ack_query_stratum(sim, cutoff_s=40.0)["summary"]
            ["source_observed_unacked_r_flows"], 0,
        )

    def test_local_observation_ttl_strata_expire_old_witness(self):
        sim = self.make_sim()
        sim.metrics.flows[1].created_at = 190.0
        sim.metrics.flows[2].created_at = 205.0
        older_flood = Packet("FLOOD", 0, 0, 2, 6, 1.0, "meshecho-dhr",
                             request_id=0, path=(0, 3))
        ack = Packet("ACK", 1, 2, 0, 6, 190.0, "meshecho-dhr",
                     request_id=1, path=(0, 1, 2), path_index=0,
                     app_payload=False)
        data = Packet("DATA", 2, 0, 2, 6, 205.0, "meshecho-dhr",
                      request_id=2, path=(0, 1, 2))
        sim.tx_history = [
            Transmission(1, 3, older_flood, 1.0, 1.1),
            Transmission(2, 1, ack, 200.0, 200.1),
            Transmission(3, 0, data, 206.0, 206.1),
        ]
        sim.successful_decodes = {1: {1: 0.0}, 2: {0: 0.0}, 3: {3: 0.0}}
        sim.protocol.action_events = [
            {"event": "commit", "time": 200.1, "flow_id": 1,
             "src": 0, "dst": 2, "path": (0, 1, 2)},
        ]

        result = analyze_first_hop_witness(sim, cutoff_s=240.0)
        strata = result["summary"]["local_observation_ttl_strata"]

        self.assertAlmostEqual(result["hops"][0]["history_age_at_ack_s"], 198.9)
        self.assertEqual(strata["no_ttl_upper_bound"]["nominated_failed_hops"], 1)
        self.assertEqual(strata["30s"]["nominated_failed_hops"], 0)
        self.assertEqual(strata["120s"]["nominated_failed_hops"], 0)
        self.assertEqual(strata["300s"]["nominated_failed_hops"], 1)
        self.assertEqual(strata["300s"]["current_decode"], 1)
        self.assertEqual(strata["300s"]["guard_oracle"], 1)

    def test_direct_unacked_flows_report_delivery_truth_only_post_hoc(self):
        sim = self.make_sim()
        sim.metrics.register_flow(3, 0, 2, 2.5)
        sim.protocol.flow_data_actions[3] = "R"
        def direct(flow_id):
            return Packet("DATA", flow_id, 0, 2, 6, 2.5, "meshecho-dhr",
                          request_id=flow_id, path=(0, 2))
        sim.tx_history = [
            Transmission(1, 0, direct(2), 3.0, 3.1),
            Transmission(2, 0, direct(3), 4.0, 4.1),
        ]
        sim.successful_decodes = {1: {2: 0.0}}
        sim.metrics.flows[2].delivered_at = 3.1

        result = analyze_first_hop_witness(sim, cutoff_s=40.0)

        self.assertEqual(result["summary"]["direct_unacked_flow_outcomes"], {
            "total": 2, "delivered": 1, "not_delivered": 1,
            "censored_deadlines": 0,
        })
