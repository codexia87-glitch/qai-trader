"""
Example script demonstrating how one would use the PyTorch trainer
and LSTM model skeleton. This script runs in dry mode if PyTorch is
not installed (prints instructions). Install PyTorch to actually run it.
"""
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.ai.models import create_lstm_model
    from src.ai.pytorch_trainer import Trainer
except Exception as e:
    print("PyTorch or trainer modules unavailable:", e)
    print("Install PyTorch to run this example: https://pytorch.org/")
    sys.exit(0)

def main() -> None:
    # Small example factory
    def model_factory():
        return create_lstm_model(input_size=1, hidden_size=8, num_layers=1, output_size=1)

    model = model_factory()
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
    except Exception:
        print("PyTorch not available; exiting")
        return

    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    trainer = Trainer(model, optimizer=optimizer, loss_fn=loss_fn)

    # Dummy dataset: list of (x, y) tensors
    # x shape: (batch, seq_len, features) -> here (1, 5, 1)
    x = torch.randn(1, 5, 1)
    y = torch.randn(1, 1)
    dataset = [(x, y)]

    trainer.train(dataset, epochs=1)
    out_path = project_root / "models" / "lstm.pth"
    trainer.save(out_path)
    print("Saved model to", out_path)
    # record checkpoint for the saved model
    try:
        from src.utils.checkpoint_manager import record_script_run

        record_script_run(
            script=str(Path(__file__).relative_to(project_root)),
            args={},
            checkpoints=[{"path": str(out_path), "type": "pytorch_model", "meta": {"model": "lstm"}}],
        )
    except Exception:
        # best-effort; do not crash the example because of checkpointing
        pass


if __name__ == "__main__":
    main()
