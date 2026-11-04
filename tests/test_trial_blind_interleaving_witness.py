"""Public same-pair witness for the trial versus blind route decision."""

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol


class PrimaryErasureTrace(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        previous = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > previous:
            self.tx_history.append(self.transmissions[-1])

    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                and tx.packet.repair_index is None
                and tx.sender == 0 and receiver == 3):
            return None
        return super().try_receive(tx, receiver)


def first_source_data(sim, flow_id):
    return next(
        tx for tx in sim.tx_history
        if tx.sender == 0 and tx.packet.origin == 0
        and tx.packet.flow_id == flow_id and tx.packet.kind == "DATA"
        and tx.packet.repair_index is None
    )


def physical_signature(tx):
    packet = tx.packet
    return (
        tx.sender, packet.kind, packet.path, packet.repair_index,
        packet.backup_relay_id, packet.backup_epoch_id,
        packet.wire_size_bytes(32),
    )


def test_public_same_pair_interleaving_exposes_trial_blind_path_difference():
    observed = {}
    for arm in (
        "meshecho-dcb-trial",
        "meshecho-dcb-trial-blind",
        "meshecho-dcb-trial-no-switch",
    ):
        protocol = build_protocol(arm)
        protocol.flood_base_delay_s = 0.5
        protocol.flood_jitter_s = 0.0
        sim = PrimaryErasureTrace(
            [Node(node_id, node_id * 10.0, 0.0) for node_id in range(4)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for flow_id, when in enumerate((1.0, 5.0, 10.0, 10.01), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))
        metrics = sim.run(12.0)
        decisions = {
            event["flow_id"]: event for event in protocol.action_events
            if event["event"] == "decision"
        }
        third = first_source_data(sim, 3)
        fourth = first_source_data(sim, 4)
        assert any(
            event["event"] == "dcb_source_ack_rx"
            and event["flow_id"] == 2 and event["accepted"]
            for event in protocol.action_events
        )
        assert third.start < decisions[4]["time"] < third.start + 15.0
        assert third.start < fourth.start < third.start + 15.0
        if arm != "meshecho-dcb-trial-no-switch":
            assert metrics.flows[3].acked_at is not None
            assert decisions[4]["time"] < fourth.start < metrics.flows[3].acked_at
        observed[arm] = {
            "decisions": decisions,
            "third": physical_signature(third),
            "fourth": physical_signature(fourth),
        }

    trial = observed["meshecho-dcb-trial"]
    blind = observed["meshecho-dcb-trial-blind"]
    no_switch = observed["meshecho-dcb-trial-no-switch"]
    assert trial["decisions"][3]["reason"] == "ack-proven-trial"
    assert trial["third"] == blind["third"]
    assert trial["third"][2] == (0, 2, 3)
    assert no_switch["third"][2] == (0, 3)
    assert all(run["decisions"][4]["action"] == "R" for run in observed.values())
    assert trial["fourth"] == no_switch["fourth"]
    assert trial["fourth"][2] == (0, 3)
    assert blind["fourth"][2] == (0, 2, 3)
