"""
Versioned signal schema and validation for qai-trader bridge.

Sprint 2: define a JSON, versioned signal schema (currently v1) and
provide lightweight validation and (de)serialization helpers. This
module purposely depends only on the Python stdlib so it stays
lightweight and testable without extra deps.

Schema v1 (fields):
  - version: str ("1")
  - symbol: str (non-empty, e.g., "EURUSD")
  - side: str ("BUY" or "SELL")
  - volume: float (positive)
  - price: optional float
  - sl_pts: optional int (>=0)
  - tp_pts: optional int (>=0)
  - ts: ISO8601 timestamp string (if missing a UTC now is set)
  - id: optional unique id (if missing a uuid4 will be generated)
  - meta: optional dict for extensibility

TODO:
- Add stricter type coercion rules as needed
- Add JSON Schema artifact if desired for cross-language validation
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import datetime
import json
import uuid


CURRENT_VERSION = "1"


@dataclass
class SignalV1:
    version: str
    symbol: str
    side: str
    volume: float
    price: Optional[float] = None
    sl_pts: Optional[int] = None
    tp_pts: Optional[int] = None
    ts: str = ""
    id: str = ""
    meta: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Serialize to a compact JSON string."""
        return json.dumps(asdict(self), separators=(",", ":"))


def _ensure_iso_ts(ts: Optional[str]) -> str:
    if ts:
        # validate parseable ISO timestamp
        try:
            # Python 3.11+: fromisoformat supports 'Z' less well; use fromisoformat for RFC3339-ish
            # We'll accept common ISO formats and keep the original string on success.
            datetime.datetime.fromisoformat(ts)
            return ts
        except Exception:
            # As fallback, try parse with strptime common formats
            try:
                datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
                return ts
            except Exception:
                raise ValueError(f"Invalid ISO timestamp: {ts}")
    # missing -> set now in ISO format
    return datetime.datetime.utcnow().isoformat()


def validate_signal_dict(d: Dict[str, Any]) -> SignalV1:
    """Validate an incoming signal dict and return a SignalV1 instance.

    Raises ValueError with clear message on validation failure.
    """
    if not isinstance(d, dict):
        raise ValueError("signal must be a dict")

    version = str(d.get("version", CURRENT_VERSION))
    if version != "1":
        raise ValueError(f"Unsupported signal version: {version}")

    symbol = d.get("symbol")
    if not symbol or not isinstance(symbol, str):
        raise ValueError("'symbol' is required and must be a non-empty string")

    side = d.get("side")
    if side not in ("BUY", "SELL"):
        raise ValueError("'side' must be 'BUY' or 'SELL'")

    volume = d.get("volume")
    try:
        volume = float(volume)
    except Exception:
        raise ValueError("'volume' must be a number")
    if volume <= 0:
        raise ValueError("'volume' must be > 0")

    price = d.get("price")
    if price is not None and price != "":
        try:
            price = float(price)
        except Exception:
            raise ValueError("'price' must be a number if provided")
    else:
        price = None

    def _maybe_int(k: str) -> Optional[int]:
        v = d.get(k)
        if v is None or v == "":
            return None
        try:
            iv = int(v)
        except Exception:
            raise ValueError(f"'{k}' must be an integer if provided")
        if iv < 0:
            raise ValueError(f"'{k}' must be >= 0")
        return iv

    sl_pts = _maybe_int("sl_pts")
    tp_pts = _maybe_int("tp_pts")

    ts_in = d.get("ts")
    ts = _ensure_iso_ts(ts_in)

    id_ = d.get("id") or uuid.uuid4().hex

    meta = d.get("meta")
    if meta is not None and not isinstance(meta, dict):
        raise ValueError("'meta' must be an object/dict if provided")

    return SignalV1(
        version=version,
        symbol=symbol,
        side=side,
        volume=volume,
        price=price,
        sl_pts=sl_pts,
        tp_pts=tp_pts,
        ts=ts,
        id=id_,
        meta=meta,
    )


def loads(s: str) -> SignalV1:
    """Load a JSON string and validate it as SignalV1."""
    try:
        d = json.loads(s)
    except Exception as e:
        raise ValueError(f"invalid json: {e}")
    return validate_signal_dict(d)


def dumps(sig: SignalV1) -> str:
    """Dump SignalV1 to JSON string."""
    return sig.to_json()


__all__ = ["SignalV1", "validate_signal_dict", "loads", "dumps", "CURRENT_VERSION"]
