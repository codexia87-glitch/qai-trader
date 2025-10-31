import json
from pathlib import Path

from src.qai.optimizer import OptimizerRL

HMAC_KEY = "unit-hmac-key"


def test_optimizer_rl_updates_weights_and_logs(tmp_path: Path):
    audit_path = tmp_path / "optimizer.log"
    optimizer = OptimizerRL(
        input_size=3,
        learning_rate=0.2,
        gamma=0.9,
        epsilon=0.2,
        audit_log=audit_path,
        session_id="optimizer-test",
        hmac_key=HMAC_KEY,
    )

    initial = optimizer.policy([0.5, -0.2, 0.1])
    updated = optimizer.train_step([0.5, -0.2, 0.1], reward=1.0)

    assert updated != initial
    assert optimizer.suggest([0.5, -0.2, 0.1]) in (-1, 0, 1)
    assert optimizer.state.epsilon <= 0.2

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries
    assert entries[0]["event"] == "init"
    assert isinstance(entries[0]["hmac"], str)
