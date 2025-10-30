"""Tests for the bridge simulator: processing and archiving signals."""
from pathlib import Path
import tempfile

from src.bridge.mt5_bridge import Signal, write_signal
from src.bridge.simulator import process_once


def test_process_once_text_and_json(tmp_path: Path):
    # Create example files using the bridge writer
    out = tmp_path / "signals"
    out.mkdir()

    sig1 = Signal(symbol="EURUSD", side="BUY", volume=0.01, sl_pts=10, tp_pts=20)
    sig2 = Signal(symbol="EURUSD", side="SELL", volume=0.02, sl_pts=5, tp_pts=15)

    p1 = write_signal(sig1, out, fmt="text")
    p2 = write_signal(sig2, out, fmt="json")

    processed = process_once(out)

    # Both signals should be processed and moved to archived/
    assert len(processed) == 2
    archived = out / "archived"
    assert archived.exists()
    archived_files = list(archived.iterdir())
    assert any(f.name.endswith(".sig") or f.name.endswith(".sig.json") for f in archived_files)
