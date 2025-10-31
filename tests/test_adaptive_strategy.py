import json
from pathlib import Path

from src.qai.adaptive_strategy import AdaptiveStrategy
from src.qai.backtester import Backtester

HMAC_KEY = "unit-hmac-key"


def test_adaptive_strategy_adjusts_threshold_and_persists(tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    persistence = tmp_path / "adaptive.json"
    strategy = AdaptiveStrategy(
        initial_threshold=0.001,
        learning_rate=0.2,
        persistence_path=persistence,
        audit_log=audit_path,
        session_id="adaptive-test",
        hmac_key=HMAC_KEY,
    )

    backtester = Backtester(initial_capital=1_000.0, risk_per_trade=0.05)
    prices = [
        {"open": 100.0, "close": 100.5},
        {"open": 99.5, "close": 99.0},
        {"open": 99.0, "close": 100.0},
    ]

    result = backtester.run(
        prices,
        strategy,
        session_id="adaptive-session",
        audit_log=audit_path,
        hmac_key=HMAC_KEY,
    )

    assert result.metrics["total_trades"] >= 1
    # ensure threshold adapted
    data = json.loads(persistence.read_text(encoding="utf-8"))
    assert data["threshold"] != 0.001
    assert strategy.state.history

    logs = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    init_events = [entry for entry in logs if entry.get("event") == "adaptive_init"]
    assert init_events
    assert all(isinstance(entry.get("hmac"), str) for entry in init_events)
