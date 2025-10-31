"""Scoring utilities for QAI predictive models."""

from __future__ import annotations

from math import sqrt
from typing import Iterable, Optional, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def _to_array(values: Sequence[float]):
    if np is not None:
        return np.asarray(list(values), dtype=float)
    return [float(v) for v in values]


def accuracy_score(predictions: Sequence[float], actual: Sequence[float]) -> float:
    preds = _to_array(predictions)
    acts = _to_array(actual)
    if len(preds) != len(acts) or not preds:
        return 0.0
    if np is not None:
        pred_dir = np.sign(preds)
        actual_dir = np.sign(acts)
        correct = np.sum(pred_dir == actual_dir)
        return float(correct) / len(pred_dir)
    correct = sum(1 for p, a in zip(preds, acts) if (p >= 0 and a >= 0) or (p < 0 and a < 0))
    return correct / len(preds)


def stability_index(predictions: Sequence[float]) -> float:
    preds = _to_array(predictions)
    if not preds:
        return 0.0
    if np is not None:
        diffs = np.diff(preds)
        return float(1.0 / (1.0 + np.std(diffs, dtype=float)))
    diffs = [preds[i] - preds[i - 1] for i in range(1, len(preds))] or [0.0]
    mean = sum(diffs) / len(diffs)
    variance = sum((x - mean) ** 2 for x in diffs) / len(diffs)
    std_dev = sqrt(variance)
    return 1.0 / (1.0 + std_dev)


def reward_factor(predictions: Sequence[float], pnl: Sequence[float]) -> float:
    preds = _to_array(predictions)
    rewards = _to_array(pnl)
    if len(preds) != len(rewards) or not preds:
        return 0.0
    if np is not None:
        numerator = np.sum(np.sign(preds) * rewards)
        denom = np.sum(np.abs(rewards)) or 1.0
        return float(numerator / denom)
    numerator = sum((1 if p >= 0 else -1) * r for p, r in zip(preds, rewards))
    denom = sum(abs(r) for r in rewards) or 1.0
    return numerator / denom


class ScoreEvaluator:
    """Compute standard metrics for predictor outputs."""

    def evaluate(
        self,
        predictions: Sequence[float],
        actual: Sequence[float],
        pnl: Optional[Sequence[float]] = None,
    ) -> dict:
        pnl = pnl if pnl is not None else actual
        return {
            "accuracy": accuracy_score(predictions, actual),
            "stability": stability_index(predictions),
            "reward": reward_factor(predictions, pnl),
        }
