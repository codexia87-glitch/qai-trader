import json
import sys
import logging
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.qai.backtester import Backtester  # noqa: E402
from src.qai.datastore import BacktestDatastore  # noqa: E402
from src.qai.model_predictor import ModelPredictor  # noqa: E402
from src.qai.simulator import BacktestSimulator  # noqa: E402
from src.qai.strategies import (  # noqa: E402
    PredictorThresholdStrategy,
    ThresholdCrossStrategy,
)

HMAC_KEY = "unit-hmac-key"


@pytest.mark.parametrize("upper,lower", [(0.15, -0.15)])
def test_multisession_simulator_generates_summary(tmp_path: Path, caplog, upper: float, lower: float):
    caplog.set_level(logging.INFO, logger="src.qai.simulator")

    datastore = BacktestDatastore(base_dir=tmp_path / "store")
    audit_path = tmp_path / "audit.log"

    backtester = Backtester(initial_capital=1_000.0, risk_per_trade=0.05)
    predictor = ModelPredictor(input_size=2, hidden_size=4)

    prices_a = [
        {"open": 100.0, "close": 101.0, "features": [0.2, 0.4]},
        {"open": 101.0, "close": 100.5, "features": [-0.1, -0.2]},
        {"open": 100.3, "close": 101.2, "features": [0.3, 0.7]},
    ]
    prices_b = [
        {"open": 99.0, "close": 100.1},
        {"open": 100.5, "close": 100.9},
        {"open": 101.0, "close": 99.8},
    ]

    simulator = BacktestSimulator(
        backtester=backtester,
        datastore=datastore,
        audit_log=audit_path,
        hmac_key=HMAC_KEY,
    )

    sessions = [
        {
            "session_id": "session-a",
            "prices": prices_a,
            "strategy": PredictorThresholdStrategy(
                predictor=predictor,
                upper=upper,
                lower=lower,
                audit_log=audit_path,
                session_id="session-a-predictor",
                hmac_key=HMAC_KEY,
            ),
            "metadata": {"tag": "alpha"},
        },
        {
            "session_id": "session-b",
            "prices": prices_b,
            "strategy": ThresholdCrossStrategy(upper=101.0, lower=99.5),
            "metadata": {"tag": "beta"},
        },
    ]

    report = simulator.run_sessions(sessions, summary_name="unit_test_summary")

    assert report.aggregate["sessions"] == 2
    assert report.aggregate["total_trades"] >= 1
    assert report.aggregate["best_session"] in {"session-a", "session-b"}
    assert report.summary_path is not None
    assert report.summary_path.exists()

    summary_payload = json.loads(report.summary_path.read_text(encoding="utf-8"))
    assert "aggregate" in summary_payload
    assert "session-a" in summary_payload["sessions"]

    structured_logs = []
    for record in caplog.records:
        try:
            structured_logs.append(json.loads(record.message))
        except json.JSONDecodeError:
            continue
    assert any(log.get("type") == "backtest.session.summary" for log in structured_logs)
    assert any(log.get("type") == "backtest.multisession.summary" for log in structured_logs)

    audit_lines = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sim_entries = [entry for entry in audit_lines if entry.get("module") == "qai.simulator"]
    assert sim_entries
    assert all(isinstance(entry.get("hmac"), str) for entry in sim_entries)
