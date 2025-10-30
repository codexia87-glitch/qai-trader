"""
Minimal Python bridge module for writing simple signals consumed by the
MetaTrader 5 EA `mt5/qai_bridge.mq5`.

Sprint 1 provided a simple text `.sig` writer. In Sprint 2 we add
support for JSON-formatted, versioned signals while keeping backward
compatibility with the original key=value `.sig` files.

This module provides:
- `Signal` dataclass: small in-memory representation
- `write_signal(..., fmt='text'|'json')`: write atomically either a
    legacy text `.sig` file or a JSON `.sig.json` file (recommended).

Notes:
- JSON serialization uses the `signal_schema` module (v1) for
    canonicalization and validation when `fmt='json'`.
- Both formats are written atomically (temp file in same dir + rename)
    to avoid partial reads by the EA.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import datetime
import tempfile
import os
import io

# For JSON schema serialization (versioned)
from . import signal_schema


@dataclass
class Signal:
    """Representation of a simple trading signal.

    Fields are intentionally minimal for Sprint 1. Expand as needed.
    """

    symbol: str
    side: str  # 'BUY' or 'SELL'
    volume: float
    price: Optional[float] = None
    sl_pts: Optional[int] = None
    tp_pts: Optional[int] = None
    ts: Optional[datetime.datetime] = None


def write_signal(signal: Signal, folder: Path, name: Optional[str] = None, fmt: str = "text") -> Path:
    """Write a `.sig` file representing `signal` into `folder`.

    Returns the path to the written file. This helper is small and
    synchronous; it purposely avoids advanced features like atomic
    renames or cryptographic signing — add those in later sprints.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    if fmt not in ("text", "json"):
        raise ValueError("fmt must be 'text' or 'json'")

    if name is None:
        ts_str = (signal.ts or datetime.datetime.utcnow()).strftime("%Y%m%dT%H%M%SZ")
        safe_symbol = signal.symbol.replace("/", "_")
        ext = ".sig" if fmt == "text" else ".sig.json"
        name = f"{safe_symbol}_{signal.side}_{ts_str}{ext}"

    path = folder / name

    if fmt == "text":
        # Simple human-readable format — EA will parse lines
        text = "\n".join(
            [
                f"symbol={signal.symbol}",
                f"side={signal.side}",
                f"volume={signal.volume}",
                f"price={signal.price if signal.price is not None else ''}",
                f"sl_pts={signal.sl_pts if signal.sl_pts is not None else ''}",
                f"tp_pts={signal.tp_pts if signal.tp_pts is not None else ''}",
                f"ts={(signal.ts or datetime.datetime.utcnow()).isoformat()}",
            ]
        )
    else:
        # Build a dict compatible with the versioned SignalV1 schema and
        # validate/serialize it using signal_schema.
        payload = {
            "version": signal_schema.CURRENT_VERSION,
            "symbol": signal.symbol,
            "side": signal.side,
            "volume": signal.volume,
            "price": signal.price,
            "sl_pts": signal.sl_pts,
            "tp_pts": signal.tp_pts,
            "ts": (signal.ts or datetime.datetime.utcnow()).isoformat(),
            # id and meta left to the schema validator
        }
        # validate_signal_dict will raise on invalid payload; it also
        # fills defaults such as id and normalized ts
        sigobj = signal_schema.validate_signal_dict(payload)
        text = signal_schema.dumps(sigobj)

    # Write atomically: create a temp file in the same folder and then
    # rename it into place. This avoids the EA reading a partially
    # written file.
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=str(folder), prefix=name + ".", suffix=".tmp") as tf:
            tf.write(text)
            tf.flush()
            os.fsync(tf.fileno())
            tmp_path = Path(tf.name)

        # Atomic rename/replace
        os.replace(str(tmp_path), str(path))
    except Exception:
        # Cleanup temp file on failure
        try:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise

    return path


__all__ = ["Signal", "write_signal"]
