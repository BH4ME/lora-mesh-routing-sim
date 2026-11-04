"""Same-wire source trigger-f control for destination-certified backup."""

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol


class TraceSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        previous = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > previous:
            self.tx_history.append(self.transmissions[-1])


class DropSecondFlowDeliverySimulator(TraceSimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 2 and receiver == 3
                and tx.packet.kind in {"DATA", "FLOOD"}):
            return None
        return super().try_receive(tx, receiver)


def run_arm(name, send_times=(1.0, 20.0, 200.0), until=204.0,
            sim_type=TraceSimulator):
    protocol = build_protocol(name)
    protocol.flood_base_delay_s = 0.5
    protocol.flood_jitter_s = 0.0
    sim = sim_type(
        [Node(i, i * 10.0, 0.0) for i in range(4)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=6, independent_random_streams=True,
    )
    for flow_id, when in enumerate(send_times, start=1):
        sim.schedule(when, "app_send", (0, 3, flow_id))
    metrics = sim.run(until)
    return protocol, sim, metrics


def test_aging_d_trigger_physically_sends_useful_f_instead_of_discovery():
    old, old_sim, _ = run_arm("meshecho-dcb")
    candidate, sim, metrics = run_arm("meshecho-dcb-source-trigger-f")

    assert [event["action"] for event in old.action_events
            if event["event"] == "decision"] == ["F", "R", "D"]
    assert [event["action"] for event in candidate.action_events
            if event["event"] == "decision"] == ["F", "R", "F"]
    assert any(tx.sender == 0 and tx.packet.flow_id == 3
               and tx.packet.kind == "RREQ" for tx in old_sim.tx_history)

    source_packets = [tx.packet for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 3]
    assert [packet.kind for packet in source_packets] == ["FLOOD"]
    assert source_packets[0].repair_index is None
    assert source_packets[0].app_payload
    assert all(tx.packet.kind not in {"RREQ", "RREP"}
               for tx in sim.tx_history if tx.packet.flow_id == 3)
    assert metrics.flows[3].delivered_at is not None


def test_trigger_f_retains_dcb_feedback_and_nomination_on_the_wire():
    observed = {}
    for name in ("meshecho-dcb", "meshecho-dcb-source-trigger-f"):
        _, sim, _ = run_arm(name, send_times=(1.0, 5.0), until=7.0)
        ack = next(tx.packet for tx in sim.tx_history
                   if tx.sender == 3 and tx.packet.kind == "ACK"
                   and tx.packet.flow_id == 1)
        data = next(tx.packet for tx in sim.tx_history
                    if tx.sender == 0 and tx.packet.kind == "DATA"
                    and tx.packet.flow_id == 2)
        observed[name] = (
            ack.path, ack.backup_relay_id, ack.wire_size_bytes(32),
            data.path, data.backup_relay_id, data.backup_epoch_id,
            data.wire_size_bytes(32),
        )
    assert observed["meshecho-dcb-source-trigger-f"] == observed["meshecho-dcb"]

    _, sim, metrics = run_arm(
        "meshecho-dcb-source-trigger-f",
        send_times=(1.0, 20.0, 200.0, 205.0), until=208.0,
    )
    ack = next(tx for tx in sim.tx_history
               if tx.sender == 3 and tx.packet.kind == "ACK"
               and tx.packet.flow_id == 3)
    routed = next(tx.packet for tx in sim.tx_history
                  if tx.sender == 0 and tx.packet.kind == "DATA"
                  and tx.packet.flow_id == 4)
    assert ack.start - metrics.flows[3].delivered_at == 2.0
    assert ack.packet.path == (0, 3)
    assert ack.packet.backup_relay_id == 2
    assert ack.packet.wire_size_bytes(32) == 19
    assert routed.path == (0, 3)
    assert routed.backup_relay_id == 2
    assert routed.backup_epoch_id == 3
    assert routed.wire_size_bytes(32) == 55


def test_trigger_f_keeps_dcb_fixed_same_flow_recovery_after_r_miss():
    recovery_starts = {}
    for name in ("meshecho-dcb", "meshecho-dcb-source-trigger-f"):
        _, sim, _ = run_arm(
            name, send_times=(1.0, 5.0), until=22.0,
            sim_type=DropSecondFlowDeliverySimulator,
        )
        initial = next(tx for tx in sim.tx_history
                       if tx.sender == 0 and tx.packet.flow_id == 2
                       and tx.packet.kind == "DATA")
        recoveries = [tx for tx in sim.tx_history
                      if tx.sender == 0 and tx.packet.flow_id == 2
                      and tx.packet.kind == "FLOOD"
                      and tx.packet.repair_index == 2]
        assert len(recoveries) == 1
        assert recoveries[0].start - initial.start == 15.0
        recovery_starts[name] = recoveries[0].start
    assert recovery_starts["meshecho-dcb-source-trigger-f"] == recovery_starts["meshecho-dcb"]
