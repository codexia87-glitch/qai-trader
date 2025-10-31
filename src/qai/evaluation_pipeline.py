"""Evaluation pipeline for adaptive strategy scoring."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple, Union

from .adaptive_strategy import AdaptiveStrategy
from .backtester import Backtester, BacktestResult
from .metrics_adaptive import AdaptiveMetrics
from .visualizer import MultiSessionVisualizer
from .dashboard import MultiSessionDashboard
from .model_predictor import ModelPredictor
from .logging_utils import append_signed_audit
from .security_validator import SecurityValidator


class EvaluationPipeline:
    """Orchestrates predictor scoring, adaptive metrics, and reporting."""

    def __init__(
        self,
        predictor: Optional[ModelPredictor] = None,
        backtester: Optional[Backtester] = None,
    ) -> None:
        self.predictor = predictor or ModelPredictor(input_size=2)
        self.backtester = backtester or Backtester()

    def evaluate(
        self,
        *,
        strategy,
        features: Iterable[Sequence[float]],
        prices: Sequence[Dict[str, float]],
        actual: Sequence[float],
        pnl: Optional[Sequence[float]] = None,
        output_dir: Optional[Path] = None,
        session_id: Optional[str] = None,
        audit_log: Optional[Path] = None,
        hmac_key: Optional[str] = None,
        visualizer: Optional[MultiSessionVisualizer] = None,
        dashboard: Optional[MultiSessionDashboard] = None,
        return_result: bool = False,
        security_validator: Optional[SecurityValidator] = None,
    ) -> Union[Dict[str, Dict[str, float]], Tuple[Dict[str, Dict[str, float]], BacktestResult]]:
        output_dir = Path(output_dir or Path("reports"))
        output_dir.mkdir(parents=True, exist_ok=True)

        predictions, scoring_metrics = self.predictor.batch_predict(
            list(features),
            actual=list(actual),
            pnl=list(pnl) if pnl is not None else None,
            audit_log=audit_log,
            session_id=session_id,
            hmac_key=hmac_key,
        )

        adaptive_metrics = AdaptiveMetrics()
        adaptive_metrics.update_stability(scoring_metrics["stability"])

        result = self.backtester.run(
            prices,
            strategy,
            session_id=session_id,
            audit_log=audit_log,
            adaptive_metrics=adaptive_metrics,
            metrics_audit_log=audit_log,
            metrics_session_id=session_id,
            hmac_key=hmac_key,
        )

        adaptive_kpis = adaptive_metrics.compute().to_dict()
        report = {
            "scoring": scoring_metrics,
            "backtest": result.metrics,
            "adaptive": adaptive_kpis,
        }

        if security_validator is not None:
            dataset = [
                {"prediction": p, "actual": a}
                for p, a in zip(predictions, actual)
            ]
            security_validator.audit_report(
                dataset,
                audit_log=audit_log,
                session_id=session_id,
                hmac_key=hmac_key,
            )

        report_path = output_dir / f"{session_id or 'evaluation'}_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        csv_path = output_dir / f"{session_id or 'evaluation'}_metrics.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["metric", "value"])
            for section in ("scoring", "adaptive"):
                for key, value in report[section].items():
                    writer.writerow([f"{section}.{key}", value])

        if audit_log is not None:
            append_signed_audit(
                {
                    "module": "qai.pipeline",
                    "event": "evaluation_complete",
                    "session_id": session_id,
                    "report": report,
                },
                audit_log=audit_log,
                session_id=session_id,
                hmac_key=hmac_key,
            )

        if visualizer is not None:
            visualizer.render(
                [
                    {
                        "session_id": session_id or "evaluation",
                        "equity_curve": result.equity_curve,
                        "metrics": report["adaptive"],
                    }
                ],
                session_id=session_id,
                audit_log=audit_log,
                hmac_key=hmac_key,
            )

        if dashboard is not None:
            dashboard.render(
                [
                    {
                        "session_id": session_id or "evaluation",
                        "equity_curve": result.equity_curve,
                        "metrics": report,
                    }
                ],
                session_id=session_id,
                audit_log=audit_log,
                hmac_key=hmac_key,
            )

        if return_result:
            return report, result
        return report
