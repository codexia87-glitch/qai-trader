"""Built-in strategy primitives for QAI backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

from .model_predictor import ModelPredictor


class StrategyProtocol:
    """Minimal strategy interface returning -1, 0 or 1."""

    def __call__(self, bar: Dict[str, float]) -> int:
        raise NotImplementedError


@dataclass
class ThresholdCrossStrategy(StrategyProtocol):
    """Enter long/short when price crosses configured thresholds."""

    upper: float
    lower: float

    def __post_init__(self) -> None:
        if self.lower >= self.upper:
            raise ValueError("lower threshold must be < upper threshold")

    def __call__(self, bar: Dict[str, float]) -> int:
        price = bar.get("close") or bar.get("open")
        if price is None:
            raise ValueError("bar requires a price-like field (close or open)")
        if price >= self.upper:
            return -1
        if price <= self.lower:
            return 1
        return 0


@dataclass
class PredictorThresholdStrategy(StrategyProtocol):
    """Generate signals from a ModelPredictor using upper/lower score bands."""

    predictor: ModelPredictor
    upper: float = 0.2
    lower: float = -0.2
    audit_log: Optional[Path] = None
    session_id: Optional[str] = None
    hmac_key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.lower >= self.upper:
            raise ValueError("lower threshold must be < upper threshold")

    def _extract_features(self, bar: Dict[str, float]) -> Sequence[float]:
        features = bar.get("features")
        if features is None:
            raise ValueError("bar must include a 'features' sequence for predictor-driven strategy")
        if len(features) != self.predictor.input_size:
            raise ValueError(
                f"Strategy expected {self.predictor.input_size} features, received {len(features)}"
            )
        return features

    def __call__(self, bar: Dict[str, float]) -> int:
        features = self._extract_features(bar)
        prediction = self.predictor.predict(features)
        if self.audit_log:
            self.predictor.audit_prediction(
                features,
                prediction,
                audit_log=self.audit_log,
                session_id=self.session_id,
                hmac_key=self.hmac_key,
            )
        if prediction >= self.upper:
            return 1
        if prediction <= self.lower:
            return -1
        return 0
