"""Adaptive reinforcement learning optimizer prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

from .logging_utils import append_signed_audit


@dataclass
class OptimizerState:
    weights: List[float] = field(default_factory=list)
    epsilon: float = 0.1
    gamma: float = 0.95


class OptimizerRL:
    """Simple optimizer that blends adaptive weights with reinforcement signals."""

    def __init__(
        self,
        input_size: int,
        *,
        learning_rate: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 0.1,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
    ) -> None:
        if input_size <= 0:
            raise ValueError("input_size must be positive")
        self.learning_rate = learning_rate
        self.state = OptimizerState(weights=[0.0] * input_size, epsilon=epsilon, gamma=gamma)
        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key
        if audit_log:
            append_signed_audit(
                {
                    "module": "qai.optimizer",
                    "event": "init",
                    "session_id": session_id,
                    "learning_rate": learning_rate,
                    "gamma": gamma,
                    "epsilon": epsilon,
                },
                audit_log=audit_log,
                session_id=session_id,
                hmac_key=hmac_key,
            )

    def policy(self, features: Sequence[float]) -> float:
        weights = self.state.weights
        if np is not None:
            return float(np.dot(np.asarray(weights, dtype=float), np.asarray(features, dtype=float)))
        return sum(w * float(f) for w, f in zip(weights, features))

    def train_step(self, features: Sequence[float], reward: float) -> float:
        prediction = self.policy(features)
        advantage = reward - prediction
        update = self.learning_rate * advantage
        self._apply_update(features, update)
        self._decay_epsilon()
        return prediction + update

    def _apply_update(self, features: Sequence[float], delta: float) -> None:
        if np is not None:
            self.state.weights = (
                np.asarray(self.state.weights, dtype=float)
                + delta * np.asarray(features, dtype=float)
            ).tolist()
        else:
            self.state.weights = [w + delta * float(f) for w, f in zip(self.state.weights, features)]

    def _decay_epsilon(self) -> None:
        self.state.epsilon = max(0.01, self.state.epsilon * 0.99)

    def suggest(self, features: Sequence[float]) -> int:
        score = self.policy(features)
        if score >= self.state.epsilon:
            return 1
        if score <= -self.state.epsilon:
            return -1
        return 0
