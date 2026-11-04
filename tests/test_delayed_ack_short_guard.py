import unittest
from dataclasses import replace
from types import SimpleNamespace

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol


class TraceSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > before:
            self.tx_history.append(self.transmissions[-1])


class InitialRDropSimulator(TraceSimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.kind == "DATA" and tx.packet.flow_id == 2
                and tx.packet.repair_index is None):
            self.metrics.rx_fail += 1
            return None
        return super().try_receive(tx, receiver)


class SourceAckDropSimulator(TraceSimulator):
    def __init__(self, *args, dropped_flows=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.dropped_flows = set(dropped_flows)

    def try_receive(self, tx, receiver):
        if (receiver == 0 and tx.packet.kind == "ACK"
                and tx.packet.flow_id in self.dropped_flows):
            self.metrics.rx_fail += 1
            return None
        return super().try_receive(tx, receiver)


class UnackedRecoverySimulator(InitialRDropSimulator):
    def try_receive(self, tx, receiver):
        if (receiver == 0 and tx.packet.kind == "ACK"
                and tx.packet.flow_id == 2):
            self.metrics.rx_fail += 1
            return None
        return super().try_receive(tx, receiver)


class SameTimestampAckSimulator(TraceSimulator):
    def begin_transmission(self, sender, packet, pending):
        super().begin_transmission(sender, packet, pending)
        if (sender == packet.origin and packet.kind == "DATA"
                and packet.flow_id == 2 and packet.repair_index is None):
            initial_r = self.transmissions[-1]
            ack = replace(packet, kind="ACK", origin=packet.final_dst,
                          final_dst=sender, app_payload=False, path_index=0)
            self.nodes[packet.final_dst].tx_available_at = (
                initial_r.start + 1.0 - self.radio.packet_toa_s(ack)
            )


def run_two_flows(protocol_name, *, source_available_at=None,
                  simulator_type=InitialRDropSimulator, protocol_args=None):
    sim = simulator_type(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        build_protocol(protocol_name, protocol_args), seed=17, max_hops=6,
        independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.run(4.0)
    if source_available_at is not None:
        sim.nodes[0].tx_available_at = source_available_at
    sim.schedule(5.0, "app_send", (0, 1, 2))
    metrics = sim.run(50.0)
    return sim, metrics


class DelayedAckShortGuardTest(unittest.TestCase):
    def test_ack_completing_exactly_at_guard_wins_before_recovery(self):
        sim, metrics = run_two_flows(
            "meshecho-dhr-flood-ack-delay-guard1",
            simulator_type=SameTimestampAckSimulator,
        )
        initial_r = next(tx for tx in sim.tx_history
                         if tx.packet.flow_id == 2 and tx.packet.kind == "DATA")
        ack = next(tx for tx in sim.tx_history
                   if tx.packet.flow_id == 2 and tx.packet.kind == "ACK")
        self.assertAlmostEqual(ack.end, initial_r.start + 1.0)
        self.assertAlmostEqual(metrics.flows[2].acked_at, ack.end)
        self.assertFalse(any(
            tx.packet.flow_id == 2 and tx.packet.repair_index == 2
            for tx in sim.tx_history
        ))
        self.assertFalse(any(
            event["event"] == "dhr_guard" and event["flow_id"] == 2
            for event in sim.protocol.action_events
        ))

    def test_guard1_recovery_starts_one_second_after_initial_r_tx(self):
        sim, _ = run_two_flows("meshecho-dhr-flood-ack-delay-guard1")
        initial_r = next(
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
        )
        recovery_f = next(
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "FLOOD"
            and tx.packet.repair_index == 2
        )
        self.assertAlmostEqual(recovery_f.start - initial_r.start, 1.0)

    def test_each_short_guard_has_its_own_name_and_recovery_time(self):
        for guard_s in (1, 2, 4, 8):
            with self.subTest(guard_s=guard_s):
                name = f"meshecho-dhr-flood-ack-delay-guard{guard_s}"
                sim, _ = run_two_flows(name)
                initial_r = next(
                    tx for tx in sim.tx_history
                    if tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                )
                recovery_f = next(
                    tx for tx in sim.tx_history
                    if tx.packet.flow_id == 2 and tx.packet.kind == "FLOOD"
                    and tx.packet.repair_index == 2
                )
                self.assertEqual(sim.protocol.name, name)
                self.assertEqual(initial_r.packet.protocol, name)
                self.assertEqual(recovery_f.packet.protocol, name)
                self.assertAlmostEqual(
                    recovery_f.start - initial_r.start, guard_s
                )
                timeouts = [
                    event for event in sim.protocol.action_events
                    if event["event"] == "timeout" and event["flow_id"] == 2
                    and event["reason"] == "source-ack-timeout"
                ]
                self.assertEqual(len(timeouts), 1)
                self.assertAlmostEqual(timeouts[0]["time"], recovery_f.start)

    def test_on_time_r_ack_prevents_recovery_and_late_timer_is_inert(self):
        for guard_s in (1, 2, 4, 8):
            with self.subTest(guard_s=guard_s):
                name = f"meshecho-dhr-flood-ack-delay-guard{guard_s}"
                sim = TraceSimulator(
                    [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    build_protocol(name), seed=17, max_hops=6,
                    independent_random_streams=True,
                )
                sim.schedule(1.0, "app_send", (0, 1, 1))
                sim.schedule(5.0, "app_send", (0, 1, 2))

                metrics = sim.run(40.0)

                self.assertEqual(sim.protocol.flow_data_actions[2], "R")
                self.assertIsNotNone(metrics.flows[2].acked_at)
                self.assertFalse(any(
                    tx.packet.flow_id == 2 and tx.packet.repair_index == 2
                    for tx in sim.tx_history
                ))
                self.assertFalse(any(
                    event["event"] == "timeout" and event["flow_id"] == 2
                    for event in sim.protocol.action_events
                ))

    def test_initial_f_keeps_two_second_destination_ack_and_15_second_source_guard(self):
        for guard_s in (1, 2, 4, 8):
            with self.subTest(guard_s=guard_s):
                sim = SourceAckDropSimulator(
                    [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    build_protocol(
                        f"meshecho-dhr-flood-ack-delay-guard{guard_s}"
                    ),
                    seed=17, max_hops=6, independent_random_streams=True,
                    dropped_flows=(1,),
                )
                sim.schedule(1.0, "app_send", (0, 1, 1))

                metrics = sim.run(20.0)

                flood = next(
                    tx for tx in sim.tx_history
                    if tx.sender == 0 and tx.packet.kind == "FLOOD"
                )
                ack = next(
                    tx for tx in sim.tx_history
                    if tx.sender == 1 and tx.packet.kind == "ACK"
                )
                timeout = next(
                    event for event in sim.protocol.action_events
                    if event["event"] == "timeout" and event["flow_id"] == 1
                    and event["reason"] == "source-ack-timeout"
                )
                self.assertAlmostEqual(
                    ack.start - metrics.flows[1].delivered_at, 2.0
                )
                self.assertAlmostEqual(timeout["time"] - flood.start, 15.0)

    def test_discovery_candidate_data_keeps_15_second_source_guard(self):
        for guard_s in (1, 2, 4, 8):
            with self.subTest(guard_s=guard_s):
                sim = SourceAckDropSimulator(
                    [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    build_protocol(
                        f"meshecho-dhr-flood-ack-delay-guard{guard_s}"
                    ),
                    seed=17, max_hops=6, independent_random_streams=True,
                    dropped_flows=(3,),
                )
                for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
                    sim.schedule(when, "app_send", (0, 1, flow_id))

                sim.run(240.0)

                self.assertEqual(sim.protocol.flow_actions[3], "D")
                self.assertEqual(sim.protocol.flow_data_actions[3], "D-candidate")
                data = next(
                    tx for tx in sim.tx_history
                    if tx.sender == 0 and tx.packet.flow_id == 3
                    and tx.packet.kind == "DATA"
                )
                timeout = next(
                    event for event in sim.protocol.action_events
                    if event["event"] == "timeout" and event["flow_id"] == 3
                    and event["reason"] == "source-ack-timeout"
                )
                self.assertAlmostEqual(timeout["time"] - data.start, 15.0)

    def test_queued_initial_r_uses_physical_start_not_application_enqueue(self):
        for guard_s in (1, 2, 4, 8):
            with self.subTest(guard_s=guard_s):
                sim, metrics = run_two_flows(
                    f"meshecho-dhr-flood-ack-delay-guard{guard_s}",
                    source_available_at=12.0,
                )
                initial_r = next(
                    tx for tx in sim.tx_history
                    if tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                )
                recovery_f = next(
                    tx for tx in sim.tx_history
                    if tx.packet.flow_id == 2 and tx.packet.kind == "FLOOD"
                    and tx.packet.repair_index == 2
                )
                self.assertAlmostEqual(metrics.flows[2].created_at, 5.0)
                self.assertAlmostEqual(initial_r.start, 12.0)
                self.assertAlmostEqual(
                    recovery_f.start - initial_r.start, guard_s
                )

    def test_recovery_still_requires_original_deadline_budget(self):
        for guard_s in (1, 2, 4, 8):
            with self.subTest(guard_s=guard_s):
                sim, metrics = run_two_flows(
                    f"meshecho-dhr-flood-ack-delay-guard{guard_s}",
                    source_available_at=31.0,
                )
                self.assertAlmostEqual(metrics.flows[2].created_at, 5.0)
                self.assertIsNone(metrics.flows[2].acked_at)
                self.assertFalse(any(
                    tx.packet.flow_id == 2 and tx.packet.repair_index == 2
                    for tx in sim.tx_history
                ))
                guards = [
                    event for event in sim.protocol.action_events
                    if event["event"] == "dhr_guard" and event["flow_id"] == 2
                ]
                self.assertEqual(len(guards), 1)
                self.assertFalse(guards[0]["admitted"])
                if guard_s < 8:
                    self.assertEqual(guards[0]["reason"], "deadline-budget")

    def test_original_delayed_ack_arm_keeps_15_second_r_guard(self):
        sim, metrics = run_two_flows("meshecho-dhr-flood-ack-delay")
        initial_r = next(
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
        )
        recovery_f = next(
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "FLOOD"
            and tx.packet.repair_index == 2
        )
        recovery_ack = next(
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
            and tx.packet.repair_index == 2
        )
        self.assertEqual(sim.protocol.name, "meshecho-dhr-flood-ack-delay")
        self.assertAlmostEqual(recovery_f.start - initial_r.start, 15.0)
        self.assertAlmostEqual(
            recovery_ack.start - metrics.flows[2].delivered_at, 2.0
        )

    def test_inherited_15_second_timer_cannot_repeat_failed_recovery(self):
        sim, metrics = run_two_flows(
            "meshecho-dhr-flood-ack-delay-guard1",
            simulator_type=UnackedRecoverySimulator,
        )
        recoveries = [
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "FLOOD"
            and tx.packet.repair_index == 2 and tx.sender == 0
        ]
        timeouts = [
            event for event in sim.protocol.action_events
            if event["event"] == "timeout" and event["flow_id"] == 2
            and event["reason"] == "source-ack-timeout"
        ]
        self.assertIsNone(metrics.flows[2].acked_at)
        self.assertEqual(len(recoveries), 1)
        self.assertEqual(len(timeouts), 1)

    def test_named_guard_does_not_change_with_general_ack_guard_override(self):
        sim, _ = run_two_flows(
            "meshecho-dhr-flood-ack-delay-guard8",
            protocol_args=SimpleNamespace(sr_ack_guard_s=0.25),
        )
        initial_r = next(
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
        )
        recovery_f = next(
            tx for tx in sim.tx_history
            if tx.packet.flow_id == 2 and tx.packet.kind == "FLOOD"
            and tx.packet.repair_index == 2
        )
        self.assertAlmostEqual(recovery_f.start - initial_r.start, 8.0)


if __name__ == "__main__":
    unittest.main()
