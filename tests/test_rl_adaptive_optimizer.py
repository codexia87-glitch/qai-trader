import json
from pathlib import Path

import pytest

from src.qai.backtester import Backtester
from src.qai.rl_adaptive_optimizer import RLAdaptiveOptimizer

HMAC_KEY = "unit-test-hmac"


def test_dynamic_learning_rate_adjustment(tmp_path: Path):
    audit_path = tmp_path / "adaptive.log"
    state_path = tmp_path / "adaptive_state.json"
    optimizer = RLAdaptiveOptimizer(
        input_size=3,
        audit_log=audit_path,
        session_id="adaptive-unit",
        hmac_key=HMAC_KEY,
        memory_path=state_path,
        min_learning_rate=0.05,
        max_learning_rate=0.5,
        smoothing=0.1,
    )
    initial_lr = optimizer.learning_rate

    for _ in range(8):
        optimizer.update([1.0, 0.3, 0.1], 1.2)

    assert optimizer.learning_rate > initial_lr

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    events = [entry["event"] for entry in entries]
    assert "adaptive_init" in events
    assert "adaptive_update" in events


def test_memory_persistence(tmp_path: Path):
    state_path = tmp_path / "adaptive_state.json"
    optimizer = RLAdaptiveOptimizer(input_size=3, memory_path=state_path, smoothing=0.5)
    optimizer.update([0.2, 0.1, -0.4], 0.5)
    optimizer.save_state()

    restored = RLAdaptiveOptimizer(input_size=3, memory_path=state_path, smoothing=0.5)
    summary = restored.memory.summary()
    assert summary["count"] >= 1
    assert restored.learning_rate == pytest.approx(optimizer.learning_rate, rel=1e-6)


def test_backtester_integration_emits_adaptive_updates(tmp_path: Path):
    audit_path = tmp_path / "adaptive.log"
    state_path = tmp_path / "adaptive_state.json"
    optimizer = RLAdaptiveOptimizer(
        input_size=3,
        audit_log=audit_path,
        session_id="adaptive-backtest",
        hmac_key=HMAC_KEY,
        memory_path=state_path,
        smoothing=0.1,
    )

    class SimpleStrategy:
        def __init__(self) -> None:
            self.steps = 0

        def __call__(self, bar: dict) -> int:
            self.steps += 1
            return 1 if self.steps == 1 else -1 if self.steps == 2 else 0

    prices = [
        {"open": 1.0, "close": 1.1},
        {"open": 1.2, "close": 1.3},
        {"open": 1.1, "close": 1.15},
    ]

    backtester = Backtester(initial_capital=1_000.0)
    backtester.run(
        prices,
        SimpleStrategy(),
        adaptive_optimizer=optimizer,
        audit_log=None,
    )

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert any(entry["event"] == "adaptive_update" for entry in entries)
    assert optimizer.memory.summary()["count"] > 0
