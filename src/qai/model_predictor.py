"""Predictive model scaffolding for QAI Trader."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None
    nn = None

from .logging_utils import append_signed_audit
from .scoring import ScoreEvaluator


logger = logging.getLogger(__name__)


class ModelPredictor:
    """Wrapper around a simple feed-forward network used for signal inference."""

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 32,
        checkpoint_path: Optional[Path] = None,
    ) -> None:
        if input_size <= 0:
            raise ValueError("input_size must be positive")
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.checkpoint_path = checkpoint_path
        self._model = self._build_model() if torch else None
        self._scorer = ScoreEvaluator()

        if checkpoint_path:
            self.load_checkpoint(checkpoint_path)

    def _build_model(self):
        if torch is None or nn is None:
            logger.info("Torch is not available; ModelPredictor will operate in numpy mode.")
            return None
        model = nn.Sequential(
            nn.Linear(self.input_size, self.hidden_size),
            nn.ReLU(),
            nn.Linear(self.hidden_size, self.hidden_size),
            nn.ReLU(),
            nn.Linear(self.hidden_size, 1),
            nn.Tanh(),
        )
        return model

    def predict(self, features: Sequence[float]) -> float:
        """Return a prediction between -1 and 1."""
        if len(features) != self.input_size:
            raise ValueError(f"Expected {self.input_size} features, got {len(features)}")

        if self._model is None:
            if np is not None:
                weights = np.linspace(1.0, 2.0, self.input_size)
                numerator = float(np.dot(weights, np.asarray(features)))
                denom = float(weights.sum()) or 1.0
            else:
                weights = [1.0 + (i / max(1, self.input_size - 1)) for i in range(self.input_size)]
                numerator = sum(w * float(f) for w, f in zip(weights, features))
                denom = sum(weights) or 1.0
            value = numerator / denom
            prediction = float(math.tanh(value))
        else:
            with torch.no_grad():
                tensor = torch.tensor(features, dtype=torch.float32).view(1, -1)
                prediction = float(self._model(tensor).item())

        logger.debug("Generated prediction=%s", prediction)
        return prediction

    def batch_predict(
        self,
        batch: Iterable[Sequence[float]],
        *,
        actual: Optional[Sequence[float]] = None,
        pnl: Optional[Sequence[float]] = None,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
    ) -> Any:
        """Generate predictions and optionally evaluate scoring metrics."""
        predictions = [self.predict(features) for features in batch]
        if actual is not None:
            metrics = self._scorer.evaluate(predictions, actual, pnl)
            if audit_log is not None:
                self._log_scoring(metrics, audit_log, session_id=session_id, hmac_key=hmac_key)
            return predictions, metrics
        return predictions

    def load_checkpoint(self, path: Path) -> None:
        """Load model weights from checkpoint if torch backend is available."""
        if path is None:
            return
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        if self._model is None:
            logger.warning("Torch unavailable; skipping checkpoint load for %s", path)
            return
        state = torch.load(path, map_location="cpu")  # type: ignore[call-arg]
        self._model.load_state_dict(state)
        logger.info("Loaded predictor checkpoint from %s", path)

    def save_checkpoint(self, path: Path) -> None:
        """Persist model weights."""
        if self._model is None:
            logger.warning("Torch unavailable; skipping checkpoint save to %s", path)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.state_dict(), path)  # type: ignore[arg-type]
        logger.info("Saved predictor checkpoint to %s", path)

    def audit_prediction(
        self,
        features: Sequence[float],
        prediction: float,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
    ) -> None:
        """Record a prediction event in the audit log."""
        if audit_log is None:
            return
        try:
            entry: Dict[str, Any] = {
                "module": "qai.model_predictor",
                "session_id": session_id,
                "prediction": float(prediction),
                "feature_hash": hash(tuple(round(f, 6) for f in features)),
            }
            append_signed_audit(entry, audit_log=audit_log, hmac_key=hmac_key)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to append predictor audit entry: %s", exc)

    def _log_scoring(
        self,
        metrics: Dict[str, float],
        audit_log: Path,
        *,
        session_id: Optional[str],
        hmac_key: Optional[str],
    ) -> None:
        entry = {
            "module": "qai.scoring",
            "event": "evaluate",
            "metrics": metrics,
            "session_id": session_id,
        }
        append_signed_audit(entry, audit_log=audit_log, hmac_key=hmac_key, session_id=session_id)
