"""QAI Trader predictive and backtesting utilities package."""

from __future__ import annotations

__all__ = [
    "Backtester",
    "BacktestResult",
    "ModelPredictor",
]

try:
    from .backtester import Backtester, BacktestResult
    from .model_predictor import ModelPredictor
except ImportError:  # pragma: no cover - modules may not be ready during stub generation
    Backtester = BacktestResult = ModelPredictor = None  # type: ignore
