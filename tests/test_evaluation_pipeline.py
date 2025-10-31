import json
from pathlib import Path

from src.qai.adaptive_strategy import AdaptiveStrategy
from src.qai.evaluation_pipeline import EvaluationPipeline
from src.qai.visualizer import MultiSessionVisualizer
from src.qai.model_predictor import ModelPredictor

HMAC_KEY = "unit-hmac-key"


def test_evaluation_pipeline_generates_reports(tmp_path: Path):
    predictor = ModelPredictor(input_size=2, hidden_size=4)
    pipeline = EvaluationPipeline(predictor=predictor)

    features = [
        [0.2, 0.4],
        [-0.1, -0.3],
        [0.5, 0.6],
    ]
    prices = [
        {"open": 100.0, "close": 100.5},
        {"open": 100.4, "close": 99.9},
        {"open": 99.8, "close": 100.2},
    ]
    actual = [0.3, -0.2, 0.4]

    audit_path = tmp_path / "audit.log"
    reports_dir = tmp_path / "reports"

    visualizer = MultiSessionVisualizer(output_dir=reports_dir)

    report = pipeline.evaluate(
        strategy=AdaptiveStrategy(),
        features=features,
        prices=prices,
        actual=actual,
        output_dir=reports_dir,
        session_id="pipeline-test",
        audit_log=audit_path,
        hmac_key=HMAC_KEY,
        visualizer=visualizer,
    )

    report_file = reports_dir / "pipeline-test_report.json"
    metrics_file = reports_dir / "pipeline-test_metrics.csv"
    assert report_file.exists()
    assert metrics_file.exists()

    loaded = json.loads(report_file.read_text(encoding="utf-8"))
    assert "scoring" in loaded and "adaptive" in loaded and "backtest" in loaded
    assert report["scoring"]["accuracy"] == loaded["scoring"]["accuracy"]

    log_entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    pipeline_events = [entry for entry in log_entries if entry.get("event") == "evaluation_complete"]
    assert pipeline_events
    last_event = pipeline_events[-1]
    assert last_event["module"] == "qai.pipeline"
    assert last_event["report"]["scoring"]["accuracy"] == report["scoring"]["accuracy"]
    assert isinstance(last_event.get("hmac"), str)

    viz_events = [entry for entry in log_entries if entry.get("event") == "render_complete"]
    assert viz_events
