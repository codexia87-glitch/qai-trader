"""
Feature engineering pipeline stubs for qai-trader.

Sprint 4: provide a small, composable pipeline API where Feature
components implement `transform(records)` and the `FeaturePipeline`
applies them in sequence. No heavy numeric libraries are required at
this stage — just contracts and simple examples.
"""
from __future__ import annotations

from typing import Iterable, Dict, Any, List, Callable


class Feature:
    """Base feature transformer.

    Subclasses should implement `transform(records)` that yields records
    enhanced with additional fields.
    """

    def transform(self, records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError()


class FeaturePipeline:
    """Apply a sequence of Feature transformers.

    Example usage:
        pipeline = FeaturePipeline([FeatureA(), FeatureB()])
        out = list(pipeline.run(records))
    """

    def __init__(self, steps: List[Feature]):
        self.steps = steps

    def run(self, records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        current = records
        for s in self.steps:
            current = s.transform(current)
        return current


class PriceDiffFeature(Feature):
    """A tiny example feature that adds 'price_diff' between consecutive
    records for the same symbol. This is simple and deterministic for
    unit tests; production versions should be vectorized and tested.
    """

    def transform(self, records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
        last: Dict[str, float] = {}
        for r in records:
            sym = r.get("symbol")
            price = r.get("price")
            prev = last.get(sym)
            r = dict(r)
            if prev is None:
                r["price_diff"] = None
            else:
                r["price_diff"] = price - prev
            last[sym] = price
            yield r


__all__ = ["Feature", "FeaturePipeline", "PriceDiffFeature"]
