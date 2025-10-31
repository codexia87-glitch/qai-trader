"""Lightweight backtesting harness for QAI Trader."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Container for backtest outcomes."""

    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Append a trade to the result set."""
        self.trades.append(trade)

    def summarize(self) -> Dict[str, float]:
        """Compute a minimal summary view of the run."""
        wins = sum(1 for t in self.trades if t.get("pnl", 0.0) > 0)
        losses = sum(1 for t in self.trades if t.get("pnl", 0.0) <= 0)
        total = len(self.trades) or 1
        self.metrics.setdefault("total_trades", len(self.trades))
        self.metrics.setdefault("wins", wins)
        self.metrics.setdefault("losses", losses)
        self.metrics.setdefault("win_rate", wins / total)
        if self.equity_curve:
            self.metrics.setdefault("ending_equity", self.equity_curve[-1])
        return self.metrics


class Backtester:
    """Simple portfolio simulator that applies a strategy to price data."""

    def __init__(
        self,
        initial_capital: float = 10_000.0,
        risk_per_trade: float = 0.01,
        slippage: float = 0.0,
    ) -> None:
        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not 0 < risk_per_trade <= 1:
            raise ValueError("risk_per_trade must be between 0 and 1")

        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.slippage = slippage

    def run(
        self,
        prices: Sequence[Dict[str, float]],
        strategy: Callable[[Dict[str, float]], int],
        session_id: Optional[str] = None,
        audit_log: Optional[Path] = None,
    ) -> BacktestResult:
        """Execute a backtest using the provided strategy callable.

        `prices` must be an iterable of dicts containing at least `open` and `close`.
        `strategy` should return -1, 0, or 1 for short/flat/long positions.
        """
        result = BacktestResult()
        equity = self.initial_capital
        position = 0
        entry_price = 0.0

        for idx, bar in enumerate(prices):
            if not {"open", "close"} <= bar.keys():
                raise ValueError("Each price bar must contain 'open' and 'close' keys")
            signal = strategy(bar)
            logger.debug("bar=%s signal=%s position=%s", idx, signal, position)

            if signal not in (-1, 0, 1):
                raise ValueError("Strategy must return -1, 0, or 1")

            # Exit if signal flips or we go flat
            if position != 0 and signal != position:
                pnl = (bar["open"] - entry_price) * position
                pnl -= self.slippage
                equity += pnl
                trade = {
                    "index": idx,
                    "direction": position,
                    "entry": entry_price,
                    "exit": bar["open"],
                    "pnl": pnl,
                }
                result.add_trade(trade)
                logger.debug("closed trade=%s", trade)
                position = 0

            # Enter new position
            if position == 0 and signal != 0:
                risk_amount = equity * self.risk_per_trade
                position = signal
                entry_price = bar["open"]
                logger.debug(
                    "opening position direction=%s entry=%s risk=%.2f",
                    position,
                    entry_price,
                    risk_amount,
                )

            result.equity_curve.append(equity)

        # Close any open position at final close
        if position != 0:
            pnl = (prices[-1]["close"] - entry_price) * position
            pnl -= self.slippage
            equity += pnl
            trade = {
                "index": len(prices) - 1,
                "direction": position,
                "entry": entry_price,
                "exit": prices[-1]["close"],
                "pnl": pnl,
            }
            result.add_trade(trade)
            result.equity_curve[-1] = equity
            logger.debug("closed final trade=%s", trade)

        result.metrics["starting_equity"] = self.initial_capital
        result.metrics["ending_equity"] = equity
        result.metrics["net_return"] = (equity / self.initial_capital) - 1

        if audit_log is not None:
            self._append_audit_entry(result, session_id=session_id, audit_log=audit_log)

        return result

    def _append_audit_entry(
        self,
        result: BacktestResult,
        session_id: Optional[str],
        audit_log: Path,
    ) -> None:
        """Append a summary line to the audit log if available."""
        try:
            entry = {
                "module": "qai.backtester",
                "session_id": session_id,
                "total_trades": len(result.trades),
                "net_return": result.metrics.get("net_return"),
            }
            from .logging_utils import append_signed_audit  # lazy import

            append_signed_audit(entry, audit_log=audit_log)
        except Exception as exc:  # pragma: no cover - logging path is best-effort
            logger.warning("Failed to append backtest audit entry: %s", exc)
