"""Interactive dashboard generator for multi-session performance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    go = None

from .logging_utils import append_signed_audit


class MultiSessionDashboard:
    """Build interactive dashboards summarizing backtest sessions."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = Path(output_dir or "dashboards")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        sessions: Iterable[Dict[str, object]],
        *,
        session_id: Optional[str] = None,
        audit_log: Optional[Path] = None,
        hmac_key: Optional[str] = None,
    ) -> Dict[str, Path]:
        session_list = list(sessions)
        summary_path = self.output_dir / f"{session_id or 'dashboard'}_summary.json"
        summary_path.write_text(json.dumps(session_list, indent=2, ensure_ascii=False), encoding="utf-8")

        dashboard_path = self.output_dir / f"{session_id or 'dashboard'}_report.html"
        if go is not None and session_list:
            fig = go.Figure()
            for entry in session_list:
                equity = entry.get("equity_curve") or []
                if equity:
                    fig.add_trace(go.Scatter(y=equity, mode="lines", name=str(entry.get("session_id", "session"))))
            fig.update_layout(
                title="Multi-Session Equity Curves",
                xaxis_title="Step",
                yaxis_title="Equity",
            )
            fig.write_html(dashboard_path)
        else:
            dashboard_path.write_text("Interactive visualization unavailable", encoding="utf-8")

        if audit_log is not None:
            append_signed_audit(
                {
                    "module": "qai.dashboard",
                    "event": "render_complete",
                    "session_id": session_id,
                    "summary": str(summary_path),
                    "report": str(dashboard_path),
                },
                audit_log=audit_log,
                session_id=session_id,
                hmac_key=hmac_key,
            )

        return {"summary": summary_path, "report": dashboard_path}
