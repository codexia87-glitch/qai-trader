"""
Tiny script that demonstrates training the stub predictive model.

This is a no-ML, no-network example that shows the intended flow:
ingest -> features -> train -> predict. Useful as a starting point for
Sprint 4 development and for manual smoke-testing.
"""
from pathlib import Path
import sys
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data.ingest import InMemoryLoader
from src.features.pipeline import FeaturePipeline, PriceDiffFeature
from src.ai.core import PredictiveModel


def main() -> None:
    # small dataset
    records = [
        {"timestamp": datetime.utcnow(), "symbol": "EURUSD", "price": 1.1},
        {"timestamp": datetime.utcnow(), "symbol": "EURUSD", "price": 1.1005},
    ]

    loader = InMemoryLoader(records=records)
    pipeline = FeaturePipeline([PriceDiffFeature()])
    model = PredictiveModel()

    dataset = list(pipeline.run(loader.fetch()))
    model.train(dataset)
    pred = model.predict(dataset[0])
    print("trained?", model._trained)
    print("prediction:", pred)


if __name__ == "__main__":
    main()
