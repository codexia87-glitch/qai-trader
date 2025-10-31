"""CI/CD integration helpers with signed audit logging."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

from .integrations import IntegrationsManager
from .logging_utils import append_signed_audit


def _detect_ci_environment() -> str:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions"
    if os.environ.get("GITLAB_CI") == "true":
        return "gitlab-ci"
    if os.environ.get("JENKINS_URL"):
        return "jenkins"
    if os.environ.get("CI") == "true":
        return "generic-ci"
    return "local"


@dataclass
class PipelineResult:
    status: str
    details: Dict[str, Any]


class CIIntegrationManager:
    """Manage external pipeline hooks and artifact transfers with audit logging."""

    def __init__(
        self,
        *,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
        integrations: Optional[IntegrationsManager] = None,
        environment: Optional[str] = None,
    ) -> None:
        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key
        self.environment = environment or _detect_ci_environment()
        self.integrations = integrations or IntegrationsManager(
            audit_log=audit_log,
            session_id=session_id,
            hmac_key=hmac_key,
        )
        self._audit(
            "integration_init",
            {
                "environment": self.environment,
            },
        )

    # ------------------------------------------------------------------
    # Artifact helpers delegated to IntegrationsManager
    # ------------------------------------------------------------------
    def export_csv(self, rows: Sequence[Dict[str, Any]], path: Path) -> Path:
        return self.integrations.export_csv(rows, path)

    def import_csv(self, path: Path) -> Sequence[Dict[str, Any]]:
        return self.integrations.import_csv(path)

    def export_parquet(self, rows: Sequence[Dict[str, Any]], path: Path) -> Path:
        return self.integrations.export_parquet(rows, path)

    def import_parquet(self, path: Path) -> Sequence[Dict[str, Any]]:
        return self.integrations.import_parquet(path)

    def upload_s3(self, local_path: Path, bucket: str, key: str) -> None:
        self.integrations.upload_s3(local_path, bucket, key)

    def download_s3(self, bucket: str, key: str, local_path: Path) -> Path:
        return self.integrations.download_s3(bucket, key, local_path)

    def trigger_ci_hook(self, payload: Dict[str, Any], *, url: Optional[str] = None) -> None:
        self.integrations.trigger_ci_hook(payload, url=url)

    # ------------------------------------------------------------------
    # Pipeline hooks
    # ------------------------------------------------------------------
    def validate_pipeline(self, stage: str, *, artifacts: Optional[Iterable[Path]] = None, notes: Optional[str] = None) -> None:
        payload: Dict[str, Any] = {
            "stage": stage,
            "environment": self.environment,
        }
        if artifacts is not None:
            payload["artifacts"] = [str(Path(item)) for item in artifacts]
        if notes:
            payload["notes"] = notes
        self._audit("pipeline_validate", payload)

    def complete_pipeline(self, status: str, *, details: Optional[Dict[str, Any]] = None) -> PipelineResult:
        payload: Dict[str, Any] = {
            "status": status,
            "environment": self.environment,
        }
        if details:
            payload["details"] = details
        self._audit("pipeline_complete", payload)
        return PipelineResult(status=status, details=details or {})

    def finalize(self, *, notes: Optional[str] = None) -> None:
        payload: Dict[str, Any] = {
            "environment": self.environment,
        }
        if notes:
            payload["notes"] = notes
        self._audit("integration_finalize", payload)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _audit(self, event: str, payload: Dict[str, Any]) -> None:
        if self.audit_log is None:
            return
        entry = {
            "module": "qai.ci",
            "event": event,
            "session_id": self.session_id,
        }
        entry.update(payload)
        append_signed_audit(entry, audit_log=self.audit_log, session_id=self.session_id, hmac_key=self.hmac_key)
