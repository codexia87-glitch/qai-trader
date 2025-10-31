import json
from pathlib import Path

from src.qai.dashboard import MultiSessionDashboard

HMAC_KEY = "unit-hmac-key"


def test_dashboard_generates_html_and_logs(tmp_path: Path):
    audit_path = tmp_path / "dashboard.log"
    dashboard = MultiSessionDashboard(output_dir=tmp_path / "dashboards")

    sessions = [
        {
            "session_id": "d1",
            "equity_curve": [100, 101, 99],
            "metrics": {"net_return": 0.01},
        }
    ]

    paths = dashboard.render(
        sessions,
        session_id="dashboard-test",
        audit_log=audit_path,
        hmac_key=HMAC_KEY,
    )

    summary = Path(paths["summary"])
    report = Path(paths["report"])
    assert summary.exists()
    assert report.exists()

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries
    assert entries[-1]["event"] == "render_complete"
    assert isinstance(entries[-1].get("hmac"), str)
