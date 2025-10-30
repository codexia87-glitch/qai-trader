# Changelog

All notable changes to this project will be documented in this file.

## [v0.1.0] - 2025-10-30
Initial release — Quantum AI Trader base release

### Added
- Audit and HMAC verification system
  - Append-only `audit.log` with HMAC-SHA256 signatures using `QAI_HMAC_KEY`.
  - `verify_audit_log` helper and `recover_state.py` integration to block unsafe resumes when integrity fails.
- Automated CI workflow (GitHub Actions)
  - `.github/workflows/test_audit_verification.yml` runs HMAC verification tests on push & PRs.
- Quantum AI trading core scaffolding (ML + PyTorch integration)
  - Lazy PyTorch LSTM model factory, trainer skeleton, save/load & checkpoint hooks.
- JSON schema and simulator bridge
  - File-based signal schema (`.sig.json`) and simulator/MT5 bridge stubs for offline testing.
- Recovery and checkpoint system
  - Project-level `.qai_state.json`, checkpoint manager, audit trail, and recovery CLI `scripts/recover_state.py`.

### Notes
- Optional dependencies: PyTorch and MetaTrader5 are lazy-imported; tests and autoload require installing them to exercise full features.
- CI requires setting the secret `QAI_HMAC_KEY` in Actions secrets to allow verification runs.
