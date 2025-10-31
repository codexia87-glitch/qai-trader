import json
from pathlib import Path

from src.qai.security_validator import SecurityValidator

HMAC_KEY = "unit-hmac-key"


def test_security_validator_detects_issues(tmp_path: Path):
    audit_path = tmp_path / "security.log"
    validator = SecurityValidator(allowed_fields=["prediction", "actual"])

    dataset = [
        {"prediction": 0.5, "actual": 0.4},
        {"prediction": 2000000, "actual": 0.3},
        {"prediction": None, "actual": "password123"},
    ]

    report = validator.audit_report(
        dataset,
        audit_log=audit_path,
        session_id="security-test",
        hmac_key=HMAC_KEY,
    )

    assert not report["compliant"]
    assert any(issue["severity"] == "error" for issue in report["issues"])

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries and entries[-1]["event"] == "validation_complete"
    assert isinstance(entries[-1].get("hmac"), str)
