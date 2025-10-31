# CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Advanced multi-session 3D visualization module exporting HTML/JSON/PNG dashboards with signed audit hooks (`src/qai/visualizer_advanced.py`).
- Evaluation pipeline and experiment engine integration for interactive visual comparisons during adaptive optimization runs.

## [v0.2.0] - 2025-10-31
### Added
- Backtest JSON datastore for session artifacts and metadata (`src/qai/datastore.py`).
- Strategy toolkit expansion with `ThresholdCrossStrategy` and `PredictorThresholdStrategy`.
- `ModelPredictor` integration with NumPy fallback and audit hooks for predictions (`src/qai/model_predictor.py`).
- Multi-session simulator orchestrating runs with structured logging and summaries (`src/qai/simulator.py`).
- Post-backtest HMAC validation helpers and dedicated tests (`src/qai/hmac_utils.py`, `tests/test_hmac_utils.py`).
- Extended unit coverage for datastore, predictor, and simulator workflows.

### Changed
- `Backtester` now persists run summaries, calculates advanced metrics (drawdown, Sharpe, avg PnL), and links datastore paths in audit entries.
- Predictor-driven strategies sign prediction events and reuse shared HMAC utilities.
- Documentation refreshed with v0.2.0 roadmap and security notes.

### Security
- Enforced HMAC signing across predictor, backtester, and simulator outputs with verification after multi-session runs.

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
