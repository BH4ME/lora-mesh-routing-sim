"""Structural/common-environment fixtures; no research seed is exposed here."""
from types import SimpleNamespace

import pytest

from tools import secon2027_scenarios as env


def fixture_spec():
    return dict(model="grid-obstructed-v1", faults=[dict(start_s=90, end_s=180,
        edges=[[7, 8], [12, 13]], attenuation_db=80)])


def test_grid_forces_multihop_and_preserves_fault_detour():
    case = SimpleNamespace(nodes=20, pair_count=4, duration_s=240)
    resolved = env.resolve_environment(case, 92000, fixture_spec())
    for src, dst in resolved["pairs"]:
        assert env.shortest_hops(resolved, src, dst, 0) == 4
        assert env.shortest_hops(resolved, src, dst, 100) == 6
        assert env.shortest_hops(resolved, src, dst, 200) == 4
    assert env.attenuation_db(resolved, 7, 8, 100) - env.attenuation_db(resolved, 7, 8, 89) == 80
    assert env.attenuation_db(resolved, 2, 3, 100) == env.attenuation_db(resolved, 2, 3, 89)


def test_common_channel_is_independent_of_query_order_and_protocol():
    case = SimpleNamespace(nodes=20, pair_count=4, duration_s=240)
    first = env.resolve_environment(case, 92000, fixture_spec())
    second = env.resolve_environment(case, 92000, fixture_spec())
    expected = env.channel_uniform(first, 7, 8, 100)
    for node in range(20):
        env.channel_uniform(first, node, 3, node * 1.13)
    assert env.channel_uniform(first, 7, 8, 100) == expected == env.channel_uniform(second, 7, 8, 100)
    assert first == second
    assert 0 <= expected < 1
    assert env.channel_uniform(first, 8, 7, 100) != expected


def test_environment_rejects_silently_ignored_configuration():
    case = SimpleNamespace(nodes=20, pair_count=4, duration_s=240)
    with pytest.raises(ValueError, match="unknown common environment"):
        env.resolve_environment(case, 92000, {**fixture_spec(), "typo_loss": 20})
    with pytest.raises(ValueError, match="not a grid neighbor"):
        env.resolve_environment(case, 92000, dict(model="grid-obstructed-v1", faults=[
            dict(start_s=90, end_s=180, edges=[[0, 19]], attenuation_db=80)]))


def test_runner_uses_same_exported_environment_and_replays_evidence():
    from tools import run_cpr_experiment as cpr
    case = cpr.CprCase(key="grid_fixture", nodes=4, area_m=2000, duration_s=20,
                       pair_count=2, sf=7, shadow_sigma_db=0)
    specification = dict(model="grid-obstructed-v1", columns=2, rows=2,
                         endpoint_pairs=[[0, 3], [3, 0]])
    first = cpr.run_matrix(case, ("meshecho-cpr", "meshtastic"), (92000,),
                           registry=cpr.EXTERNAL_REGISTRY, environment=specification)
    second = cpr.run_matrix(case, ("meshecho-cpr", "meshtastic"), (92000,),
                            registry=cpr.EXTERNAL_REGISTRY, environment=specification)
    assert first.runs == second.runs
    assert first.transmissions == second.transmissions
    assert first.rx_attempts == second.rx_attempts
    assert first.paired[0]["environment_match"]
    assert first.identities[92000]["common_environment"]["channel_field"] == "sha256-uniform-directed-link-time-bin-v1"
    assert len(first.identities[92000]["application_trace"]) == 2
