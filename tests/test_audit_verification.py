import os
import sys
import json
import hmac
import hashlib
import subprocess
from pathlib import Path
import importlib.util
import pytest


# Skip the whole module if QAI_HMAC_KEY is not set in the environment.
if not os.environ.get("QAI_HMAC_KEY"):
    pytest.skip("QAI_HMAC_KEY not set; skipping audit verification tests", allow_module_level=True)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECOVER_SCRIPT = PROJECT_ROOT / "scripts" / "recover_state.py"


def _load_recover_module():
    spec = importlib.util.spec_from_file_location("recover_state", str(RECOVER_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_audit_lines(path: Path, key: str, entries_with_hmac: list, entries_without_hmac: list = None):
    """Helper to write audit.log lines.

    entries_with_hmac: list of dicts that will be HMAC-signed and written
    entries_without_hmac: list of dicts that will be written without hmac (simulating missing signature)
    """
    entries_without_hmac = entries_without_hmac or []
    with path.open("w", encoding="utf-8") as af:
        for e in entries_with_hmac:
            sig = hmac.new(key.encode("utf-8"), json.dumps(e, sort_keys=True, ensure_ascii=False).encode("utf-8"), hashlib.sha256).hexdigest()
            line = dict(e)
            line["hmac"] = sig
            af.write(json.dumps(line, ensure_ascii=False) + "\n")
        for e in entries_without_hmac:
            af.write(json.dumps(e, ensure_ascii=False) + "\n")


def test_verify_audit_log_all_valid(tmp_path):
    key = os.environ.get("QAI_HMAC_KEY")
    audit_path = PROJECT_ROOT / "audit.log"

    # backup existing audit.log if present
    backup = None
    if audit_path.exists():
        backup = audit_path.read_text(encoding="utf-8")

    try:
        entries = [
            {"action": "resume_live", "user": "alice", "ts": "2025-10-30T00:00:00Z"},
            {"action": "emit", "user": "bob", "ts": "2025-10-30T01:00:00Z"},
        ]
        _write_audit_lines(audit_path, key, entries)

        mod = _load_recover_module()
        total, verified, failed, failures = mod.verify_audit_log(key, path=audit_path)

        assert total == 2
        assert verified == 2
        assert failed == 0
        assert failures == []
    finally:
        # restore backup
        if backup is None:
            try:
                audit_path.unlink()
            except Exception:
                pass
        else:
            audit_path.write_text(backup, encoding="utf-8")


def test_verify_audit_log_missing_and_tampered(tmp_path):
    key = os.environ.get("QAI_HMAC_KEY")
    audit_path = PROJECT_ROOT / "audit.log"

    backup = None
    if audit_path.exists():
        backup = audit_path.read_text(encoding="utf-8")

    try:
        # valid entry (we will tamper later)
        good = {"action": "emit", "user": "carol", "ts": "2025-10-30T02:00:00Z"}

        # Create a tampered line: compute signature for original, then change payload before writing
        original = {"action": "sensitive", "user": "mallory", "ts": "2025-10-30T03:00:00Z"}
        sig = hmac.new(key.encode("utf-8"), json.dumps(original, sort_keys=True, ensure_ascii=False).encode("utf-8"), hashlib.sha256).hexdigest()
        tampered = dict(original)
        tampered["action"] = "tampered"

        # Write tampered line but with signature of original (mismatch)
        with audit_path.open("w", encoding="utf-8") as af:
            # missing hmac line
            af.write(json.dumps({"action": "no_hmac", "user": "eve"}, ensure_ascii=False) + "\n")
            # tampered line
            tline = dict(tampered)
            tline["hmac"] = sig
            af.write(json.dumps(tline, ensure_ascii=False) + "\n")

        mod = _load_recover_module()
        total, verified, failed, failures = mod.verify_audit_log(key, path=audit_path)

        assert total == 2
        assert verified == 0
        assert failed == 2
        reasons = {f["reason"] for f in failures}
        assert "MISSING_HMAC" in reasons
        assert "HMAC_MISMATCH" in reasons
    finally:
        if backup is None:
            try:
                audit_path.unlink()
            except Exception:
                pass
        else:
            audit_path.write_text(backup, encoding="utf-8")


def test_cli_verify_only_verbose_detects_corruption(tmp_path):
    key = os.environ.get("QAI_HMAC_KEY")
    audit_path = PROJECT_ROOT / "audit.log"

    backup = None
    if audit_path.exists():
        backup = audit_path.read_text(encoding="utf-8")

    try:
        # create one valid and one tampered line
        good = {"action": "emit", "user": "frank", "ts": "2025-10-30T04:00:00Z"}
        original = {"action": "sensitive", "user": "mallory", "ts": "2025-10-30T05:00:00Z"}
        sig = hmac.new(key.encode("utf-8"), json.dumps(original, sort_keys=True, ensure_ascii=False).encode("utf-8"), hashlib.sha256).hexdigest()
        tampered = dict(original)
        tampered["action"] = "tampered"

        with audit_path.open("w", encoding="utf-8") as af:
            # valid line
            gs = dict(good)
            gs["hmac"] = hmac.new(key.encode("utf-8"), json.dumps(good, sort_keys=True, ensure_ascii=False).encode("utf-8"), hashlib.sha256).hexdigest()
            af.write(json.dumps(gs, ensure_ascii=False) + "\n")
            # tampered line
            tline = dict(tampered)
            tline["hmac"] = sig
            af.write(json.dumps(tline, ensure_ascii=False) + "\n")

        # run the CLI
        env = os.environ.copy()
        env["QAI_HMAC_KEY"] = key
        proc = subprocess.run([sys.executable, str(RECOVER_SCRIPT), "--verify-only", "--verbose"], cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True)

        assert proc.returncode == 1
        assert "Audit verify summary" in proc.stdout
        # expect at least one HMAC_MISMATCH in verbose output
        assert "HMAC_MISMATCH" in proc.stdout or "MISSING_HMAC" in proc.stdout
    finally:
        if backup is None:
            try:
                audit_path.unlink()
            except Exception:
                pass
        else:
            audit_path.write_text(backup, encoding="utf-8")
