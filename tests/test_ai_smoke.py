"""Smoke test for AI core imports and basic flow.

This test ensures the AI/data/features modules import cleanly and a
simple train/predict flow runs without external dependencies.
"""
from datetime import datetime

from src.data.ingest import InMemoryLoader
from src.features.pipeline import FeaturePipeline, PriceDiffFeature
from src.ai.core import PredictiveModel


def test_ai_flow_imports_and_run():
    records = [
        {"timestamp": datetime.utcnow(), "symbol": "EURUSD", "price": 1.1},
        {"timestamp": datetime.utcnow(), "symbol": "EURUSD", "price": 1.1005},
    ]
    loader = InMemoryLoader(records=records)
    pipeline = FeaturePipeline([PriceDiffFeature()])
    model = PredictiveModel()

    dataset = list(pipeline.run(loader.fetch()))
    model.train(dataset)
    p = model.predict(dataset[0])
    assert isinstance(p, dict)
