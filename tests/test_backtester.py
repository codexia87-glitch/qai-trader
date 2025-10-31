import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.qai.backtester import Backtester  # noqa: E402
from src.qai.datastore import BacktestDatastore  # noqa: E402
from src.qai.strategies import ThresholdCrossStrategy  # noqa: E402

HMAC_KEY = "unit-hmac-key"


def test_backtester_generates_trades(tmp_path: Path):
    prices = [
        {"open": 100.0, "close": 101.0},
        {"open": 102.0, "close": 103.0},
        {"open": 104.0, "close": 103.5},
        {"open": 103.0, "close": 102.0},
    ]

    audit_path = tmp_path / "audit.log"
    datastore = BacktestDatastore(base_dir=tmp_path / "store")
    strategy = ThresholdCrossStrategy(upper=103.5, lower=101.0)

    tester = Backtester(initial_capital=1000.0, risk_per_trade=0.05)
    result = tester.run(
        prices,
        strategy,
        session_id="test-session",
        audit_log=audit_path,
        datastore=datastore,
        metadata={"note": "unit-test"},
        hmac_key=HMAC_KEY,
    )

    summary = result.summarize()
    assert summary["total_trades"] >= 1
    assert isinstance(summary["net_return"], float)
    assert summary["max_drawdown"] >= 0
    assert "avg_trade_pnl" in summary
    assert audit_path.exists()

    stored = datastore.load_run("test-session")
    assert stored["metadata"]["note"] == "unit-test"
    assert stored["result"]["summary"]["total_trades"] == summary["total_trades"]

    # ensure audit entry has expected fields
    content = audit_path.read_text(encoding="utf-8").strip()
    assert content
    entry = json.loads(content.splitlines()[-1])
    assert entry["module"] == "qai.backtester"
    assert entry["session_id"] == "test-session"
    assert "datastore_path" in entry
    assert isinstance(entry["hmac"], str)


def test_backtester_invalid_signal_raises():
    prices = [{"open": 1.0, "close": 1.1}]

    def bad_strategy(_):
        return 2

    tester = Backtester()
    with pytest.raises(ValueError):
        tester.run(prices, bad_strategy)
