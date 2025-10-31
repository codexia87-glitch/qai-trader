"""Multi-session visualization utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None

from .logging_utils import append_signed_audit


class MultiSessionVisualizer:
    """Render equity curves and KPIs for multiple backtest sessions."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = Path(output_dir or "reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        sessions: Iterable[Dict[str, object]],
        *,
        session_id: Optional[str] = None,
        audit_log: Optional[Path] = None,
        hmac_key: Optional[str] = None,
    ) -> Dict[str, object]:
        data: List[Dict[str, object]] = []
        for session in sessions:
            data.append(dict(session))

        summary_path = self.output_dir / f"{session_id or 'multisession'}_visual_summary.json"
        summary_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        image_path = self.output_dir / f"{session_id or 'multisession'}_equity.png"
        if plt is not None:
            fig, ax = plt.subplots(figsize=(6, 3))
            for entry in data:
                equity = entry.get("equity_curve") or []
                if equity:
                    ax.plot(equity, label=entry.get("session_id", "session"))
            ax.set_title("Equity Curves")
            ax.set_xlabel("Step")
            ax.set_ylabel("Equity")
            if data:
                ax.legend(loc="best")
            fig.tight_layout()
            fig.savefig(image_path, dpi=120)
            plt.close(fig)
        else:
            image_path.write_text("matplotlib unavailable", encoding="utf-8")

        if audit_log is not None:
            append_signed_audit(
                {
                    "module": "qai.visualizer",
                    "event": "render_complete",
                    "session_id": session_id,
                    "summary": str(summary_path),
                    "image": str(image_path),
                },
                audit_log=audit_log,
                session_id=session_id,
                hmac_key=hmac_key,
            )

        return {
            "summary": summary_path,
            "image": image_path,
        }
