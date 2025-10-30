"""
CLI wrapper to process `.sig.json` files and optionally send live orders.

Usage:
  python scripts/run_mt5_client.py --folder example_signals --dry-run
  python scripts/run_mt5_client.py --folder example_signals --live

Credentials are read from environment variables by default:
  MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER

Be careful with `--live`.
"""
from pathlib import Path
import sys
import argparse
import os

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.bridge.mt5_client import process_folder
from src.utils.checkpoint_manager import record_script_run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="example_signals")
    parser.add_argument("--live", action="store_true", help="Send real orders via MetaTrader5 (use with caution)")
    parser.add_argument("--once", action="store_true", help="Process once and exit")
    args = parser.parse_args()

    folder = project_root / args.folder
    live = args.live

    connect_params = None
    if live:
        # read credentials from env
        account = os.environ.get("MT5_ACCOUNT")
        password = os.environ.get("MT5_PASSWORD")
        server = os.environ.get("MT5_SERVER")
        if account is None:
            print("MT5_ACCOUNT not set in environment; cannot run in live mode")
            return
        connect_params = {"account": int(account), "password": password, "server": server}

    results = process_folder(folder, live=live, connect_params=connect_params)
    for r in results:
        print(r)

    try:
        record_script_run(
            script=str(Path(__file__).relative_to(project_root)),
            args=vars(args),
            checkpoints=[{"path": str(folder), "type": "mt5_client_run", "meta": {"count": len(results)}}],
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
