import json
from pathlib import Path

from src.qai.optimizer import OptimizerRL
from src.qai.rl_continuous import RLContinuousAgent

HMAC_KEY = "unit-hmac-key"


def test_rl_continuous_persistence_and_logging(tmp_path: Path):
    state_path = tmp_path / "state.json"
    replay_path = tmp_path / "replay.json"
    audit_path = tmp_path / "rl.log"

    optimizer = OptimizerRL(3, audit_log=audit_path, session_id="rl-test", hmac_key=HMAC_KEY)
    agent = RLContinuousAgent(
        input_size=3,
        state_path=state_path,
        replay_path=replay_path,
        audit_log=audit_path,
        session_id="rl-test",
        hmac_key=HMAC_KEY,
        optimizer=optimizer,
    )

    agent.append_experience([1.0, 0.5, 0.2], 1.0)
    agent.append_experience([-0.5, 0.1, -0.2], -0.5)
    metrics = agent.end_episode()
    agent.save_state()

    assert metrics["updates"] >= 1
    assert state_path.exists()
    assert replay_path.exists()

    agent2 = RLContinuousAgent(
        input_size=3,
        state_path=state_path,
        replay_path=replay_path,
        audit_log=audit_path,
        session_id="rl-test-2",
        hmac_key=HMAC_KEY,
    )
    assert len(agent2.replay_snapshot()) >= 1

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    events = [entry["event"] for entry in entries]
    assert "continuous_init" in events
    assert "continuous_update" in events
    assert all(isinstance(entry.get("hmac"), str) for entry in entries if entry.get("event") in {"continuous_init", "continuous_update"})
