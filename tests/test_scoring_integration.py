import json
from pathlib import Path

from src.qai.model_predictor import ModelPredictor

HMAC_KEY = "unit-hmac-key"


def test_scoring_metrics_and_logging(tmp_path: Path):
    predictor = ModelPredictor(input_size=2, hidden_size=4)

    features_batch = [
        [0.2, 0.4],
        [-0.1, -0.2],
        [0.3, 0.6],
    ]
    actual = [0.25, -0.3, 0.5]
    pnl = [10.0, -5.0, 8.0]
    audit_path = tmp_path / "audit.log"

    preds, metrics = predictor.batch_predict(
        features_batch,
        actual=actual,
        pnl=pnl,
        audit_log=audit_path,
        session_id="scoring-test",
        hmac_key=HMAC_KEY,
    )

    assert len(preds) == len(actual)
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 < metrics["stability"] <= 1.0
    assert -1.0 <= metrics["reward"] <= 1.0

    log_entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    scoring_events = [entry for entry in log_entries if entry.get("event") == "evaluate"]
    assert scoring_events
    last = scoring_events[-1]
    assert last["module"] == "qai.scoring"
    assert last["metrics"]["accuracy"] == metrics["accuracy"]
    assert isinstance(last.get("hmac"), str)
