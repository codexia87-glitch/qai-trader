import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.qai.backtester import Backtester  # noqa: E402
from src.qai.datastore import BacktestDatastore  # noqa: E402
from src.qai.model_predictor import ModelPredictor  # noqa: E402
from src.qai.strategies import PredictorThresholdStrategy  # noqa: E402

HMAC_KEY = "unit-hmac-key"


@pytest.mark.parametrize("upper,lower", [(0.2, -0.2)])
def test_predictor_strategy_generates_signals(tmp_path: Path, upper: float, lower: float):
    prices = [
        {"open": 100.0, "close": 101.0, "features": [0.1, 0.5]},
        {"open": 101.5, "close": 101.2, "features": [-0.1, -0.5]},
        {"open": 99.5, "close": 100.2, "features": [0.4, 0.8]},
        {"open": 100.1, "close": 99.9, "features": [-0.4, -0.9]},
    ]

    predictor = ModelPredictor(input_size=2, hidden_size=4)
    audit_path = tmp_path / "audit.log"
    datastore = BacktestDatastore(base_dir=tmp_path / "store")

    strategy = PredictorThresholdStrategy(
        predictor=predictor,
        upper=upper,
        lower=lower,
        audit_log=audit_path,
        session_id="predictor-test",
        hmac_key=HMAC_KEY,
    )

    backtester = Backtester(initial_capital=1_000.0, risk_per_trade=0.1)
    result = backtester.run(
        prices,
        strategy,
        session_id="predictor-backtest",
        audit_log=audit_path,
        datastore=datastore,
        hmac_key=HMAC_KEY,
    )

    assert len(result.trades) >= 1
    stored = datastore.load_run("predictor-backtest")
    assert stored["result"]["summary"]["total_trades"] == len(result.trades)

    # Predictor should have appended audit entries along with backtester summary
    logs = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    predictor_events = [entry for entry in logs if entry.get("module") == "qai.model_predictor"]
    assert predictor_events, "Expected predictor audit entries"
    assert all(isinstance(entry.get("hmac"), str) for entry in predictor_events)
    assert logs[-1]["module"] == "qai.backtester"
