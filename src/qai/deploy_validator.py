"""Deployment validation utilities for QAI Trader."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from .logging_utils import append_signed_audit

REQUIRED_CHECKS: Sequence[str] = ("ci",)


@dataclass
class ValidationIssue:
    """Represents a single validation problem."""

    artifact: str
    message: str
    check: Optional[str] = None
    severity: str = "error"


@dataclass
class ValidationReport:
    """Summary of a validation run."""

    release: str
    passed: bool
    checked_artifacts: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    rollback_plan: List[str] = field(default_factory=list)
    manifest_path: Optional[Path] = None

    def raise_on_failure(self) -> None:
        if not self.passed:
            details = ", ".join(f"{issue.artifact}: {issue.message}" for issue in self.issues)
            raise RuntimeError(f"Deployment validation failed: {details}")


class DeployValidator:
    """Validate deployment artifacts before an experimental release."""

    def __init__(
        self,
        *,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
        required_checks: Sequence[str] = REQUIRED_CHECKS,
    ) -> None:
        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key
        self.required_checks = tuple(required_checks)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def validate(
        self,
        manifest: Union[Dict[str, Any], Path],
        *,
        raise_on_failure: bool = False,
    ) -> ValidationReport:
        manifest_dict, manifest_path = self._load_manifest(manifest)

        release = str(manifest_dict.get("release") or manifest_dict.get("version") or "unknown")
        artifacts: Iterable[Dict[str, Any]] = manifest_dict.get("artifacts", [])

        checked: List[str] = []
        issues: List[ValidationIssue] = []
        rollback: List[str] = []

        for item in artifacts:
            name = str(item.get("name") or item.get("path") or "unknown")
            path_value = item.get("path")
            if not path_value:
                issues.append(ValidationIssue(name, "missing artifact path"))
                rollback.append(name)
                continue

            path = Path(path_value)
            if not path.exists():
                issues.append(ValidationIssue(name, f"artifact not found at {path}"))
                rollback.append(name)
                continue

            checked.append(name)

            expected_checksum = item.get("checksum")
            if expected_checksum:
                actual_checksum = self._sha256(path)
                if actual_checksum != expected_checksum:
                    issues.append(
                        ValidationIssue(
                            name,
                            "checksum mismatch",
                            check="checksum",
                        )
                    )
                    rollback.append(name)
                    continue

            artifact_checks = item.get("checks", {})
            missing_checks = [
                check for check in self.required_checks if not artifact_checks.get(check, False)
            ]
            if missing_checks:
                for check in missing_checks:
                    issues.append(
                        ValidationIssue(
                            name,
                            f"required check '{check}' not passed",
                            check=check,
                        )
                    )
                rollback.append(name)

        passed = not issues
        report = ValidationReport(
            release=release,
            passed=passed,
            checked_artifacts=checked,
            issues=issues,
            rollback_plan=sorted(set(rollback)),
            manifest_path=manifest_path,
        )

        if passed:
            self._audit_success(report, manifest_dict)
        elif raise_on_failure:
            report.raise_on_failure()

        return report

    def build_rollback_plan(
        self,
        report: ValidationReport,
        *,
        baseline_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a simple rollback plan for failed artifacts."""
        plan = {
            "release": report.release,
            "baseline": baseline_tag,
            "artifacts": [],
        }
        for artifact in report.rollback_plan:
            plan["artifacts"].append(
                {
                    "artifact": artifact,
                    "action": "restore_from_baseline",
                    "target_tag": baseline_tag or "previous-stable",
                }
            )
        return plan

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_manifest(
        self,
        manifest: Union[Dict[str, Any], Path],
    ) -> tuple[Dict[str, Any], Optional[Path]]:
        if isinstance(manifest, Path):
            manifest_dict = json.loads(manifest.read_text(encoding="utf-8"))
            return manifest_dict, manifest
        return manifest, None

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _audit_success(self, report: ValidationReport, manifest: Dict[str, Any]) -> None:
        payload = {
            "module": "qai.deploy",
            "event": "experimental_validation_complete",
            "release": report.release,
            "artifact_count": len(report.checked_artifacts),
            "manifest": str(report.manifest_path) if report.manifest_path else None,
            "required_checks": list(self.required_checks),
        }
        if manifest.get("pipeline"):
            payload["pipeline"] = manifest["pipeline"]
        append_signed_audit(
            payload,
            audit_log=self.audit_log,
            session_id=self.session_id,
            hmac_key=self.hmac_key,
        )


def validate_artifacts(
    manifest: Union[Dict[str, Any], Path],
    *,
    audit_log: Optional[Path] = None,
    session_id: Optional[str] = None,
    hmac_key: Optional[str] = None,
    required_checks: Sequence[str] = REQUIRED_CHECKS,
) -> ValidationReport:
    """Convenience wrapper around DeployValidator.validate."""
    validator = DeployValidator(
        audit_log=audit_log,
        session_id=session_id,
        hmac_key=hmac_key,
        required_checks=required_checks,
    )
    return validator.validate(manifest)
