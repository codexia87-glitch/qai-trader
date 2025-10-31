"""Temporary backtesting datastore for persisting run artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BacktestDatastore:
    """Persist backtest inputs/outputs to JSON files for later analysis."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir or PROJECT_ROOT / "var" / "backtests")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        if not session_id:
            raise ValueError("session_id is required to persist backtests")
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in session_id)
        return self.base_dir / f"{safe}.json"

    def save_run(
        self,
        session_id: str,
        *,
        prices: Sequence[Dict[str, Any]],
        result: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Persist result + raw prices to disk and return the path written."""
        path = self._session_path(session_id)

        data: Dict[str, Any] = {
            "session_id": session_id,
            "prices": list(prices),
            "metadata": metadata or {},
        }

        if hasattr(result, "summarize"):
            summary = result.summarize()
            data["result"] = {
                "summary": summary,
                "trades": getattr(result, "trades", []),
                "equity_curve": getattr(result, "equity_curve", []),
            }
        elif is_dataclass(result):
            data["result"] = asdict(result)
        else:
            data["result"] = result

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_run(self, session_id: str) -> Dict[str, Any]:
        """Load a previously stored run."""
        path = self._session_path(session_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def save_summary(self, name: str, summary: Dict[str, Any]) -> Path:
        """Persist an aggregate summary payload."""
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)
        path = self.base_dir / f"{safe}_summary.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_runs(self) -> Sequence[str]:
        """Return available session identifiers."""
        return [
            p.stem
            for p in sorted(self.base_dir.glob("*.json"))
        ]
