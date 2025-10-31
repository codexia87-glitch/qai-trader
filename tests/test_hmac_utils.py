import json
from pathlib import Path

from src.qai.hmac_utils import HMACFailure, verify_audit_file, verify_audit_stream


def test_verify_audit_stream_success():
    key = "unit-hmac-key"
    entries = [
        {
            "module": "qai.simulator",
            "payload": 1,
        },
        {
            "module": "qai.simulator",
            "payload": 2,
        },
    ]

    signed = []
    import hmac
    import hashlib

    for entry in entries:
        normalized = json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hmac.new(key.encode("utf-8"), normalized, hashlib.sha256).hexdigest()
        signed.append({**entry, "hmac": digest})

    total, verified, failures = verify_audit_stream(signed, key)
    assert total == 2
    assert verified == 2
    assert failures == []


def test_verify_audit_file_detects_failures(tmp_path: Path):
    key = "unit-hmac-key"
    path = tmp_path / "audit.log"
    content = [
        {"module": "ok", "value": 1, "hmac": "bad"},
        {"module": "no-hmac", "value": 2},
    ]
    path.write_text("\n".join(json.dumps(entry) for entry in content), encoding="utf-8")

    total, verified, failures = verify_audit_file(path, key)
    assert total == 2
    assert verified == 0
    assert len(failures) == 2
    reasons = {f.reason for f in failures}
    assert "MISSING_HMAC" in reasons
    assert "HMAC_MISMATCH" in reasons
