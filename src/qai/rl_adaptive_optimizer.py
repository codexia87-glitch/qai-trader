"""Adaptive reinforcement optimizer with dynamic memory and auto-tuning."""

from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Sequence

from .logging_utils import append_signed_audit
from .optimizer import OptimizerRL


@dataclass
class MemorySample:
    state: List[float]
    reward: float

    def to_dict(self) -> Dict[str, object]:
        return {"state": self.state, "reward": self.reward}


@dataclass
class AdaptiveMemory:
    """Experience buffer with dynamic capacity."""

    base_capacity: int = 256
    max_capacity: int = 1024
    min_capacity: int = 64
    decay: float = 0.98
    buffer: Deque[MemorySample] = field(default_factory=deque)
    capacity: int = field(init=False)

    def __post_init__(self) -> None:
        self.capacity = self.base_capacity

    def append(self, state: Sequence[float], reward: float) -> None:
        self.buffer.append(MemorySample(list(state), float(reward)))
        self._truncate()

    def summary(self) -> Dict[str, float]:
        if not self.buffer:
            return {"count": 0, "mean_reward": 0.0, "volatility": 0.0}
        rewards = [sample.reward for sample in self.buffer]
        count = len(rewards)
        mean_reward = sum(rewards) / count
        variance = sum((value - mean_reward) ** 2 for value in rewards) / count
        volatility = math.sqrt(variance)
        return {"count": count, "mean_reward": mean_reward, "volatility": volatility}

    def adapt_capacity(self, volatility: float) -> None:
        target = int(self.base_capacity * (1 + min(volatility, 2.0)))
        target = max(self.min_capacity, min(self.max_capacity, target))
        if target != self.capacity:
            self.capacity = target
            self._truncate()

    def snapshot(self) -> List[Dict[str, object]]:
        return [sample.to_dict() for sample in self.buffer]

    def load_snapshot(self, samples: Iterable[Dict[str, object]]) -> None:
        self.buffer.clear()
        for item in samples:
            state = list(item.get("state", []))
            reward = float(item.get("reward", 0.0))
            self.buffer.append(MemorySample(state, reward))
        self._truncate()

    def __len__(self) -> int:  # pragma: no cover - simple delegation
        return len(self.buffer)

    def _truncate(self) -> None:
        while len(self.buffer) > self.capacity:
            self.buffer.popleft()
        if len(self.buffer) < self.min_capacity:
            return
        if self.decay < 1.0:
            # Apply decay by down-weighting older experiences through thinning
            keep = deque()
            for idx, sample in enumerate(self.buffer):
                if idx == len(self.buffer) - 1 or (idx % int(1 / max(self.decay, 0.1)) == 0):
                    keep.append(sample)
            self.buffer = keep


class RLAdaptiveOptimizer:
    """Wrapper around OptimizerRL with adaptive memory and learning rate tuning."""

    def __init__(
        self,
        input_size: int,
        *,
        base_optimizer: Optional[OptimizerRL] = None,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
        memory: Optional[AdaptiveMemory] = None,
        memory_path: Optional[Path] = None,
        learning_rate: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 0.1,
        min_learning_rate: float = 0.01,
        max_learning_rate: float = 0.5,
        smoothing: float = 0.25,
    ) -> None:
        if input_size <= 0:
            raise ValueError("input_size must be positive")

        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key

        self.memory_path = Path(memory_path or Path("var/rl/adaptive_optimizer.json"))
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        self.memory = memory or AdaptiveMemory()
        self.base_optimizer = base_optimizer or OptimizerRL(
            input_size,
            learning_rate=learning_rate,
            gamma=gamma,
            epsilon=epsilon,
            audit_log=None,
        )
        self._initial_lr = self.base_optimizer.learning_rate
        self.min_learning_rate = min_learning_rate
        self.max_learning_rate = max_learning_rate
        self.smoothing = smoothing
        self._steps = 0

        self._load_state()
        self._log_event(
            "adaptive_init",
            {
                "learning_rate": self.base_optimizer.learning_rate,
                "memory_size": len(self.memory),
                "min_lr": self.min_learning_rate,
                "max_lr": self.max_learning_rate,
            },
        )

    @property
    def learning_rate(self) -> float:
        return self.base_optimizer.learning_rate

    def update(self, state: Sequence[float], reward: float) -> Dict[str, float]:
        self.memory.append(state, reward)
        stats = self.memory.summary()
        self.memory.adapt_capacity(stats["volatility"])

        target_lr = self._target_learning_rate(stats)
        tuned_lr = self._apply_smoothing(target_lr)
        self.base_optimizer.learning_rate = tuned_lr
        prediction = self.base_optimizer.train_step(state, reward)

        self._steps += 1
        metrics = {
            "learning_rate": tuned_lr,
            "prediction": prediction,
            "mean_reward": stats["mean_reward"],
            "volatility": stats["volatility"],
            "memory_size": stats["count"],
        }
        self._log_event("adaptive_update", metrics)
        if self._steps % 10 == 0:
            self.save_state()
        return metrics

    def observe_trade(self, trade: Dict[str, float]) -> Dict[str, float]:
        entry = float(trade.get("entry", 0.0))
        exit_price = float(trade.get("exit", entry))
        pnl = float(trade.get("pnl", 0.0))
        features = [entry, exit_price - entry, pnl]
        return self.update(features, pnl)

    def suggest(self, features: Sequence[float]) -> int:
        return self.base_optimizer.suggest(features)

    def finalize(self) -> None:
        self.save_state()

    def save_state(self) -> None:
        payload = {
            "learning_rate": self.base_optimizer.learning_rate,
            "epsilon": self.base_optimizer.state.epsilon,
            "gamma": self.base_optimizer.state.gamma if hasattr(self.base_optimizer.state, "gamma") else 0.95,
            "memory": self.memory.snapshot(),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_state(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            self.base_optimizer.learning_rate = float(data.get("learning_rate", self.base_optimizer.learning_rate))
            epsilon = float(data.get("epsilon", self.base_optimizer.state.epsilon))
            self.base_optimizer.state.epsilon = epsilon
            self.base_optimizer.state.gamma = float(data.get("gamma", self.base_optimizer.state.gamma))
            self.memory.load_snapshot(data.get("memory", []))
        except Exception:
            # Corrupted state should not break runtime; fallback to defaults.
            pass

    def _target_learning_rate(self, stats: Dict[str, float]) -> float:
        mean_reward = stats["mean_reward"]
        volatility = stats["volatility"]
        tilt = mean_reward / (1.0 + volatility)
        target = self._initial_lr * (1.0 + 0.5 * tilt)
        return max(self.min_learning_rate, min(self.max_learning_rate, target))

    def _apply_smoothing(self, target: float) -> float:
        current = self.base_optimizer.learning_rate
        return current * self.smoothing + target * (1.0 - self.smoothing)

    def _log_event(self, event: str, payload: Dict[str, object]) -> None:
        if self.audit_log is None:
            return
        entry = {
            "module": "qai.optimizer",
            "event": event,
            "session_id": self.session_id,
        }
        entry.update(payload)
        append_signed_audit(
            entry,
            audit_log=self.audit_log,
            session_id=self.session_id,
            hmac_key=self.hmac_key,
        )
