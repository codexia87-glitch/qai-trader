import json
from pathlib import Path

import pytest

from src.qai.integrations import IntegrationsManager

HMAC_KEY = "unit-hmac-key"


class StubS3Client:
    def __init__(self) -> None:
        self.storage = {}
        self.uploads = []

    def upload_file(self, filename: str, bucket: str, key: str) -> None:
        data = Path(filename).read_bytes()
        self.storage[(bucket, key)] = data
        self.uploads.append((filename, bucket, key))

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        data = self.storage[(bucket, key)]
        Path(filename).write_bytes(data)


class StubRequests:
    def __init__(self) -> None:
        self.calls = []

    def post(self, url: str, json: dict, timeout: int) -> None:  # type: ignore[override]
        self.calls.append((url, json, timeout))


def test_csv_export_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    audit_path = tmp_path / "integrations.log"
    manager = IntegrationsManager(audit_log=audit_path, session_id="csv", hmac_key=HMAC_KEY)
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]

    csv_path = manager.export_csv(rows, tmp_path / "data.csv")
    assert csv_path.exists()

    imported = manager.import_csv(csv_path)
    assert imported == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]

    events = [json.loads(line)["event"] for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert events.count("export_complete") == 1
    assert events.count("import_complete") == 1


def test_parquet_export_import(tmp_path: Path):
    audit_path = tmp_path / "integrations.log"
    manager = IntegrationsManager(audit_log=audit_path, session_id="parquet", hmac_key=HMAC_KEY)
    rows = [{"a": 1.0, "b": "x"}]

    pq_path = manager.export_parquet(rows, tmp_path / "data.parquet")
    assert pq_path.exists()

    imported = manager.import_parquet(pq_path)
    assert len(imported) == 1
    assert imported[0]["a"] in (1.0, "1.0")


def test_s3_upload_download(tmp_path: Path):
    audit_path = tmp_path / "integrations.log"
    s3 = StubS3Client()
    manager = IntegrationsManager(audit_log=audit_path, session_id="s3", hmac_key=HMAC_KEY, s3_client=s3)

    local = tmp_path / "file.csv"
    local.write_text("value", encoding="utf-8")

    manager.upload_s3(local, "bucket", "key")
    download_path = manager.download_s3("bucket", "key", tmp_path / "downloaded.csv")
    assert download_path.read_text(encoding="utf-8") == "value"


def test_ci_hook(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    audit_path = tmp_path / "integrations.log"
    stub = StubRequests()
    monkeypatch.setattr("src.qai.integrations.requests", stub)

    manager = IntegrationsManager(audit_log=audit_path, session_id="ci", hmac_key=HMAC_KEY)
    manager.trigger_ci_hook({"ok": True}, url="https://ci.example/hook")
    assert stub.calls == [("https://ci.example/hook", {"ok": True}, 10)]

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries[-1]["event"] == "ci_hook_triggered"
