import json
from pathlib import Path

import pytest

from src.qai.integrations_ci import CIIntegrationManager

HMAC_KEY = "ci-hmac-key"


class StubS3Client:
    def __init__(self) -> None:
        self.uploads = {}

    def upload_file(self, filename: str, bucket: str, key: str) -> None:
        self.uploads[(bucket, key)] = Path(filename).read_bytes()

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        Path(filename).write_bytes(self.uploads[(bucket, key)])


def test_ci_manager_detects_github_actions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    manager = CIIntegrationManager(audit_log=audit_path, session_id="ci-demo", hmac_key=HMAC_KEY)

    csv_rows = [{"a": 1}, {"a": 2}]
    csv_path = tmp_path / "artifact.csv"
    manager.export_csv(csv_rows, csv_path)
    assert csv_path.exists()

    manager.validate_pipeline("pre-build", notes="starting build")
    manager.complete_pipeline("passed", details={"stage": "build"})
    manager.finalize(notes="pipeline closed")

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    ci_entries = [entry for entry in entries if entry.get("module") == "qai.ci"]
    events = [entry["event"] for entry in ci_entries]
    assert events == ["integration_init", "pipeline_validate", "pipeline_complete", "integration_finalize"]
    assert ci_entries[0]["environment"] == "github-actions"


def test_ci_manager_artifact_and_hook_flow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("CI", "true")

    s3 = StubS3Client()

    from src.qai import integrations

    monkeypatch.setattr(integrations, "boto3", None)

    manager = CIIntegrationManager(
        audit_log=audit_path,
        session_id="ci-artifacts",
        hmac_key=HMAC_KEY,
        integrations=integrations.IntegrationsManager(
            audit_log=audit_path,
            session_id="ci-artifacts",
            hmac_key=HMAC_KEY,
            s3_client=s3,  # type: ignore[arg-type]
        ),
    )

    csv_path = manager.export_csv([{"k": "v"}], tmp_path / "data.csv")
    parquet_path = manager.export_parquet([{"k": "v"}], tmp_path / "data.parquet")
    manager.upload_s3(csv_path, "bucket", "key.csv")
    downloaded = manager.download_s3("bucket", "key.csv", tmp_path / "download.csv")
    assert downloaded.exists()

    manager.validate_pipeline("post-tests", artifacts=[csv_path, parquet_path])
    result = manager.complete_pipeline("passed", details={"tests": "ok"})

    assert result.status == "passed"
    assert result.details == {"tests": "ok"}

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    ci_entries = [entry for entry in entries if entry.get("module") == "qai.ci"]
    assert ci_entries[1]["event"] == "pipeline_validate"
    assert ci_entries[2]["event"] == "pipeline_complete"
    assert ci_entries[1]["artifacts"][0].endswith("data.csv")
