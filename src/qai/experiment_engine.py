"""Experiment engine for running parameterized evaluation batches."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TYPE_CHECKING

from .datastore import BacktestDatastore
from .evaluation_pipeline import EvaluationPipeline
from .visualizer import MultiSessionVisualizer
from .dashboard import MultiSessionDashboard
from .logging_utils import append_signed_audit

if TYPE_CHECKING:  # pragma: no cover
    from .visualizer_advanced import AdvancedMultiSessionVisualizer


class ExperimentEngine:
    """Coordinate multi-parameter strategy evaluations and persist results."""

    def __init__(
        self,
        pipeline: Optional[EvaluationPipeline] = None,
        *,
        output_dir: Optional[Path] = None,
        datastore: Optional[BacktestDatastore] = None,
        visualizer: Optional[MultiSessionVisualizer] = None,
        dashboard: Optional[MultiSessionDashboard] = None,
        visualizer_advanced: Optional["AdvancedMultiSessionVisualizer"] = None,
    ) -> None:
        self.pipeline = pipeline or EvaluationPipeline()
        self.datastore = datastore
        self.output_dir = Path(output_dir or "experiments")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.visualizer = visualizer or MultiSessionVisualizer(output_dir=self.output_dir / "visuals")
        self.dashboard = dashboard or MultiSessionDashboard(output_dir=self.output_dir / "dashboards")
        self.visualizer_advanced = visualizer_advanced

    def run_batch(
        self,
        scenarios: Iterable[Dict[str, object]],
        *,
        audit_log: Optional[Path] = None,
        hmac_key: Optional[str] = None,
    ) -> Dict[str, Path]:
        summaries: List[Dict[str, object]] = []
        advanced_sessions: List[Dict[str, object]] = []
        for scenario in scenarios:
            scenario_id = str(scenario.get("id"))
            strategy = scenario["strategy"]
            features = scenario["features"]
            prices = scenario["prices"]
            actual = scenario["actual"]
            pnl = scenario.get("pnl")

            scenario_dir = self.output_dir / scenario_id
            scenario_dir.mkdir(parents=True, exist_ok=True)

            report, result = self.pipeline.evaluate(
                strategy=strategy,
                features=features,
                prices=prices,
                actual=actual,
                pnl=pnl,
                output_dir=scenario_dir,
                session_id=scenario_id,
                audit_log=audit_log,
                hmac_key=hmac_key,
                visualizer=self.visualizer,
                dashboard=self.dashboard,
                visualizer_advanced=self.visualizer_advanced,
                return_result=True,
            )

            summaries.append(
                {
                    "id": scenario_id,
                    "report": report,
                }
            )
            advanced_sessions.append(
                {
                    "session_id": scenario_id,
                    "equity_curve": result.equity_curve,
                    "metrics": report,
                }
            )

            if self.datastore is not None:
                self.datastore.save_run(
                    scenario_id,
                    prices=prices,
                    result=result,
                    metadata={"report": report},
                )

        summary_path = self.output_dir / "experiment_summary.json"
        summary_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")

        csv_path = self.output_dir / "experiment_metrics.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["scenario", "metric", "value"])
            for entry in summaries:
                scenario_id = entry["id"]
                for section, metrics in entry["report"].items():
                    for key, value in metrics.items():
                        writer.writerow([scenario_id, f"{section}.{key}", value])

        if audit_log is not None:
            append_signed_audit(
                {
                    "module": "qai.experiments",
                    "event": "run_batch_complete",
                    "summary": str(summary_path),
                    "count": len(summaries),
                },
                audit_log=audit_log,
                hmac_key=hmac_key,
            )

        if self.visualizer_advanced is not None and advanced_sessions:
            self.visualizer_advanced.render(
                advanced_sessions,
                session_id="experiment-batch",
                audit_log=audit_log,
                hmac_key=hmac_key,
                title="Experiment Scenario Comparison",
            )

        return {"summary": summary_path, "metrics": csv_path}
