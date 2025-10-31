"""Distributed validation coordinator with redundancy checks and audit logging."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from .logging_utils import append_signed_audit


def _hash_payload(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class NodeResult:
    node_id: str
    status: str
    payload: Any
    hash: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "node_id": self.node_id,
            "status": self.status,
            "payload": self.payload,
        }
        if self.hash is not None:
            data["hash"] = self.hash
        return data


class RedundancyChecker:
    """Verify that validation nodes produced consistent outputs."""

    def evaluate(self, results: Sequence[NodeResult]) -> Dict[str, Any]:
        hashes = {result.node_id: result.hash for result in results if result.hash is not None}
        unique_hashes = {value for value in hashes.values() if value is not None}
        failed_nodes = [result.node_id for result in results if result.status != "success"]
        consistent = len(unique_hashes) <= 1 and not failed_nodes
        if len(unique_hashes) <= 1:
            mismatched_nodes = []
        else:
            mismatched_nodes = list(hashes.keys())

        return {
            "consistent": consistent,
            "hashes": hashes,
            "unique_hashes": list(unique_hashes),
            "failed_nodes": failed_nodes,
            "mismatched_nodes": mismatched_nodes,
        }


class DistributedValidator:
    """Coordinate concurrent validation tasks across multiple nodes."""

    def __init__(
        self,
        *,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
        redundancy_checker: Optional[RedundancyChecker] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key
        self.redundancy_checker = redundancy_checker or RedundancyChecker()
        self.max_workers = max_workers
        self._results: List[NodeResult] = []

    def run_validation_batch(self, inputs: Sequence[Dict[str, Any]]) -> List[NodeResult]:
        """Execute validation callables concurrently."""
        self._results = []
        if not inputs:
            return self._results

        self._audit(
            "init",
            {
                "nodes": [entry.get("node_id", f"node-{idx}") for idx, entry in enumerate(inputs)],
                "count": len(inputs),
            },
        )

        with ThreadPoolExecutor(max_workers=self.max_workers or len(inputs) or 1) as executor:
            futures = {}
            for index, entry in enumerate(inputs):
                node_id = str(entry.get("node_id") or f"node-{index}")
                func: Callable[..., Any] = entry["callable"]
                args = entry.get("args", ())
                kwargs = entry.get("kwargs", {})
                futures[executor.submit(func, *args, **kwargs)] = node_id

            for future in as_completed(futures):
                node_id = futures[future]
                try:
                    payload = future.result()
                    status = "success"
                    digest = _hash_payload(payload)
                except Exception as exc:  # pragma: no cover - error path exercised in tests
                    payload = {"error": str(exc)}
                    status = "error"
                    digest = None
                result = NodeResult(node_id=node_id, status=status, payload=payload, hash=digest)
                self._results.append(result)
                self._audit(
                    "validation_node_result",
                    {
                        "node_id": node_id,
                        "status": status,
                        "hash": digest,
                        "payload": payload,
                    },
                )

        return self._results

    def consolidate_results(self) -> Dict[str, Any]:
        """Compare node results and emit a consolidated audit entry."""
        summary = self.redundancy_checker.evaluate(self._results)
        summary.update(
            {
                "node_count": len(self._results),
                "successful_nodes": [result.node_id for result in self._results if result.status == "success"],
            }
        )
        self.emit_signed_event(payload=summary)
        return summary

    def emit_signed_event(
        self,
        *,
        event_name: str = "validation_complete",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a final signed event summarising the distributed validation."""
        self._audit(event_name, payload or {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _audit(self, event: str, payload: Dict[str, Any]) -> None:
        if self.audit_log is None:
            return
        entry = {
            "module": "qai.distributed",
            "event": f"qai.distributed/{event}",
            "session_id": self.session_id,
        }
        entry.update(payload)
        append_signed_audit(
            entry,
            audit_log=self.audit_log,
            session_id=self.session_id,
            hmac_key=self.hmac_key,
        )
