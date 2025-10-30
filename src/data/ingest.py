"""
Data ingestion stubs for qai-trader.

Sprint 4: provide a clearly documented DataLoader interface that future
connectors (live feeds, historical CSVs, database, or API) will
implement. This file intentionally contains no network or IO logic —
only interfaces and minimal local helpers for tests.

Contract (small):
- DataLoader should provide `fetch(start, end)` -> iterable of records
- `schema()` returns a description of returned fields

Edge cases to handle later:
- large streaming windows, backfills, missing values, timezone handling
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Dict, Any, Optional


class DataLoader:
    """Abstract-ish DataLoader.

    Implementations should override `fetch`. This minimal base class
    is used by tests and higher-level pipelines during Sprint 4.
    """

    def schema(self) -> Dict[str, str]:
        """Return a mapping of field name -> type description."""
        return {"timestamp": "datetime", "symbol": "str", "price": "float"}

    def fetch(self, start: Optional[datetime] = None, end: Optional[datetime] = None) -> Iterable[Dict[str, Any]]:
        """Fetch records between start and end. Must be implemented by subclasses.

        Here we raise NotImplementedError in the stub.
        """
        raise NotImplementedError()


@dataclass
class InMemoryLoader(DataLoader):
    """A tiny in-memory loader used for tests and examples.

    Holds a list of dict records and yields those that fall within the
    optional start/end window.
    """
    records: list

    def fetch(self, start: Optional[datetime] = None, end: Optional[datetime] = None):
        for r in self.records:
            ts = r.get("timestamp")
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            yield r


__all__ = ["DataLoader", "InMemoryLoader"]
