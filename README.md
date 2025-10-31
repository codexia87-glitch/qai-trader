# QAI Audit Verification

[![QAI Audit Verification](https://github.com/codexia87-glitch/qai-trader/actions/workflows/test_audit_verification.yml/badge.svg)](https://github.com/codexia87-glitch/qai-trader/actions/workflows/test_audit_verification.yml)

Badge updated to point to: `codexia87-glitch/qai-trader`

Project: qai-trader — minimal scaffold for QUANT AI intraday trading. See `./.github/workflows/test_audit_verification.yml` for CI details.
# qai-trader

Minimal scaffold for a QUANT AI intraday trading system (Sprint 0).

This repository contains an initial project skeleton to connect Python-based quant/AI code with MT5 (MQL5) later. At this stage there is no business logic, no network calls, and no data ingestion — only a minimal package structure, configuration files, and a smoke test.

Quick start
1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:
   pip install -r requirements.txt
3. Run tests:
   pytest -q

Project layout (initial)
- src/: Python package stubs for domain areas (data, ai, quant, bridge, etc.)
- config/: YAML configuration placeholder
- tests/: smoke test that imports modules to ensure packaging is correct
- mt5/: placeholder for MQL5 Expert Advisor (EA) later

This scaffold intentionally contains no business logic. Add concrete implementations in future sprints.

## 🚀 Roadmap v0.2.0 — Predictive Backtesting Phase

- Backtesting datastore (`src/qai/datastore.py`) storing run artefacts under `var/backtests/`.
- Strategy toolkit with threshold and predictor-driven logic (`src/qai/strategies.py`).
- `ModelPredictor` integration (NumPy/PyTorch) plus audit logging for generated signals.
- Automated tests validating datastore persistence and predictor-driven simulations.
- HMAC validation helpers (`src/qai/hmac_utils.py`) verifying audit integrity after runs.
- Multi-session simulator (`src/qai/simulator.py`) generating aggregate performance summaries.

## 📦 Release v0.2.0 Highlights

- Branch `release/v0.2.0` contains the finalized predictive & backtesting stack ready for tagging.
- CHANGELOG now documents predictor, simulator and HMAC validation improvements for the 0.2.0 drop.
- Audit log entries are fully HMAC-signed across backtester, predictor and simulator workflows.
- Use `pytest tests/test_backtester.py tests/test_predictor_integration.py tests/test_backtest_simulator.py tests/test_hmac_utils.py` to validate the release locally.
- Next steps: tag `v0.2.0`, merge `release/v0.2.0` after QA, and plan the v0.2.x enhancements.

## 🔐 CI Setup — Secrets

The CI workflow `test_audit_verification.yml` verifies the integrity of the append-only `audit.log` by checking HMAC-SHA256 signatures. For the workflow to pass you must provide the secret key used to sign/verify audit entries.

How to set the secret on GitHub (web UI):

1. Go to your repository on GitHub: https://github.com/codexia87-glitch/qai-trader
2. Settings → Secrets and variables → Actions → New repository secret
3. Name: `QAI_HMAC_KEY`
4. Value: (your HMAC secret string, e.g. a long random token)
5. Save secret.

Or using GitHub CLI:

1. Install `gh` and authenticate: `gh auth login`
2. Run:

   gh secret set QAI_HMAC_KEY --body "$(openssl rand -hex 32)"

Security notes:
- Use a strong random value (example above uses `openssl rand -hex 32`).
- Store the key only in GitHub Secrets (not in the repo). The workflow reads `QAI_HMAC_KEY` from secrets at runtime.
- If you rotate the key, re-sign any existing audit entries or note the rotation in your audit trail.

Quick local test (optional):

```bash
export QAI_HMAC_KEY="your-test-key"
python3 -m pytest -q tests/test_audit_verification.py
```

After adding the secret, push your changes and the workflow will run on the next push or pull request. If the audit signatures are valid the job will exit successfully; otherwise it will fail and report which lines (if `--verbose`) are invalid.
