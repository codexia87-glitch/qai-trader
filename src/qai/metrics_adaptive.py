"""Adaptive KPI utilities for backtesting sessions."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Deque, Dict, Iterable, List, Optional
from collections import deque

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

from .logging_utils import append_signed_audit


@dataclass
class AdaptiveKPIs:
    stability: float
    volatility: float
    adaptive_score: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "stability": self.stability,
            "volatility": self.volatility,
            "adaptive_score": self.adaptive_score,
        }


class AdaptiveMetrics:
    """Track predictor stability and PnL volatility to derive adaptive KPIs."""

    def __init__(self, window: int = 20) -> None:
        self.window = window
        self._stability: Deque[float] = deque(maxlen=window)
        self._equity: List[float] = []

    def update_stability(self, value: float) -> None:
        self._stability.append(float(value))

    def record_equity(self, value: float) -> None:
        self._equity.append(float(value))

    def compute(self) -> AdaptiveKPIs:
        stability = self._average_stability()
        volatility = self._equity_volatility()
        adaptive_score = stability / (1.0 + volatility)
        return AdaptiveKPIs(stability=stability, volatility=volatility, adaptive_score=adaptive_score)

    def _average_stability(self) -> float:
        if not self._stability:
            return 0.0
        if np is not None:
            return float(np.mean(np.asarray(self._stability, dtype=float)))
        return sum(self._stability) / len(self._stability)

    def _equity_volatility(self) -> float:
        if len(self._equity) < 2:
            return 0.0
        if np is not None:
            diffs = np.diff(np.asarray(self._equity, dtype=float))
            return float(np.std(diffs, dtype=float))
        diffs = [self._equity[i] - self._equity[i - 1] for i in range(1, len(self._equity))]
        mean = sum(diffs) / len(diffs)
        variance = sum((x - mean) ** 2 for x in diffs) / len(diffs)
        return sqrt(variance)

    def log_update(
        self,
        audit_log,
        *,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
    ) -> AdaptiveKPIs:
        kpis = self.compute()
        append_signed_audit(
            {
                "module": "qai.metrics",
                "event": "adaptive_update",
                "metrics": kpis.to_dict(),
                "session_id": session_id,
            },
            audit_log=audit_log,
            session_id=session_id,
            hmac_key=hmac_key,
        )
        return kpis
