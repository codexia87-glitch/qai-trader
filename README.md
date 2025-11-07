# QAI Audit Verification

[![QAI Audit Verification](https://github.com/codexia87-glitch/qai-trader/actions/workflows/test_audit_verification.yml/badge.svg)](https://github.com/codexia87-glitch/qai-trader/actions/workflows/test_audit_verification.yml)

Badge updated to point to: `codexia87-glitch/qai-trader`

Project: qai-trader — minimal scaffold for QUANT AI intraday trading. See `./.github/workflows/test_audit_verification.yml` for CI details.
# qai-trader

Quantum AI Trading System with FastAPI Bridge for MetaTrader 5 integration.

## 🚀 Quick Start (Windows - All-in-One Setup)

**NEW: Complete Windows installation guide available!**

### Prerequisites
- Windows 10/11 (64-bit)
- Python 3.11+
- MetaTrader 5
- Git

### Installation (30 minutes)
```powershell
# 1. Clone repository
git clone https://github.com/codexia87-glitch/qai-trader.git
cd qai-trader

# 2. Check prerequisites
.\scripts\check_windows_setup.ps1

# 3. Setup Python environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Start bridge server (localhost mode)
.\scripts\start_bridge_server.ps1

# 5. Test connection
.\scripts\test_bridge_local.ps1
```

**📖 Full Windows Guide:** See [`WINDOWS_SETUP_GUIDE.md`](./WINDOWS_SETUP_GUIDE.md) for step-by-step instructions including MT5 EA installation.

**📋 System Audit:** See [`AUDIT_REPORT_2025-11-06.md`](./AUDIT_REPORT_2025-11-06.md) for complete roadmap and implementation status.

---

## 📂 Project Structure
- `src/`: Python packages (strategies, bridge, quant modules)
- `core/`: FastAPI bridge server
- `scripts/`: Utilities (signal generation, testing, startup)
- `mt5/`: MetaTrader 5 Expert Advisors (MQL5)
- `config/`: YAML configuration
- `tests/`: Unit and integration tests

---

## 🌐 Bridge Architecture

**Localhost Mode (Recommended for Windows):**
```
Windows PC:
├── Python Bridge (127.0.0.1:8443)
├── MT5 Client EA
└── Signal Generator
    → All on same machine (~1ms latency)
```

**LAN Mode (Mac/Windows Split):**
```
Mac:
├── Python Bridge (192.168.0.100:8443)
└── Signal Generator

Windows:
└── MT5 Client EA
    → Connects via LAN (~10-50ms latency)
```

---

## 🧪 Testing

### Local Testing
```powershell
# Generate test signal
python scripts\emit_example_signal.py --symbol EURUSD --side BUY

# Check bridge health
curl http://127.0.0.1:8443/health

# Run unit tests
pytest -q
```

---

## 🎯 Current Status (v0.7.0 in progress)

**✅ Completed:**
- FastAPI bridge server with authentication (Token + HMAC)
- MT5 Expert Advisor with localhost optimization
- Signal queue system with archiving
- Feedback loop (EA → Bridge)
- Windows PowerShell scripts

**⏳ In Progress:**
- Automated strategy generation (EMA/RSI)
- Trade feedback persistence
- KPI metrics and monitoring

**📊 Progress:** 42% complete (26/61 roadmap items)

See [`AUDIT_REPORT_2025-11-06.md`](./AUDIT_REPORT_2025-11-06.md) for detailed breakdown.

---

## ✨ Advanced Visualization (v0.6.0 in progress)

- `AdvancedMultiSessionVisualizer` (`src/qai/visualizer_advanced.py`) renders multi-session dashboards with interactive 3D equity surfaces, JSON summaries, and PNG snapshots.
- The evaluation pipeline and experiment engine accept the advanced visualizer for side-by-side comparisons with signed audit events (`qai.visualizer3d/*`).
- Generated dashboards export HTML/JSON/PNG assets suitable for release auditing and artifact sharing.

## 🔗 Integración con CI/CD externo

- `CIIntegrationManager` (`src/qai/integrations_ci.py`) detecta entornos GitHub Actions, GitLab o Jenkins para activar validaciones automáticas.
- Los pipelines pueden exportar y recuperar artefactos (CSV/Parquet/S3) reutilizando `IntegrationsManager`, con auditoría firmada (`qai.ci/*`).
- `DeployValidator` y `EvaluationPipeline` pueden registrar hooks de validación y finalización tras pruebas o despliegues canary.

## 🛡️ Validación distribuida y redundancia

- `DistributedValidator` y `RedundancyChecker` (`src/qai/distributed_validator.py`) permiten ejecutar verificaciones concurrentes en múltiples nodos con comparaciones de hashes.
- Se registran eventos firmados (`qai.distributed/*`) para cada nodo y para el resumen consolidado, asegurando integridad criptográfica.
- `DeployValidator` y `EvaluationPipeline` pueden acoplar el validador distribuido para reforzar controles post-deploy y post-simulación.

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
