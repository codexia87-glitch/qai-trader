"""Advanced multi-session visualization with 3D dashboards."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

try:  # pragma: no cover - optional dependency
    import plotly.graph_objects as go  # type: ignore
    from plotly.io import write_html  # type: ignore
except Exception:  # pragma: no cover
    go = None  # type: ignore
    write_html = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
except Exception:  # pragma: no cover
    plt = None  # type: ignore

from .logging_utils import append_signed_audit


@dataclass
class VisualizationArtifacts:
    """Container describing exported visualization assets."""

    html: Path
    json: Path
    png: Path

    def to_dict(self) -> Dict[str, str]:
        return {"html": str(self.html), "json": str(self.json), "png": str(self.png)}


class AdvancedMultiSessionVisualizer:
    """Render interactive 3D dashboards with signed audit events."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = Path(output_dir or "reports/visualizer3d")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        sessions: Iterable[Dict[str, object]],
        *,
        session_id: Optional[str] = None,
        audit_log: Optional[Path] = None,
        hmac_key: Optional[str] = None,
        title: Optional[str] = None,
    ) -> VisualizationArtifacts:
        normalized = self._normalize_sessions(sessions)
        run_id = session_id or "multisession3d"

        html_path = self.output_dir / f"{run_id}_dashboard.html"
        json_path = self.output_dir / f"{run_id}_summary.json"
        png_path = self.output_dir / f"{run_id}_snapshot.png"

        self._log_event(
            "render_init",
            audit_log=audit_log,
            hmac_key=hmac_key,
            payload={
                "session_id": session_id,
                "count": len(normalized),
                "title": title or "Multi-Session 3D Visualization",
            },
        )

        summary = {
            "sessions": normalized,
            "aggregates": self._aggregate_metrics(normalized),
        }
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

        figure = self._build_plotly_figure(normalized, title=title)
        html_created = self._write_html(html_path, figure, summary)
        png_created = self._write_png(png_path, figure, normalized, title)

        artifacts = VisualizationArtifacts(html=html_path, json=json_path, png=png_path)

        self._log_event(
            "render_complete",
            audit_log=audit_log,
            hmac_key=hmac_key,
            payload={
                "session_id": session_id,
                "artifacts": artifacts.to_dict(),
                "plotly": bool(figure is not None and go is not None and html_created),
                "png_created": png_created,
            },
        )

        return artifacts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_sessions(self, sessions: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
        normalized: List[Dict[str, object]] = []
        for index, session in enumerate(sessions):
            entry = dict(session)
            entry.setdefault("session_id", f"session-{index + 1}")
            equity = entry.get("equity_curve") or []
            entry["equity_curve"] = [float(x) for x in equity] if isinstance(equity, Sequence) else []
            metrics = entry.get("metrics") or {}
            entry["metrics"] = metrics
            normalized.append(entry)
        return normalized

    def _aggregate_metrics(self, sessions: List[Dict[str, object]]) -> Dict[str, float]:
        if not sessions:
            return {"avg_final_equity": 0.0, "avg_equity_points": 0.0}
        endings: List[float] = []
        counts: List[int] = []
        for session in sessions:
            equity_curve = session.get("equity_curve") or []
            if equity_curve:
                endings.append(float(equity_curve[-1]))
                counts.append(len(equity_curve))
        avg_final = sum(endings) / len(endings) if endings else 0.0
        avg_points = sum(counts) / len(counts) if counts else 0.0
        return {
            "avg_final_equity": avg_final,
            "avg_equity_points": avg_points,
        }

    def _build_plotly_figure(
        self,
        sessions: List[Dict[str, object]],
        *,
        title: Optional[str],
    ):
        if go is None:  # pragma: no cover - fallback path
            return None
        fig = go.Figure()
        for idx, session in enumerate(sessions):
            equity_curve = session.get("equity_curve") or []
            if not equity_curve:
                continue
            x_axis = list(range(len(equity_curve)))
            y_axis = [idx] * len(equity_curve)
            fig.add_trace(
                go.Scatter3d(
                    x=x_axis,
                    y=y_axis,
                    z=equity_curve,
                    mode="lines",
                    name=str(session.get("session_id")),
                )
            )
        fig.update_layout(
            title=title or "Multi-Session Equity Surface",
            scene=dict(
                xaxis_title="Step",
                yaxis_title="Session Index",
                zaxis_title="Equity",
            ),
            template="plotly_white",
            legend=dict(orientation="h"),
        )
        return fig

    def _write_html(self, path: Path, figure, summary: Dict[str, object]) -> bool:
        if figure is not None and write_html is not None:
            try:  # pragma: no cover - external dependency
                write_html(figure, str(path), include_plotlyjs="cdn", full_html=True)
                return True
            except Exception:
                pass
        # Fallback HTML
        lines = [
            "<html><head><title>Multi-Session Visualization</title></head>",
            "<body>",
            "<h1>Multi-Session Visualization (Fallback)</h1>",
            "<pre>",
            json.dumps(summary, indent=2, ensure_ascii=False),
            "</pre>",
            "</body></html>",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return False

    def _write_png(
        self,
        path: Path,
        figure,
        sessions: List[Dict[str, object]],
        title: Optional[str],
    ) -> bool:
        if figure is not None and hasattr(figure, "write_image"):
            try:  # pragma: no cover - requires kaleido
                figure.write_image(str(path), width=1024, height=640)
                return True
            except Exception:
                pass
        if plt is None:  # pragma: no cover - fallback path
            path.write_text("PNG rendering unavailable", encoding="utf-8")
            return False

        fig = plt.figure(figsize=(6, 4))
        ax = fig.add_subplot(111, projection="3d")
        for idx, session in enumerate(sessions):
            equity_curve = session.get("equity_curve") or []
            if not equity_curve:
                continue
            steps = list(range(len(equity_curve)))
            indices = [idx] * len(equity_curve)
            ax.plot(steps, indices, equity_curve, label=str(session.get("session_id")))
        ax.set_title(title or "Multi-Session Equity (3D)")
        ax.set_xlabel("Step")
        ax.set_ylabel("Session")
        ax.set_zlabel("Equity")
        if sessions:
            ax.legend(loc="best")
        fig.tight_layout()
        fig.savefig(path, dpi=140)
        plt.close(fig)
        return True

    def _log_event(
        self,
        event: str,
        *,
        audit_log: Optional[Path],
        hmac_key: Optional[str],
        payload: Dict[str, object],
    ) -> None:
        if audit_log is None:
            return
        entry = {"module": "qai.visualizer3d", "event": event}
        entry.update(payload)
        append_signed_audit(entry, audit_log=audit_log, hmac_key=hmac_key, session_id=payload.get("session_id"))
