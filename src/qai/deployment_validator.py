"""Backward-compatibility wrapper for deployment validation."""

from __future__ import annotations

from .deploy_validator import DeployValidator, ValidationIssue, ValidationReport, validate_artifacts


class DeploymentValidator(DeployValidator):
    """Alias class preserved for historical imports."""

    __doc__ = DeployValidator.__doc__


__all__ = [
    "DeploymentValidator",
    "DeployValidator",
    "ValidationIssue",
    "ValidationReport",
    "validate_artifacts",
]
