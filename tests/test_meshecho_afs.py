"""Public behavior of terminal-ACK cancellation for pending FLOOD relays."""

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, build_protocol


class RecordingSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        count = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > count:
            self.tx_history.append(self.transmissions[-1])


class IsolatedAckSimulator(RecordingSimulator):
    def try_receive(self, tx, receiver):
        if tx.packet.kind == "FLOOD" and receiver == 3:
            return None
        return super().try_receive(tx, receiver)


def run_direct_delivery(protocol_name):
    protocol = build_protocol(protocol_name)
    sim = RecordingSimulator(
        [Node(node_id, node_id * 10.0, 0.0) for node_id in range(3)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=4, independent_random_streams=True,
    )
    protocol.send_app(0, 2, 1)
    sim.run(3.0)
    return sim


def run_injected_recovery_ack(marker, flood_marker=2, ack_protocol=None,
                              ack_delay=0.2, relay_busy_until=0.0):
    protocol = build_protocol("meshecho-afs")
    nodes = [Node(node_id, node_id * 10.0, 0.0,
                  role="router" if node_id == 1 else "client")
             for node_id in range(4)]
    sim = IsolatedAckSimulator(
        nodes, RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=4, independent_random_streams=True,
    )
    sim.metrics.register_flow(7, 0, 3, 0.0)
    sim.nodes[1].tx_available_at = relay_busy_until
    sim.transmit_later(
        0, Packet("FLOOD", 7, 0, 3, 4, 0.0, protocol.name,
                  request_id=7, path=(0,), repair_index=flood_marker), 0.0,
    )
    sim.transmit_later(
        3, Packet("ACK", 7, 3, 0, 4, ack_delay,
                  ack_protocol or protocol.name,
                  request_id=7, path=(0, 3), path_index=0,
                  app_payload=False, repair_index=marker), ack_delay,
    )
    sim.run(3.0)
    return sim


def test_off_path_terminal_ack_cancels_pending_flood_but_preserves_delivery():
    candidate = run_direct_delivery("meshecho-afs")
    no_cancel = run_direct_delivery("meshecho-afs-nocancel")

    assert candidate.metrics.flows[1].delivered_at is not None
    assert candidate.metrics.flows[1].acked_at is not None
    assert no_cancel.metrics.flows[1].delivered_at is not None
    assert no_cancel.metrics.flows[1].acked_at is not None
    assert not any(tx.sender == 1 and tx.packet.kind == "FLOOD"
                   for tx in candidate.tx_history)
    assert any(tx.sender == 1 and tx.packet.kind == "FLOOD"
               for tx in no_cancel.tx_history)
    assert any(event["event"] == "afs_cancel" and event["relay"] == 1
               for event in candidate.protocol.action_events)


def test_no_cancel_arm_exactly_replays_unchanged_fixed_f():
    shadow = run_direct_delivery("meshecho-afs-nocancel")
    baseline = run_direct_delivery("meshecho-dhr-flood")

    def tx_trace(sim):
        return [
            (tx.sender, tx.packet.kind, tx.packet.flow_id,
             tx.packet.path, tx.packet.path_index, tx.packet.repair_index,
             tx.start, tx.end)
            for tx in sim.tx_history
        ]

    assert tx_trace(shadow) == tx_trace(baseline)
    assert vars(shadow.metrics.flows[1]) == vars(baseline.metrics.flows[1])
    assert shadow.metrics.total_airtime_s == baseline.metrics.total_airtime_s
    assert [event for event in shadow.protocol.action_events
            if not event["event"].startswith("afs_")] == baseline.protocol.action_events


def test_r_stage_ack_cannot_cancel_later_f_recovery_epoch():
    matching = run_injected_recovery_ack(2)
    earlier_r = run_injected_recovery_ack(None)

    assert not any(tx.sender == 1 and tx.packet.kind == "FLOOD"
                   for tx in matching.tx_history)
    assert any(tx.sender == 1 and tx.packet.kind == "FLOOD"
               for tx in earlier_r.tx_history)


def test_non_f_repair_marker_never_enrolls_pending_flood():
    invalid_epoch = run_injected_recovery_ack(1, flood_marker=1)

    assert any(tx.sender == 1 and tx.packet.kind == "FLOOD"
               for tx in invalid_epoch.tx_history)
    assert not any(event["event"] == "afs_cancel"
                   for event in invalid_epoch.protocol.action_events)


def test_simulator_only_protocol_label_is_not_ack_evidence():
    metadata_changed = run_injected_recovery_ack(
        2, ack_protocol="different-simulator-label",
    )

    assert not any(tx.sender == 1 and tx.packet.kind == "FLOOD"
                   for tx in metadata_changed.tx_history)
    assert any(event["event"] == "afs_cancel"
               for event in metadata_changed.protocol.action_events)


def test_committed_future_start_is_not_cancelable_by_later_ack():
    committed = run_injected_recovery_ack(
        2, ack_delay=1.0, relay_busy_until=3.0,
    )

    assert any(tx.sender == 1 and tx.packet.kind == "FLOOD"
               and tx.start == 3.0 for tx in committed.tx_history)
    assert not any(event["event"] == "afs_cancel"
                   for event in committed.protocol.action_events)
