"""
Run the signal execution simulator loop or a single pass.

Usage:
  python scripts/run_simulator.py --folder example_signals --once
  python scripts/run_simulator.py --folder example_signals --poll 1.0
"""
from pathlib import Path
import sys
import argparse

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.bridge.simulator import watch_loop, process_once
from src.utils.checkpoint_manager import record_script_run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="example_signals", help="Folder to watch/process")
    parser.add_argument("--once", action="store_true", help="Process once and exit")
    parser.add_argument("--poll", type=float, default=1.0, help="Poll interval in seconds for watch loop")
    args = parser.parse_args()

    folder = project_root / args.folder
    if args.once:
        processed = process_once(folder)
        for rec in processed:
            print(rec)
        # record run metadata and a small checkpoint summary
        ck_meta = {"processed_count": len(processed)}
        try:
            archived = [r.get("archived") for r in processed if isinstance(r, dict) and r.get("archived")]
            if archived:
                ck_meta["archived"] = archived
        except Exception:
            pass
        record_script_run(script=str(Path(__file__).relative_to(project_root)), args=vars(args), checkpoints=[{"path": str(folder), "type": "simulator_run", "meta": ck_meta}])
    else:
        # record that a watch loop started (will update .qai_state.json)
        record_script_run(script=str(Path(__file__).relative_to(project_root)), args=vars(args), checkpoints=None)
        watch_loop(folder, poll_interval=args.poll)


if __name__ == "__main__":
    main()
