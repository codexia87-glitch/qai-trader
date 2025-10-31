import json
from pathlib import Path

from src.qai.adaptive_strategy import AdaptiveStrategy
from src.qai.datastore import BacktestDatastore
from src.qai.evaluation_pipeline import EvaluationPipeline
from src.qai.experiment_engine import ExperimentEngine

HMAC_KEY = "unit-hmac-key"


def _scenario(session_id: str):
    return {
        "id": session_id,
        "strategy": AdaptiveStrategy(),
        "features": [
            [0.1, 0.2],
            [-0.2, 0.3],
        ],
        "prices": [
            {"open": 100.0, "close": 100.3},
            {"open": 100.2, "close": 99.9},
        ],
        "actual": [0.2, -0.1],
    }


def test_experiment_engine_runs_batch(tmp_path: Path):
    audit_path = tmp_path / "experiments.log"
    datastore = BacktestDatastore(base_dir=tmp_path / "store")
    pipeline = EvaluationPipeline()
    engine = ExperimentEngine(
        pipeline=pipeline,
        output_dir=tmp_path / "experiments",
        datastore=datastore,
    )

    result_paths = engine.run_batch(
        [_scenario("s1"), _scenario("s2")],
        audit_log=audit_path,
        hmac_key=HMAC_KEY,
    )

    summary = Path(result_paths["summary"])
    metrics = Path(result_paths["metrics"])
    assert summary.exists()
    assert metrics.exists()

    data = json.loads(summary.read_text(encoding="utf-8"))
    assert len(data) == 2

    log_entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    events = [entry for entry in log_entries if entry.get("event") == "run_batch_complete"]
    assert events
    assert isinstance(events[-1].get("hmac"), str)

    stored_runs = datastore.list_runs()
    assert "s1" in stored_runs and "s2" in stored_runs
