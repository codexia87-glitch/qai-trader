"""Utilities to validate post-backtest audit entries."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class HMACFailure:
    index: int
    reason: str
    entry: Dict[str, Any]


def _normalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {k: v for k, v in entry.items() if k != "hmac"}
    return normalized


def verify_audit_stream(
    entries: Iterable[Dict[str, Any]],
    key: str,
) -> Tuple[int, int, List[HMACFailure]]:
    total = 0
    verified = 0
    failures: List[HMACFailure] = []

    for idx, entry in enumerate(entries):
        total += 1
        signature = entry.get("hmac")
        if not signature:
            failures.append(HMACFailure(index=idx, reason="MISSING_HMAC", entry=entry))
            continue

        normalized = _normalize_entry(entry)
        digest = hmac.new(key.encode("utf-8"), json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, digest):
            failures.append(HMACFailure(index=idx, reason="HMAC_MISMATCH", entry=entry))
            continue

        verified += 1

    return total, verified, failures


def verify_audit_file(path: Path, key: str) -> Tuple[int, int, List[HMACFailure]]:
    entries: List[Dict[str, Any]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            entries.append({"raw": line, "error": str(exc), "hmac": None})
    return verify_audit_stream(entries, key)
