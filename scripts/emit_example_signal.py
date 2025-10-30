"""
Emit an example trading signal to simulate the Python -> MT5 signal flow.

This script emits a JSON signal by default (recommended). Pass
`--text` to emit the legacy key=value `.sig` file instead.

Run from project root:
    python scripts/emit_example_signal.py
    python scripts/emit_example_signal.py --text
"""
from pathlib import Path
from datetime import datetime
import sys
import argparse

# Ensure the project root is on sys.path so we can run this script directly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.bridge.mt5_bridge import Signal, write_signal
from src.utils.checkpoint_manager import add_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit example signal for MT5 bridge")
    parser.add_argument("--text", action="store_true", help="Emit legacy .sig key=value text file instead of JSON")
    parser.add_argument("--out", type=str, default=None, help="Optional output folder (relative to project root)")
    args = parser.parse_args()

    out_folder = project_root / (args.out if args.out else "example_signals")

    sig = Signal(
        symbol="EURUSD",
        side="BUY",
        volume=0.01,
        sl_pts=40,
        tp_pts=80,
        ts=datetime.utcnow(),
    )

    fmt = "text" if args.text else "json"
    path = write_signal(sig, out_folder, fmt=fmt)

    print(f"Wrote signal ({fmt}): {path}")
    print("--- file content ---")
    print(path.read_text(encoding="utf-8"))
    print("--- end content ---")
    # record the emitted signal as a lightweight checkpoint
    try:
        add_checkpoint(path=str(path), typ="signal", meta={"format": fmt})
    except Exception:
        pass


if __name__ == "__main__":
    main()
