"""Data security and compliance validation for QAI pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .logging_utils import append_signed_audit


@dataclass
class ValidationIssue:
    message: str
    severity: str = "warning"


class SecurityValidator:
    """Validate datasets for anomalies and compliance before persistence."""

    def __init__(self, *, allowed_fields: Optional[Sequence[str]] = None) -> None:
        self.allowed_fields = allowed_fields

    def validate_dataset(self, dataset: Iterable[Dict[str, object]]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        for idx, row in enumerate(dataset):
            if self.allowed_fields:
                extra_fields = set(row.keys()) - set(self.allowed_fields)
                if extra_fields:
                    issues.append(ValidationIssue(f"Row {idx}: unexpected fields {extra_fields}", "error"))
            for key, value in row.items():
                if value is None:
                    issues.append(ValidationIssue(f"Row {idx}, field {key}: null value", "warning"))
                if isinstance(value, (int, float)) and abs(value) > 1e6:
                    issues.append(ValidationIssue(f"Row {idx}, field {key}: value out of range", "error"))
        return issues

    def check_compliance(self, dataset: Iterable[Dict[str, object]]) -> bool:
        for row in dataset:
            if any(isinstance(value, str) and "password" in value.lower() for value in row.values() if isinstance(value, str)):
                return False
        return True

    def audit_report(
        self,
        dataset: Iterable[Dict[str, object]],
        *,
        audit_log: Optional[Path],
        session_id: Optional[str],
        hmac_key: Optional[str] = None,
    ) -> Dict[str, object]:
        issues = self.validate_dataset(dataset)
        compliant = self.check_compliance(dataset)
        report = {
            "issues": [issue.__dict__ for issue in issues],
            "compliant": compliant,
        }
        if audit_log is not None:
            append_signed_audit(
                {
                    "module": "qai.security",
                    "event": "validation_complete",
                    "session_id": session_id,
                    "report": report,
                },
                audit_log=audit_log,
                session_id=session_id,
                hmac_key=hmac_key,
            )
        return report
