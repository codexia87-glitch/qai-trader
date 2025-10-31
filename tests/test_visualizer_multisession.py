import json
from pathlib import Path

from src.qai.visualizer import MultiSessionVisualizer

HMAC_KEY = "unit-hmac-key"


def test_multisession_visualizer_outputs(tmp_path: Path):
    audit_path = tmp_path / "visualizer.log"
    visualizer = MultiSessionVisualizer(output_dir=tmp_path / "reports")

    sessions = [
        {
            "session_id": "s1",
            "equity_curve": [100, 102, 101],
            "metrics": {"stability": 0.8},
        },
        {
            "session_id": "s2",
            "equity_curve": [100, 99, 103],
            "metrics": {"stability": 0.6},
        },
    ]

    paths = visualizer.render(
        sessions,
        session_id="viz-test",
        audit_log=audit_path,
        hmac_key=HMAC_KEY,
    )

    summary = Path(paths["summary"])
    image = Path(paths["image"])
    assert summary.exists()
    assert image.exists()

    data = json.loads(summary.read_text(encoding="utf-8"))
    assert len(data) == 2

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries and entries[-1]["event"] == "render_complete"
    assert isinstance(entries[-1].get("hmac"), str)
