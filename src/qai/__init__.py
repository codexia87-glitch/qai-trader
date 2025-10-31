"""QAI Trader predictive and backtesting utilities package."""

from __future__ import annotations

__all__ = [
    "Backtester",
    "BacktestResult",
    "BacktestDatastore",
    "BacktestSimulator",
    "ModelPredictor",
    "MultiSessionReport",
    "HMACFailure",
    "PredictorThresholdStrategy",
    "AdaptiveStrategy",
    "ScoreEvaluator",
    "AdaptiveMetrics",
    "AdaptiveKPIs",
    "ThresholdCrossStrategy",
]

try:
    from .backtester import Backtester, BacktestResult
    from .datastore import BacktestDatastore
    from .simulator import BacktestSimulator, MultiSessionReport
    from .strategies import ThresholdCrossStrategy, PredictorThresholdStrategy
    from .model_predictor import ModelPredictor
    from .hmac_utils import HMACFailure
    from .adaptive_strategy import AdaptiveStrategy
    from .scoring import ScoreEvaluator
    from .metrics_adaptive import AdaptiveMetrics, AdaptiveKPIs
except ImportError:  # pragma: no cover - modules may not be ready during stub generation
    Backtester = BacktestResult = BacktestDatastore = BacktestSimulator = ThresholdCrossStrategy = PredictorThresholdStrategy = MultiSessionReport = ModelPredictor = HMACFailure = AdaptiveStrategy = ScoreEvaluator = AdaptiveMetrics = AdaptiveKPIs = None  # type: ignore
