"""Tests for the PyTorch trainer skeleton.

These tests are skipped automatically if PyTorch is not installed.
They exercise save/load and a tiny train loop with synthetic tensors.
"""
import pytest
from pathlib import Path

try:
    import torch  # noqa: F401
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")

from src.ai.models import create_lstm_model
from src.ai.pytorch_trainer import Trainer


def test_trainer_save_load(tmp_path: Path):
    model = create_lstm_model(input_size=1, hidden_size=8, num_layers=1, output_size=1)
    import torch
    import torch.nn as nn
    import torch.optim as optim

    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    trainer = Trainer(model, optimizer=optimizer, loss_fn=loss_fn)

    # tiny dataset
    x = torch.randn(1, 5, 1)
    y = torch.randn(1, 1)
    dataset = [(x, y)]

    trainer.train(dataset, epochs=1)
    path = tmp_path / "m.pth"
    trainer.save(path)

    # load back
    def factory():
        return create_lstm_model(input_size=1, hidden_size=8, num_layers=1, output_size=1)

    new_trainer = Trainer.load(path, model_factory=factory)
    assert new_trainer.model is not None
