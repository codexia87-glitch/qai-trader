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
