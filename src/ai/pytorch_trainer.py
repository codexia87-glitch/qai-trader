"""
Skeleton PyTorch trainer utilities.

This module provides a minimal `Trainer` class with `train`, `save`,
and `load` functions. It uses lazy imports so the package can be
imported without PyTorch present; attempting to use trainer methods
without PyTorch will raise informative ImportError.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


class Trainer:
    """Minimal trainer wrapper around a PyTorch model.

    Methods:
      - train(dataset, epochs=1): minimal loop (user-provided dataset
        must yield (x, y) torch tensors).
      - save(path): save model state_dict and trainer config
      - load(path, model_factory): classmethod to load a saved model
    """

    def __init__(self, model: Any, optimizer: Optional[Any] = None, loss_fn: Optional[Any] = None):
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self._torch = None
        # training state
        self.epoch = 0
        self.training_stats: dict = {}

    def _ensure_torch(self):
        if self._torch is None:
            try:
                import torch
            except Exception as e:
                raise ImportError("PyTorch is required to use Trainer: " + str(e))
            self._torch = torch
        return self._torch

    def train(self, dataset, epochs: int = 1, device: str = "cpu"):
        torch = self._ensure_torch()
        device_obj = torch.device(device)
        self.model.to(device_obj)
        if self.optimizer is None or self.loss_fn is None:
            raise RuntimeError("Trainer requires optimizer and loss_fn")

        self.model.train()
        for epoch in range(epochs):
            for x, y in dataset:
                x = x.to(device_obj)
                y = y.to(device_obj)
                self.optimizer.zero_grad()
                out = self.model(x)
                loss = self.loss_fn(out, y)
                loss.backward()
                self.optimizer.step()

    def save(self, path: Path):
        torch = self._ensure_torch()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Persist model state, optimizer state (if available), epoch and training stats
        state: dict = {
            "model_state": self.model.state_dict(),
            "epoch": int(self.epoch),
            "training_stats": self.training_stats,
        }
        if self.optimizer is not None:
            try:
                state["optimizer_state"] = self.optimizer.state_dict()
            except Exception:
                # if optimizer has no state_dict or fails, skip but warn via metadata
                state["optimizer_state"] = None

        torch.save(state, str(path))

    @classmethod
    def load(cls, path: Path, model_factory):
        try:
            import torch
        except Exception as e:
            raise ImportError("PyTorch is required to load Trainer state: " + str(e))

        path = Path(path)
        state = torch.load(str(path), map_location="cpu")
        model = model_factory()
        model.load_state_dict(state.get("model_state", {}))

        # Create trainer instance
        trainer = cls(model)

        # restore epoch and stats if present
        trainer.epoch = int(state.get("epoch", 0))
        trainer.training_stats = state.get("training_stats", {}) or {}

        # If caller provides an optimizer via optimizer_factory attribute on model_factory
        # we don't have that here; instead we offer the caller to pass an optimizer
        # via a second return value or to call `attach_optimizer` themselves.
        # However, for convenience, if the model_factory has an attribute
        # `optimizer_factory` we will call it to recreate and restore optimizer state.
        optimizer_state = state.get("optimizer_state", None)
        opt = None
        opt_factory = getattr(model_factory, "optimizer_factory", None)
        if opt_factory is not None:
            try:
                opt = opt_factory(model.parameters())
                if optimizer_state:
                    opt.load_state_dict(optimizer_state)
                trainer.optimizer = opt
            except Exception:
                # failed to restore optimizer; leave as None
                trainer.optimizer = opt

        return trainer

    def attach_optimizer(self, optimizer: Any, restore_state: Optional[dict] = None) -> None:
        """Attach an optimizer to the trainer and optionally restore its state.

        This helper allows callers that created an optimizer externally to
        attach it to a loaded Trainer and restore optimizer_state from a
        loaded checkpoint dict.
        """
        self.optimizer = optimizer
        if restore_state is not None:
            try:
                self.optimizer.load_state_dict(restore_state)
            except Exception:
                # ignore restore errors; caller will handle
                pass


__all__ = ["Trainer"]
