"""
MT5-side helper: read `*.sig.json`, validate, and send orders via MetaTrader5 API.

This module provides functions to:
- connect to MetaTrader5 using environment credentials (or params)
- process a folder of `.sig.json` files: validate via `signal_schema`,
  compute prices (ask/bid), and send market orders.

CAUTION: This code can send real orders if run with `--live` and valid
MT5 credentials. By default the CLI uses `--dry-run` to avoid accidental
trades. Always test in a demo account first.

Dependencies: the `MetaTrader5` Python package must be installed to
enable live trading. When it's not available the module can still be
used in dry-run mode.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, List
import os
import json
import time

try:
    import MetaTrader5 as mt5  # type: ignore
    MT5_AVAILABLE = True
except Exception:
    MT5_AVAILABLE = False

from . import signal_schema


def connect(account: Optional[int] = None, password: Optional[str] = None, server: Optional[str] = None) -> bool:
    """Initialize and optionally login to MetaTrader5 terminal.

    If `account` is provided the function attempts to log in. Returns
    True on success.
    """
    if not MT5_AVAILABLE:
        raise RuntimeError("MetaTrader5 package not installed; cannot connect")

    ok = mt5.initialize()
    if not ok:
        return False

    if account is not None:
        # Some MT5 setups require server and password on login
        res = mt5.login(account, password=password, server=server)
        return res

    return True


def _send_order_live(sig: signal_schema.SignalV1, deviation: int = 10) -> Dict[str, Any]:
    """Send a market order using MetaTrader5 API. Returns the result dict.

    Raises RuntimeError if MT5 is not available or not initialized.
    """
    if not MT5_AVAILABLE:
        raise RuntimeError("MetaTrader5 package not available")

    symbol = sig.symbol
    # Ensure symbol is available
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Symbol not found: {symbol}")

    # Ensure symbol is visible/enabled
    if not info.visible:
        mt5.symbol_select(symbol, True)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"Could not get tick for {symbol}")

    price = sig.price
    if price is None:
        # choose appropriate side price
        price = tick.ask if sig.side == "BUY" else tick.bid

    point = info.point
    sl = None
    tp = None
    if sig.sl_pts is not None:
        if sig.side == "BUY":
            sl = price - sig.sl_pts * point
        else:
            sl = price + sig.sl_pts * point
    if sig.tp_pts is not None:
        if sig.side == "BUY":
            tp = price + sig.tp_pts * point
        else:
            tp = price - sig.tp_pts * point

    order_type = mt5.ORDER_TYPE_BUY if sig.side == "BUY" else mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(sig.volume),
        "type": order_type,
        "price": float(price),
        "sl": float(sl) if sl is not None else None,
        "tp": float(tp) if tp is not None else None,
        "deviation": deviation,
        "magic": 0,
        "comment": "qai-signal",
        "type_filling": mt5.ORDER_FILLING_FOK if info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL else mt5.ORDER_FILLING_IOC,
    }

    # Clean None values for mt5.order_send
    request = {k: v for k, v in request.items() if v is not None}

    result = mt5.order_send(request)
    # Convert result to dict-like
    try:
        return result._asdict()  # type: ignore[attr-defined]
    except Exception:
        # Fallback to str
        return {"result": str(result)}


def process_sig_file(path: Path, live: bool = False, connect_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process a single .sig.json file: validate, optionally send order.

    Returns a dict with processing result and any order response.
    """
    text = path.read_text(encoding="utf-8")
    try:
        sig = signal_schema.loads(text)
    except Exception as e:
        raise ValueError(f"Invalid signal JSON in {path}: {e}")

    if live:
        # connect if needed
        if connect_params:
            connect(**connect_params)
        if not MT5_AVAILABLE:
            raise RuntimeError("MT5 package not available for live trading")
        order_res = _send_order_live(sig)
    else:
        # dry-run: simulate order send
        order_res = {
            "status": "dry_run",
            "symbol": sig.symbol,
            "side": sig.side,
            "volume": sig.volume,
        }

    return {"signal": sig, "order_result": order_res}


def process_folder(folder: Path, live: bool = False, connect_params: Optional[Dict[str, Any]] = None, move_archived: bool = True) -> List[Dict[str, Any]]:
    """Process all `*.sig.json` files in `folder`.

    Returns a list of results. Files are moved to `archived/` on
    success or `failed/` on error.
    """
    folder = Path(folder)
    if not folder.exists():
        return []

    results: List[Dict[str, Any]] = []
    for p in sorted(folder.glob("*.sig.json")):
        try:
            res = process_sig_file(p, live=live, connect_params=connect_params)
            if move_archived:
                archived = folder / "archived"
                archived.mkdir(parents=True, exist_ok=True)
                os.replace(str(p), str(archived / p.name))
            results.append({"path": p, "status": "ok", "res": res})
        except Exception as e:
            failed = folder / "failed"
            failed.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(str(p), str(failed / p.name))
            except Exception:
                pass
            results.append({"path": p, "status": "error", "error": str(e)})

    return results


__all__ = ["connect", "process_sig_file", "process_folder"]
