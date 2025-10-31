import json
from pathlib import Path

from src.qai.backtester import Backtester
from src.qai.metrics_adaptive import AdaptiveMetrics

HMAC_KEY = "unit-hmac-key"


class MetricsAwareStrategy:
    def __init__(self, metrics: AdaptiveMetrics) -> None:
        self.metrics = metrics
        self.sequence = [1, 1, -1, 0]
        self.idx = 0

    def __call__(self, bar):
        if self.idx >= len(self.sequence):
            return 0
        signal = self.sequence[self.idx]
        self.idx += 1
        return signal

    def on_trade_close(self, trade):
        pnl = trade.get("pnl", 0.0)
        stability = 0.9 if pnl >= 0 else 0.4
        self.metrics.update_stability(stability)


def test_adaptive_metrics_logging(tmp_path: Path):
    metrics = AdaptiveMetrics(window=10)
    strategy = MetricsAwareStrategy(metrics)

    prices = [
        {"open": 100.0, "close": 101.0},
        {"open": 101.2, "close": 100.5},
        {"open": 100.4, "close": 100.9},
        {"open": 100.8, "close": 100.7},
    ]

    tester = Backtester(initial_capital=5_000.0, risk_per_trade=0.05)
    audit_path = tmp_path / "metrics.log"

    tester.run(
        prices,
        strategy,
        session_id="adaptive-metrics",
        adaptive_metrics=metrics,
        metrics_audit_log=audit_path,
        metrics_session_id="adaptive-metrics",
        audit_log=tmp_path / "backtester.log",
        hmac_key=HMAC_KEY,
    )

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    events = [e for e in entries if e.get("event") == "adaptive_update"]
    assert events
    event = events[-1]
    assert event["module"] == "qai.metrics"
    assert "metrics" in event
    assert isinstance(event["metrics"]["adaptive_score"], float)
    assert isinstance(event.get("hmac"), str)

    kpis = metrics.compute()
    assert 0.0 <= kpis.stability <= 1.0
    assert kpis.volatility >= 0.0
