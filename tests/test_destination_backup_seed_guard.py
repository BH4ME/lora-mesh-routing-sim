"""Reserved backup-screen seeds require a staged passive diagnostic."""

import pytest

from tools import run_sr_experiment as sr
from tools import run_destination_backup_screen as backup


@pytest.mark.parametrize("seed", (46000, 46001, 46020, 46000.0))
@pytest.mark.parametrize("protocol", (
    "meshecho-dhr-flood-ack-delay", "meshtastic-like",
))
def test_generic_runner_rejects_backup_screen_seed_before_topology(
    monkeypatch, seed, protocol,
):
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )

    with pytest.raises(ValueError, match="backup.*reserved seed"):
        sr.run_one_sr(sr.SR_CASES["recurring_fading"], protocol, seed, 30.0)


def test_imported_token_and_invalid_permit_cannot_start_backup_seed(
    tmp_path, monkeypatch,
):
    permit = tmp_path / "invalid.authorization.json"
    permit.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )

    with pytest.raises(ValueError, match="authorization"):
        sr.run_one_sr(
            sr.SR_CASES["recurring_fading"], backup.PROTOCOL, 46000, 30.0,
            research_authorization=backup._RUNNER_AUTHORIZATION,
        )
    with pytest.raises(ValueError, match="authorization"):
        sr.run_one_sr(
            sr.SR_CASES["recurring_fading"], backup.PROTOCOL, 46000, 30.0,
            research_authorization=backup._RUNNER_AUTHORIZATION,
            stage_authorization_path=permit,
        )
