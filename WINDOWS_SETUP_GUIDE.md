# ================================================================
# QAI TRADER - GUÍA DE INSTALACIÓN EN WINDOWS
# ================================================================
# Configuración completa para ejecutar TODO en un solo PC Windows
# Bridge + MT5 + Generador de señales en localhost
# ================================================================

## 📋 PRERREQUISITOS

### 1. Software Necesario
- **Windows 10/11** (64-bit)
- **Python 3.11+** - [Descargar](https://www.python.org/downloads/)
  - ⚠️ Durante instalación: Marcar "Add Python to PATH"
- **Git** - [Descargar](https://git-scm.com/download/win)
- **MetaTrader 5** - [Descargar](https://www.metatrader5.com/en/download)
- **Visual Studio Code** (recomendado) - [Descargar](https://code.visualstudio.com/)

### 2. Cuenta MT5 Demo
- Abre MetaTrader 5
- File → Open Account → Demo Account
- Elige broker (ej: MetaQuotes-Demo)
- Guarda credenciales

---

## 🚀 INSTALACIÓN PASO A PASO

### PASO 1: Clonar Repositorio (5 min)

```powershell
# Abrir PowerShell (Win + X → Windows PowerShell)
cd C:\Users\TU_USUARIO\Desktop

# Clonar proyecto
git clone https://github.com/codexia87-glitch/qai-trader.git
cd qai-trader

# Verificar que estás en la carpeta correcta
ls  # Debes ver: src/, scripts/, mt5/, etc.
```

---

### PASO 2: Configurar Python (10 min)

```powershell
# Verificar versión de Python
python --version
# Debe mostrar: Python 3.11.x o superior

# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# Si aparece error de "execution policy":
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Volver a activar
.\.venv\Scripts\Activate.ps1

# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias del proyecto
pip install -r requirements.txt

# Verificar instalación
pip list | Select-String "fastapi|uvicorn"
# Debe mostrar: fastapi 0.104.x, uvicorn 0.24.x
```

---

### PASO 3: Configurar Bridge Server (3 min)

```powershell
# Crear directorios necesarios
New-Item -ItemType Directory -Path "logs" -Force
New-Item -ItemType Directory -Path "example_signals" -Force
New-Item -ItemType Directory -Path "example_signals\archived" -Force

# Copiar plantilla de configuración
Copy-Item ".env.example" -Destination ".env"

# Las credenciales ya están en los scripts, pero puedes editarlas en .env
notepad .env
```

**Contenido de `.env`:**
```env
QAI_TOKEN=w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo
QAI_HMAC_SECRET=D2urWwuvEeShrcK5T1EUSu_H6eSHotC16Vq9FdCz3BaOAYeQ_SuAq1gGV7xYCZYKl-Ld1YVdShATwBjZk2BiQg
SIGNAL_QUEUE_DIR=example_signals
```

---

### PASO 4: Probar Bridge Server (5 min)

#### Terminal 1: Iniciar Bridge
```powershell
# Asegúrate de estar en la carpeta qai-trader con .venv activo
.\scripts\start_bridge_server.ps1
```

**Debes ver:**
```
================================
QAI Bridge Server - Windows
Mode: LOCALHOST (127.0.0.1)
================================
✓ QAI_TOKEN configurado
✓ Python encontrado: Python 3.11.x
...
INFO:     Uvicorn running on http://127.0.0.1:8443
```

#### Terminal 2: Probar Conexión
```powershell
# Abrir NUEVA ventana PowerShell
cd C:\Users\TU_USUARIO\Desktop\qai-trader
.\.venv\Scripts\Activate.ps1

# Ejecutar tests
.\scripts\test_bridge_local.ps1
```

**Debes ver:**
```
[1] Verificando puerto 8443...
    ✓ Puerto 8443 está ESCUCHANDO
[2] Health check (público)...
    ✓ Status: 200 OK
[3] GET /next CON token...
    ✓ Status: 200 OK
    → Cola vacía (normal)
...
✓ TODAS LAS PRUEBAS EXITOSAS
```

---

### PASO 5: Instalar EA en MT5 (10 min)

#### 5.1 Copiar archivo EA
```powershell
# Localizar carpeta de datos de MT5
# Método 1: Desde MT5
# File → Open Data Folder → MQL5 → Experts

# Método 2: Ruta común
# C:\Users\TU_USUARIO\AppData\Roaming\MetaQuotes\Terminal\XXXXXX\MQL5\Experts

# Copiar EA (ajusta la ruta según tu instalación)
$mt5DataFolder = "C:\Users\TU_USUARIO\AppData\Roaming\MetaQuotes\Terminal\XXXXXX"
Copy-Item "mt5\QAI_Bridge_Client_Local.mq5" -Destination "$mt5DataFolder\MQL5\Experts\"
```

#### 5.2 Compilar EA
1. Abre **MetaEditor** (F4 en MT5 o desde Tools → MetaQuotes Language Editor)
2. File → Open → Navega a `Experts\QAI_Bridge_Client_Local.mq5`
3. Presiona **F7** (Compile)
4. Verifica: "0 error(s), 0 warning(s)"
5. Se genera `QAI_Bridge_Client_Local.ex5`

#### 5.3 Configurar Whitelist de URLs
1. En MT5: Tools → Options → Expert Advisors
2. Marca: ☑ "Allow WebRequest for listed URL"
3. Agrega: `http://127.0.0.1:8443`
4. Click OK

#### 5.4 Activar EA
1. Navigator (Ctrl+N) → Expert Advisors
2. Arrastra `QAI_Bridge_Client_Local` a un gráfico (ej: EURUSD M5)
3. En la ventana de inputs:
   - BridgeHost: `127.0.0.1` (ya configurado)
   - QAI_Token: (ya configurado)
   - AllowedSymbols: `EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,XAUUSD`
4. Marca: ☑ "Allow Algo Trading" (botón en toolbar)
5. Click OK

**En la pestaña "Experts" debes ver:**
```
[QAI-Local] ================================
[QAI-Local] QAI Bridge Client - LOCALHOST MODE
[QAI-Local] ================================
[QAI-Local] Bridge URL: http://127.0.0.1:8443
[QAI-Local] ✓ Successfully connected to bridge server
[QAI-Local] ✓ Localhost mode active (low latency)
```

---

### PASO 6: Prueba End-to-End (5 min)

#### 6.1 Generar Señal de Prueba
```powershell
# Terminal 2 (con bridge corriendo en Terminal 1)
cd C:\Users\TU_USUARIO\Desktop\qai-trader
.\.venv\Scripts\Activate.ps1

# Generar señal EURUSD BUY
python scripts\emit_example_signal.py --symbol EURUSD --side BUY --volume 0.01 --sl 40 --tp 80
```

**Debes ver:**
```
Signal written to: example_signals\EURUSD_BUY_20251107T120000Z.sig.json
```

#### 6.2 Verificar Ejecución en MT5

**En MT5 (pestaña "Experts"):**
```
[QAI-Local] ✓ Signal received from localhost
[QAI-Local] Executing: BUY 0.01 EURUSD
[QAI-Local] ✓ Order executed successfully!
[QAI-Local]   Ticket: 123456789
[QAI-Local]   Price: 1.08345
[QAI-Local]   Volume: 0.01
[QAI-Local] ✓ Feedback sent to localhost
```

**En Terminal 1 (bridge logs):**
```
INFO:     127.0.0.1:xxxxx - "GET /next HTTP/1.1" 200 OK
INFO:     Processed signal: EURUSD_BUY_20251107T120000Z.sig.json -> archived
INFO:     127.0.0.1:xxxxx - "POST /feedback HTTP/1.1" 200 OK
INFO:     Feedback received: {"signal_id":"...", "status":"executed", ...}
```

**En MT5 (pestaña "Trade"):**
- Nueva posición abierta: EURUSD BUY 0.01 lots

---

## ✅ VERIFICACIÓN FINAL

### Checklist de Funcionamiento
- [ ] Bridge server corre sin errores en `127.0.0.1:8443`
- [ ] `test_bridge_local.ps1` pasa todas las pruebas
- [ ] EA se conecta exitosamente (mensaje verde en Experts)
- [ ] Señal manual ejecuta orden en MT5
- [ ] Feedback llega al bridge (log en terminal)
- [ ] Archivo `.sig.json` se mueve a `archived/`

---

## 🔧 TROUBLESHOOTING

### Problema: "Python no encontrado"
```powershell
# Verificar instalación
python --version

# Si no funciona, reinstala Python desde https://www.python.org/downloads/
# Asegúrate de marcar "Add Python to PATH"
```

### Problema: "Puerto 8443 en uso"
```powershell
# Encontrar proceso usando el puerto
Get-NetTCPConnection -LocalPort 8443 | Select-Object OwningProcess

# Matar proceso
Stop-Process -Id XXXX -Force

# Reiniciar bridge
.\scripts\start_bridge_server.ps1
```

### Problema: "EA no se conecta"
1. Verifica que bridge esté corriendo: `Test-NetConnection -ComputerName 127.0.0.1 -Port 8443`
2. Verifica whitelist en MT5: Tools → Options → Expert Advisors
3. Verifica token en EA inputs (debe coincidir con QAI_TOKEN)
4. Revisa logs en pestaña "Experts" de MT5

### Problema: "WebRequest error 4060"
- URL no está en whitelist de MT5
- Solución: Tools → Options → Expert Advisors → Agregar `http://127.0.0.1:8443`

### Problema: "Symbol not allowed"
- El símbolo no está en `AllowedSymbols` del EA
- Solución: Edita input `AllowedSymbols` para incluir el par deseado

---

## 🚀 USO DIARIO

### Arrancar el Sistema
```powershell
# 1. Abrir PowerShell
cd C:\Users\TU_USUARIO\Desktop\qai-trader
.\.venv\Scripts\Activate.ps1

# 2. Iniciar bridge
.\scripts\start_bridge_server.ps1

# 3. Abrir MT5 y activar EA en gráfico
```

### Generar Señales Manualmente
```powershell
# Otra ventana PowerShell
cd C:\Users\TU_USUARIO\Desktop\qai-trader
.\.venv\Scripts\Activate.ps1

# Señal custom
python scripts\emit_example_signal.py --symbol GBPUSD --side SELL --volume 0.02
```

### Detener el Sistema
```powershell
# 1. Ctrl+C en terminal del bridge
# 2. Cerrar MT5 o desactivar EA
```

---

## 📊 PRÓXIMOS PASOS

Una vez verificado el funcionamiento:

### 1. Implementar Generación Automática (Sprint 1)
- Crear `src\strategies\technical_layer.py` (EMA/RSI)
- Crear `scripts\dual_tick.py` (genera señales cada 60s)
- Crear daemon `bin\qai_tickd.ps1`

### 2. Persistencia de Feedback (Sprint 2)
- Implementar `data\trade_feedback.jsonl`
- Crear `scripts\qai_kpi.py` para métricas

### 3. Pruebas en Demo Account
- Mínimo 2 semanas de trading simulado
- Validar win rate y drawdown
- Ajustar parámetros de estrategia

---

## 📝 NOTAS IMPORTANTES

### ⚠️ SEGURIDAD
- **NUNCA** ejecutes en cuenta real sin testing exhaustivo
- Mantén credenciales en `.env` (no commitear a Git)
- Usa siempre cuenta DEMO primero

### 💾 BACKUP
```powershell
# Backup periódico
git add .
git commit -m "Checkpoint: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push origin main
```

### 📈 MONITOREO
- Revisa logs del bridge regularmente
- Monitorea equity curve en MT5
- Verifica que `archived/` crece (señales procesadas)

---

## 🆘 SOPORTE

### Recursos
- **Documentación:** `AUDIT_REPORT_2025-11-06.md`
- **Setup Original:** `BRIDGE_SETUP_GUIDE.md`
- **Success Log:** `IMPLEMENTATION_SUCCESS.md`

### Logs Útiles
- Bridge: `logs/` (cuando implementes logs rotativos)
- MT5 Experts: Tools → Options → Expert Advisors → Journal
- Señales archivadas: `example_signals\archived\`

---

**¡SISTEMA LISTO PARA USAR!** 🎉

El bridge local está optimizado para máximo rendimiento (~1ms latency).
Siguiente paso: Implementar estrategias automáticas (ver AUDIT_REPORT).
