"""Continuous reinforcement learning agent with persistent experience."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .logging_utils import append_signed_audit
from .optimizer import OptimizerRL


@dataclass
class Experience:
    state: List[float]
    reward: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "state": self.state,
            "reward": self.reward,
        }


@dataclass
class RLState:
    epsilon: float = 0.1
    weights: List[float] = field(default_factory=list)


class RLContinuousAgent:
    """Reinforcement agent that keeps a persistent replay buffer between runs."""

    def __init__(
        self,
        input_size: int,
        *,
        state_path: Optional[Path] = None,
        replay_path: Optional[Path] = None,
        max_buffer: int = 1024,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
        optimizer: Optional[OptimizerRL] = None,
    ) -> None:
        if input_size <= 0:
            raise ValueError("input_size must be positive")

        self.state_path = Path(state_path or Path("var/rl/continuous_state.json"))
        self.replay_path = Path(replay_path or Path("var/rl/replay_buffer.json"))
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.replay_path.parent.mkdir(parents=True, exist_ok=True)

        self.max_buffer = max_buffer
        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key

        self.optimizer = optimizer or OptimizerRL(
            input_size,
            audit_log=audit_log,
            session_id=session_id,
            hmac_key=hmac_key,
        )

        self.replay_buffer: List[Experience] = []
        self.state = RLState(epsilon=self.optimizer.state.epsilon, weights=self.optimizer.state.weights)
        self._load_state()

        if audit_log is not None:
            append_signed_audit(
                {
                    "module": "qai.rl",
                    "event": "continuous_init",
                    "session_id": session_id,
                    "buffer_size": len(self.replay_buffer),
                    "epsilon": self.state.epsilon,
                },
                audit_log=audit_log,
                session_id=session_id,
                hmac_key=hmac_key,
            )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load_state(self) -> None:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                self.state.epsilon = data.get("epsilon", self.state.epsilon)
                self.state.weights = data.get("weights", self.state.weights)
                self.optimizer.state.weights = list(self.state.weights)
                self.optimizer.state.epsilon = self.state.epsilon
            except Exception:
                # corrupted state -> fallback to defaults
                pass
        if self.replay_path.exists():
            try:
                entries = json.loads(self.replay_path.read_text(encoding="utf-8"))
                self.replay_buffer = [Experience(state=list(item["state"]), reward=float(item["reward"])) for item in entries]
            except Exception:
                self.replay_buffer = []
        self._truncate_buffer()

    def save_state(self) -> None:
        data = {
            "epsilon": self.optimizer.state.epsilon,
            "weights": self.optimizer.state.weights,
        }
        self.state_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.replay_path.write_text(
            json.dumps([exp.to_dict() for exp in self.replay_buffer], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Experience handling
    # ------------------------------------------------------------------
    def append_experience(self, state: Sequence[float], reward: float) -> None:
        self.replay_buffer.append(Experience(list(state), float(reward)))
        self._truncate_buffer()

    def observe_trade(self, trade: Dict[str, float]) -> None:
        entry = float(trade.get("entry", 0.0))
        exit_price = float(trade.get("exit", entry))
        pnl = float(trade.get("pnl", 0.0))
        features = [entry, exit_price - entry, pnl]
        self.append_experience(features, pnl)

    def _truncate_buffer(self) -> None:
        if len(self.replay_buffer) > self.max_buffer:
            self.replay_buffer = self.replay_buffer[-self.max_buffer :]

    # ------------------------------------------------------------------
    # Training utilities
    # ------------------------------------------------------------------
    def train(self, batch_size: int = 32) -> Dict[str, float]:
        if not self.replay_buffer:
            return {"updates": 0}
        updates = 0
        batch = self.replay_buffer[-batch_size:]
        for exp in batch:
            self.optimizer.train_step(exp.state, exp.reward)
            updates += 1
        self.state.epsilon = self.optimizer.state.epsilon
        self.state.weights = list(self.optimizer.state.weights)
        return {"updates": updates, "epsilon": self.state.epsilon}

    def end_episode(self, *, audit: bool = True) -> Dict[str, float]:
        metrics = self.train()
        self.save_state()
        if audit and self.audit_log is not None and metrics["updates"] > 0:
            append_signed_audit(
                {
                    "module": "qai.rl",
                    "event": "continuous_update",
                    "session_id": self.session_id,
                    "metrics": metrics,
                    "buffer_size": len(self.replay_buffer),
                },
                audit_log=self.audit_log,
                session_id=self.session_id,
                hmac_key=self.hmac_key,
            )
        return metrics

    def attach_optimizer(self, optimizer: OptimizerRL) -> None:
        self.optimizer = optimizer
        self.optimizer.state.weights = list(self.state.weights) or list(self.optimizer.state.weights)
        self.optimizer.state.epsilon = self.state.epsilon

    def load_state(self) -> None:
        self._load_state()

    def replay_snapshot(self) -> List[Dict[str, object]]:
        return [exp.to_dict() for exp in self.replay_buffer]
