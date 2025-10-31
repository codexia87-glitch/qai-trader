import json
from pathlib import Path
from typing import Any, Dict

import pytest

from src.qai.distributed_validator import DistributedValidator, RedundancyChecker

HMAC_KEY = "distributed-hmac"


def _node_success(payload: Dict[str, Any]) -> Dict[str, Any]:
    return payload


def _node_failure() -> Dict[str, Any]:  # pragma: no cover - exercised in tests
    raise RuntimeError("node error")


def test_distributed_validator_success(tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    validator = DistributedValidator(audit_log=audit_path, session_id="dist", hmac_key=HMAC_KEY)

    inputs = [
        {"node_id": "n1", "callable": _node_success, "args": ({"value": 1},)},
        {"node_id": "n2", "callable": _node_success, "args": ({"value": 1},)},
    ]

    results = validator.run_validation_batch(inputs)
    assert len(results) == 2
    summary = validator.consolidate_results()
    assert summary["consistent"] is True
    assert summary["failed_nodes"] == []

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    events = [entry["event"] for entry in entries]
    assert events.count("qai.distributed/init") == 1
    assert events.count("qai.distributed/validation_node_result") == 2
    assert events[-1] == "qai.distributed/validation_complete"


def test_distributed_validator_detects_mismatch(tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    checker = RedundancyChecker()
    validator = DistributedValidator(
        audit_log=audit_path,
        session_id="dist-mismatch",
        hmac_key=HMAC_KEY,
        redundancy_checker=checker,
    )

    inputs = [
        {"node_id": "n1", "callable": _node_success, "args": ({"value": 1},)},
        {"node_id": "n2", "callable": _node_success, "args": ({"value": 2},)},
    ]

    validator.run_validation_batch(inputs)
    summary = validator.consolidate_results()
    assert summary["consistent"] is False
    assert set(summary["mismatched_nodes"]) == {"n1", "n2"}


def test_distributed_validator_handles_failure(tmp_path: Path):
    audit_path = tmp_path / "audit.log"
    validator = DistributedValidator(audit_log=audit_path, session_id="dist-failure", hmac_key=HMAC_KEY)

    inputs = [
        {"node_id": "n1", "callable": _node_success, "args": ({"value": 1},)},
        {"node_id": "n2", "callable": _node_failure},
    ]

    results = validator.run_validation_batch(inputs)
    statuses = {result.node_id: result.status for result in results}
    assert statuses["n1"] == "success"
    assert statuses["n2"] == "error"

    summary = validator.consolidate_results()
    assert summary["failed_nodes"] == ["n2"]
    assert summary["consistent"] is False
