"""Test the public matched D-trigger intervention hook."""

from __future__ import annotations

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


def _run(protocol, flow_override=None):
    if flow_override is not None:
        protocol.source_action_overrides = {3: flow_override}
        protocol.equalize_forced_discovery = True
    sim = TraceSimulator(
        [Node(i, i * 10.0, 0.0) for i in range(4)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=6, independent_random_streams=True,
    )
    for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
        sim.schedule(when, "app_send", (0, 3, flow_id))
    sim.run(240.0)
    return sim, protocol


def test_matched_override_forces_target_action_and_equalizes_d_ledger():
    sim, protocol = _run(build_protocol("meshecho-dcb"), "F")

    decision = next(
        event for event in protocol.action_events
        if event.get("event") == "decision" and event.get("flow_id") == 3
    )
    assert decision["action"] == "F"
    assert decision["reason"] == "matched-override-F"
    state = protocol.destination_state[(0, 3)]
    assert state.last_discovery_at == 200.0
    assert protocol.source_tokens[0] == 0
    target_source = [
        tx.packet.kind for tx in sim.tx_history
        if tx.sender == 0 and tx.packet.flow_id == 3
        and tx.packet.repair_index is None
    ]
    assert target_source == ["FLOOD"]


def test_without_override_old_dcb_decision_is_unchanged():
    _, protocol = _run(build_protocol("meshecho-dcb"))
    decisions = [
        event["action"] for event in protocol.action_events
        if event.get("event") == "decision"
    ]
    assert decisions == ["F", "R", "D"]
