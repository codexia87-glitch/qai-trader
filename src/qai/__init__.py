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
    "EvaluationPipeline",
    "OptimizerRL",
    "MultiSessionVisualizer",
    "ExperimentEngine",
    "RLContinuousAgent",
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
    from .evaluation_pipeline import EvaluationPipeline
    from .optimizer import OptimizerRL
    from .visualizer import MultiSessionVisualizer
    from .experiment_engine import ExperimentEngine
    from .rl_continuous import RLContinuousAgent
except ImportError:  # pragma: no cover - modules may not be ready during stub generation
    Backtester = BacktestResult = BacktestDatastore = BacktestSimulator = ThresholdCrossStrategy = PredictorThresholdStrategy = MultiSessionReport = ModelPredictor = HMACFailure = AdaptiveStrategy = ScoreEvaluator = AdaptiveMetrics = AdaptiveKPIs = EvaluationPipeline = OptimizerRL = MultiSessionVisualizer = ExperimentEngine = RLContinuousAgent = None  # type: ignore
