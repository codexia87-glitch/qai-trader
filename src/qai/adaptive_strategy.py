"""Adaptive trading strategy that adjusts thresholds based on recent performance."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .logging_utils import append_signed_audit
from .strategies import StrategyProtocol


@dataclass
class AdaptiveState:
    threshold: float = 0.001
    learning_rate: float = 0.25
    min_threshold: float = 0.0005
    max_threshold: float = 0.01
    history: List[float] = field(default_factory=list)


class AdaptiveStrategy(StrategyProtocol):
    """Momentum-based strategy that adapts its threshold after each trade."""

    def __init__(
        self,
        *,
        initial_threshold: float = 0.001,
        learning_rate: float = 0.25,
        min_threshold: float = 0.0005,
        max_threshold: float = 0.01,
        persistence_path: Optional[Path] = None,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
    ) -> None:
        if not 0 < min_threshold <= max_threshold:
            raise ValueError("min_threshold must be > 0 and <= max_threshold")
        if not 0 < learning_rate <= 1:
            raise ValueError("learning_rate must be between 0 and 1")
        self.state = AdaptiveState(
            threshold=initial_threshold,
            learning_rate=learning_rate,
            min_threshold=min_threshold,
            max_threshold=max_threshold,
        )
        self.persistence_path = persistence_path
        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key
        if self.persistence_path and self.persistence_path.exists():
            self._load_state()
        if self.audit_log:
            append_signed_audit(
                {
                    "module": "qai.strategy",
                    "event": "adaptive_init",
                    "session_id": self.session_id,
                    "threshold": self.state.threshold,
                    "learning_rate": learning_rate,
                },
                audit_log=self.audit_log,
                session_id=self.session_id,
                hmac_key=self.hmac_key,
            )

    def __call__(self, bar: Dict[str, float]) -> int:
        open_price = bar.get("open")
        close_price = bar.get("close")
        if open_price is None or close_price is None:
            raise ValueError("AdaptiveStrategy requires 'open' and 'close' prices")
        momentum = (close_price - open_price) / max(open_price, 1e-9)
        threshold = self.state.threshold
        if momentum > threshold:
            return 1
        if momentum < -threshold:
            return -1
        return 0

    # Hooks consumed by Backtester
    def on_trade_close(self, trade: Dict[str, float]) -> None:
        pnl = float(trade.get("pnl", 0.0))
        self.state.history.append(pnl)
        # keep only last 20 trades
        if len(self.state.history) > 20:
            self.state.history = self.state.history[-20:]
        direction = 1 if pnl > 0 else -1 if pnl < 0 else 0
        adjustment = self.state.learning_rate * (abs(pnl) / max(abs(trade.get("entry", 1.0)), 1e-6))
        if direction > 0:
            self.state.threshold = max(
                self.state.min_threshold,
                self.state.threshold * (1 - adjustment),
            )
        elif direction < 0:
            self.state.threshold = min(
                self.state.max_threshold,
                self.state.threshold * (1 + adjustment),
            )
        self._persist_state()

    def on_session_end(self) -> None:
        self._persist_state()

    # Persistence helpers
    def _persist_state(self) -> None:
        if not self.persistence_path:
            return
        payload = {
            "threshold": self.state.threshold,
            "learning_rate": self.state.learning_rate,
            "min_threshold": self.state.min_threshold,
            "max_threshold": self.state.max_threshold,
            "history": self.state.history,
        }
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        self.persistence_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_state(self) -> None:
        try:
            data = json.loads(self.persistence_path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.state.threshold = float(data.get("threshold", self.state.threshold))
        self.state.learning_rate = float(data.get("learning_rate", self.state.learning_rate))
        self.state.min_threshold = float(data.get("min_threshold", self.state.min_threshold))
        self.state.max_threshold = float(data.get("max_threshold", self.state.max_threshold))
        history = data.get("history") or []
        if isinstance(history, list):
            self.state.history = [float(x) for x in history][-20:]
