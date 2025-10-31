"""Utilities for writing HMAC-signed audit events with session metadata."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import hmac
import json
import os
import platform
import socket
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_PATH = PROJECT_ROOT / "audit.log"


def _default_session_info() -> Dict[str, Any]:
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    info: Dict[str, Any] = {
        "user": username,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
    }
    try:
        info["pid"] = os.getpid()
    except Exception:
        pass
    return info


def append_signed_audit(
    payload: Dict[str, Any],
    *,
    audit_log: Optional[Path] = None,
    session_id: Optional[str] = None,
    hmac_key: Optional[str] = None,
) -> None:
    """Append an audit entry enriched with session metadata and HMAC signature."""
    audit_path = audit_log or DEFAULT_AUDIT_PATH
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    entry = dict(payload)
    if session_id:
        entry["session_id"] = session_id
    ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    entry.setdefault("ts", ts)

    session_info = entry.setdefault("session", {})
    for key, value in _default_session_info().items():
        session_info.setdefault(key, value)

    key = hmac_key or os.environ.get("QAI_HMAC_KEY")
    signature: Optional[str] = None
    if key:
        msg = json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")
        signature = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    entry["hmac"] = signature

    with audit_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
