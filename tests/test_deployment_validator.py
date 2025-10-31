import hashlib
from pathlib import Path

from src.qai.deployment_validator import DeploymentValidator


def test_deployment_validator_alias(tmp_path: Path):
    path = tmp_path / "artifact.bin"
    path.write_text("data", encoding="utf-8")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()

    manifest = {
        "release": "alias-test",
        "artifacts": [
            {
                "name": "artifact",
                "path": str(path),
                "checksum": checksum,
                "checks": {"ci": True},
            }
        ],
    }

    validator = DeploymentValidator(audit_log=tmp_path / "audit.log", required_checks=("ci",))
    report = validator.validate(manifest)

    assert report.passed is True
    assert report.checked_artifacts == ["artifact"]
