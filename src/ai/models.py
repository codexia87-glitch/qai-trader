"""
PyTorch model definitions (skeleton).

This file defines a small LSTM-based model factory for time-series
prediction. To avoid import-time errors when PyTorch is not installed,
we perform lazy imports inside factory functions.
"""
from __future__ import annotations

from typing import Tuple


def create_lstm_model(input_size: int, hidden_size: int = 32, num_layers: int = 1, output_size: int = 1):
    """Create and return a torch.nn.Module LSTM model.

    Raises ImportError if PyTorch is not available. The function keeps
    a minimal interface so tests can import the module even when torch
    is missing (they should catch ImportError if necessary).
    """
    try:
        import torch
        import torch.nn as nn
    except Exception as e:
        raise ImportError("PyTorch is required for LSTM model creation: " + str(e))

    class LSTMModel(nn.Module):
        def __init__(self, input_size: int, hidden_size: int, num_layers: int, output_size: int):
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, output_size)

        def forward(self, x):
            # x: (batch, seq, features)
            out, _ = self.lstm(x)
            # take last time-step
            out = out[:, -1, :]
            out = self.fc(out)
            return out

    return LSTMModel(input_size, hidden_size, num_layers, output_size)


__all__ = ["create_lstm_model"]
