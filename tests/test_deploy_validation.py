import hashlib
import json
from pathlib import Path

import pytest

from src.qai.deploy_validator import DeployValidator, ValidationIssue, validate_artifacts

HMAC_KEY = "unit-hmac-key"


def _make_artifact(tmp_path: Path, name: str, content: str) -> tuple[Path, str]:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, checksum


def test_successful_validation_logs_audit(tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    artifact_a_path, artifact_a_hash = _make_artifact(tmp_path, "model.bin", "model-bytes")
    artifact_b_path, artifact_b_hash = _make_artifact(tmp_path, "report.json", '{"ok": true}')

    manifest = {
        "release": "v0.5.0",
        "pipeline": {"ci": "github-actions/pr", "smoke": "pytest-smoke"},
        "artifacts": [
            {
                "name": "model",
                "path": str(artifact_a_path),
                "checksum": artifact_a_hash,
                "checks": {"ci": True, "smoke": True},
            },
            {
                "name": "report",
                "path": str(artifact_b_path),
                "checksum": artifact_b_hash,
                "checks": {"ci": True, "smoke": True},
            },
        ],
    }

    validator = DeployValidator(
        audit_log=audit_path,
        session_id="deployment-smoke",
        hmac_key=HMAC_KEY,
        required_checks=("ci", "smoke"),
    )
    report = validator.validate(manifest)

    assert report.passed is True
    assert report.issues == []
    assert sorted(report.checked_artifacts) == ["model", "report"]

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries[-1]["event"] == "experimental_validation_complete"
    assert entries[-1]["artifact_count"] == 2


def test_validation_failure_generates_rollback_plan(tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    artifact_ok_path, artifact_ok_hash = _make_artifact(tmp_path, "bundle.tar.gz", "binary")
    missing_path = tmp_path / "missing.asset"

    manifest = {
        "release": "v0.5.0-rc",
        "artifacts": [
            {
                "name": "bundle",
                "path": str(artifact_ok_path),
                "checksum": artifact_ok_hash,
                "checks": {"ci": True},
            },
            {
                "name": "asset",
                "path": str(missing_path),
                "checksum": "000",
                "checks": {"ci": False},
            },
        ],
    }

    validator = DeployValidator(audit_log=audit_path, required_checks=("ci",))
    report = validator.validate(manifest)

    assert report.passed is False
    assert any(isinstance(issue, ValidationIssue) and issue.artifact == "asset" for issue in report.issues)
    assert "asset" in report.rollback_plan
    assert audit_path.exists() is False

    plan = validator.build_rollback_plan(report, baseline_tag="v0.4.0")
    assert plan["baseline"] == "v0.4.0"
    assert plan["artifacts"][0]["artifact"] == "asset"


def test_validate_artifacts_supports_manifest_path(tmp_path: Path):
    artifact_path, artifact_hash = _make_artifact(tmp_path, "dataset.csv", "value,1")

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "release": "v0.5.0-beta",
                "artifacts": [
                    {
                        "name": "dataset",
                        "path": str(artifact_path),
                        "checksum": artifact_hash,
                        "checks": {"ci": True},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = validate_artifacts(
        manifest_path,
        audit_log=tmp_path / "deploy.log",
        session_id="from-path",
        hmac_key=HMAC_KEY,
    )

    assert report.passed is True
    assert report.manifest_path == manifest_path
