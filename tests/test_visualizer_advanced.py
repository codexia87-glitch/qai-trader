import json
from pathlib import Path

import pytest

from src.qai.visualizer_advanced import AdvancedMultiSessionVisualizer

HMAC_KEY = "unit-visualizer-hmac"


def test_visualizer_creates_artifacts_and_audit(tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    visualizer = AdvancedMultiSessionVisualizer(output_dir=tmp_path / "viz")

    sessions = [
        {
            "session_id": "alpha",
            "equity_curve": [1000, 1010, 1025],
            "metrics": {"stability": 0.9},
        },
        {
            "session_id": "beta",
            "equity_curve": [1000, 995, 1005],
            "metrics": {"stability": 0.8},
        },
    ]

    artifacts = visualizer.render(
        sessions,
        session_id="demo",
        audit_log=audit_path,
        hmac_key=HMAC_KEY,
        title="Demo 3D Dashboard",
    )

    assert artifacts.html.exists()
    assert artifacts.json.exists()
    assert artifacts.png.exists()

    html_content = artifacts.html.read_text(encoding="utf-8")
    assert "Multi-Session" in html_content

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert [entry["event"] for entry in entries] == ["render_init", "render_complete"]
    assert entries[-1]["artifacts"]["html"].endswith("demo_dashboard.html")


def test_visualizer_fallback_without_plotly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import src.qai.visualizer_advanced as module

    monkeypatch.setattr(module, "go", None)
    monkeypatch.setattr(module, "write_html", None)
    monkeypatch.setattr(module, "plt", None)

    visualizer = module.AdvancedMultiSessionVisualizer(output_dir=tmp_path / "fallback")

    artifacts = visualizer.render(
        [{"session_id": "fallback", "equity_curve": [1, 2, 3], "metrics": {}}],
        session_id="fallback",
    )

    assert artifacts.html.exists()
    assert artifacts.json.exists()
    assert artifacts.png.exists()
    assert "PNG rendering unavailable" in artifacts.png.read_text(encoding="utf-8")
