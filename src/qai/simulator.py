"""Multi-session backtesting simulator utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from .backtester import Backtester, BacktestResult
from .datastore import BacktestDatastore
from .logging_utils import append_signed_audit
from .hmac_utils import verify_audit_stream


logger = logging.getLogger(__name__)


@dataclass
class MultiSessionReport:
    """Aggregate view of multiple backtest sessions."""

    sessions: Dict[str, BacktestResult]
    aggregate: Dict[str, Any]
    summary_path: Optional[Path] = None


class BacktestSimulator:
    """Coordinate multiple backtests and emit structured logging."""

    def __init__(
        self,
        *,
        backtester: Optional[Backtester] = None,
        datastore: Optional[BacktestDatastore] = None,
        audit_log: Optional[Path] = None,
        hmac_key: Optional[str] = None,
    ) -> None:
        self.backtester = backtester or Backtester()
        self.datastore = datastore
        self.audit_log = audit_log
        self.hmac_key = hmac_key

    def run_sessions(
        self,
        sessions: Sequence[Dict[str, Any]],
        *,
        strategy_factory: Optional[
            Callable[[Dict[str, Any]], Callable[[Dict[str, float]], int]]
        ] = None,
        summary_name: str = "multisession_latest",
    ) -> MultiSessionReport:
        if not sessions:
            raise ValueError("No sessions provided for simulation")

        session_results: Dict[str, BacktestResult] = {}
        total_trades = 0
        total_return = 0.0
        best_session_id: Optional[str] = None
        best_session_return = float("-inf")

        initial_entries: List[Dict[str, Any]] = []
        if self.audit_log and self.hmac_key:
            initial_entries = self._read_audit_entries()

        for spec in sessions:
            session_id = spec["session_id"]
            prices = spec["prices"]
            metadata = spec.get("metadata") or {}
            strategy = spec.get("strategy")
            if strategy is None:
                if strategy_factory is None:
                    raise ValueError(f"No strategy provided for session {session_id}")
                strategy = strategy_factory(spec)

            result = self.backtester.run(
                prices,
                strategy,
                session_id=session_id,
                audit_log=self.audit_log,
                datastore=self.datastore,
                metadata=metadata,
                hmac_key=self.hmac_key,
            )
            summary = result.summarize()

            session_results[session_id] = result
            total_trades += summary.get("total_trades", 0)
            total_return += summary.get("net_return", 0.0)
            if summary.get("net_return", float("-inf")) > best_session_return:
                best_session_id = session_id
                best_session_return = summary.get("net_return", float("-inf"))

            self._log_session_summary(session_id, summary, metadata)

        session_count = len(session_results)
        aggregate = {
            "sessions": session_count,
            "total_trades": total_trades,
            "average_net_return": (total_return / session_count) if session_count else 0.0,
            "best_session": best_session_id,
            "best_session_return": best_session_return if best_session_id else None,
        }

        summary_payload = {
            "aggregate": aggregate,
            "sessions": {sid: res.summarize() for sid, res in session_results.items()},
        }
        summary_path: Optional[Path] = None
        if self.datastore is not None:
            summary_path = self.datastore.save_summary(summary_name, summary_payload)

        self._log_aggregate_summary(aggregate, summary_path)

        if self.audit_log is not None:
            append_signed_audit(
                {
                    "module": "qai.simulator",
                    "event": "multi_session_backtest",
                    "aggregate": aggregate,
                    "summary_path": str(summary_path) if summary_path else None,
                },
                audit_log=self.audit_log,
                hmac_key=self.hmac_key,
                session_id="multi-session",
            )

        if self.audit_log and self.hmac_key:
            all_entries = self._read_audit_entries()
            new_entries = all_entries[len(initial_entries) :]
            total, verified, failures = verify_audit_stream(new_entries, self.hmac_key)
            if failures:
                raise ValueError(f"HMAC validation failed: {failures}")

        return MultiSessionReport(
            sessions=session_results,
            aggregate=aggregate,
            summary_path=summary_path,
        )

    def _log_session_summary(
        self,
        session_id: str,
        summary: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> None:
        payload = {
            "type": "backtest.session.summary",
            "session_id": session_id,
            "metrics": summary,
            "metadata": metadata,
        }
        logger.info(json.dumps(payload, ensure_ascii=False))

    def _log_aggregate_summary(
        self,
        aggregate: Dict[str, Any],
        summary_path: Optional[Path],
    ) -> None:
        payload = {
            "type": "backtest.multisession.summary",
            "aggregate": aggregate,
            "summary_path": str(summary_path) if summary_path else None,
        }
        logger.info(json.dumps(payload, ensure_ascii=False))

    def _read_audit_entries(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        if not self.audit_log or not self.audit_log.exists():
            return entries
        for line in self.audit_log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
