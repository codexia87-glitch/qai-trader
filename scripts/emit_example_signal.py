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
    parser.add_argument("--symbol", type=str, default="EURUSD", help="Trading symbol (default: EURUSD)")
    parser.add_argument("--side", type=str, default="BUY", choices=["BUY", "SELL"], help="Order side: BUY or SELL")
    parser.add_argument("--volume", type=float, default=0.01, help="Lot size (default: 0.01)")
    parser.add_argument("--sl", type=int, default=40, help="Stop Loss in points (default: 40)")
    parser.add_argument("--tp", type=int, default=80, help="Take Profit in points (default: 80)")
    parser.add_argument("--price", type=float, default=None, help="Optional entry price")
    args = parser.parse_args()

    out_folder = project_root / (args.out if args.out else "example_signals")

    sig = Signal(
        symbol=args.symbol,
        side=args.side,
        volume=args.volume,
        price=args.price,
        sl_pts=args.sl,
        tp_pts=args.tp,
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
