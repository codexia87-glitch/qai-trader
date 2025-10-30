"""
Simulator for signal execution and a simple Python<->MT5 bridge loop.

This module provides `process_once(folder)` which scans `folder` for
signal files (*.sig, *.sig.json), parses them (text or JSON), performs
a simulated execution (no real orders), and moves processed files to
an `archived/` subfolder to avoid re-processing.

Design aims:
- Pure Python, stdlib only
- Deterministic and testable: process_once returns a list of processed
  records for assertions in tests
- Atomic moves for processed files (os.replace)
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Tuple
import os
import json
import shutil

from .mt5_bridge import Signal, write_signal
from . import signal_schema


def _parse_text_signal(path: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip() or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def _parse_json_signal(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _normalize_to_v1(d: Dict[str, Any]) -> signal_schema.SignalV1:
    # Use the schema validator to coerce/validate and fill defaults
    return signal_schema.validate_signal_dict(d)


def _archive(path: Path, archive_root: Path) -> Path:
    archive_root.mkdir(parents=True, exist_ok=True)
    dest = archive_root / path.name
    # Use atomic replace to move
    os.replace(str(path), str(dest))
    return dest


def process_once(folder: Path) -> List[Dict[str, Any]]:
    """Scan `folder` for signals, process them once, and archive them.

    Returns a list of processed signal records (dictionaries) with keys:
      - 'path': original path (Path)
      - 'archived': archived path (Path)
      - 'signal': validated SignalV1 instance
      - 'result': simulated execution result dict
    """
    folder = Path(folder)
    if not folder.exists():
        return []

    processed: List[Dict[str, Any]] = []
    archive_root = folder / "archived"

    # Look for both .sig and .sig.json files
    patterns = ["*.sig.json", "*.sig"]
    files: List[Path] = []
    for p in patterns:
        files.extend(sorted(folder.glob(p)))

    for f in files:
        try:
            if f.suffix == ".json" or f.name.endswith(".sig.json"):
                raw = _parse_json_signal(f)
            else:
                raw = _parse_text_signal(f)

            sigv1 = _normalize_to_v1(raw)

            # Simulated execution: we just create a fake fill result
            result = {
                "status": "simulated_filled",
                "symbol": sigv1.symbol,
                "side": sigv1.side,
                "volume": sigv1.volume,
                "exec_price": sigv1.price or 0.0,
            }

            archived = _archive(f, archive_root)

            processed.append({"path": f, "archived": archived, "signal": sigv1, "result": result})
        except Exception as e:
            # On error, move file to failed/ for manual inspection
            failed_root = folder / "failed"
            failed_root.mkdir(parents=True, exist_ok=True)
            dest = failed_root / f.name
            try:
                os.replace(str(f), str(dest))
            except Exception:
                # last resort copy and unlink
                try:
                    shutil.copy2(str(f), str(dest))
                    f.unlink()
                except Exception:
                    pass
            processed.append({"path": f, "archived": dest, "signal": None, "result": {"status": "error", "error": str(e)}})

    return processed


def watch_loop(folder: Path, poll_interval: float = 1.0) -> None:
    """Simple blocking loop that polls `folder` and processes signals.

    This is intentionally naive (polling). It prints the simulated
    execution results to stdout.
    """
    import time

    folder = Path(folder)
    print(f"Starting simulator loop on {folder} (poll_interval={poll_interval}s)")
    try:
        while True:
            processed = process_once(folder)
            for rec in processed:
                if rec["signal"] is not None:
                    s = rec["signal"]
                    print(f"[SIM] executed {s.side} {s.symbol} vol={s.volume} id={s.id}")
                else:
                    print(f"[SIM] failed processing {rec['path']}: {rec['result']}")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("Simulator stopped by user")


__all__ = ["process_once", "watch_loop"]
