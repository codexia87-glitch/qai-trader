# ================================================================
# QAI Bridge Server - Windows PowerShell Launcher
# ================================================================
# Este script inicia el bridge server en modo LOCALHOST (127.0.0.1)
# para uso en el mismo PC donde corre MT5
#
# Uso: .\scripts\start_bridge_server.ps1
# ================================================================

Write-Host "================================" -ForegroundColor Green
Write-Host "QAI Bridge Server - Windows" -ForegroundColor Green
Write-Host "Mode: LOCALHOST (127.0.0.1)" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "core\bridge_server.py")) {
    Write-Host "ERROR: No se encuentra core\bridge_server.py" -ForegroundColor Red
    Write-Host "Ejecuta este script desde la raíz del proyecto qai-trader" -ForegroundColor Yellow
    exit 1
}

# Crear directorio de logs si no existe
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "Creado directorio logs\" -ForegroundColor Green
}

# Configurar credenciales
Write-Host "`nConfigurando credenciales..." -ForegroundColor Cyan
$env:QAI_TOKEN = "w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo"
$env:QAI_HMAC_SECRET = "D2urWwuvEeShrcK5T1EUSu_H6eSHotC16Vq9FdCz3BaOAYeQ_SuAq1gGV7xYCZYKl-Ld1YVdShATwBjZk2BiQg"
$env:SIGNAL_QUEUE_DIR = "example_signals"

Write-Host "✓ QAI_TOKEN configurado" -ForegroundColor Green
Write-Host "✓ QAI_HMAC_SECRET configurado" -ForegroundColor Green
Write-Host "✓ SIGNAL_QUEUE_DIR = example_signals" -ForegroundColor Green

# Verificar que Python está instalado
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: Python no está instalado o no está en PATH" -ForegroundColor Red
    Write-Host "Instala Python 3.11+ desde https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host "`n✓ Python encontrado: $pythonVersion" -ForegroundColor Green

# Verificar entorno virtual
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "`nWARNING: No se encuentra entorno virtual .venv" -ForegroundColor Yellow
    Write-Host "Creando entorno virtual..." -ForegroundColor Cyan
    python -m venv .venv
    Write-Host "✓ Entorno virtual creado" -ForegroundColor Green
    
    Write-Host "`nInstalando dependencias..." -ForegroundColor Cyan
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\pip.exe install -r requirements.txt
    Write-Host "✓ Dependencias instaladas" -ForegroundColor Green
}

# Activar entorno virtual
Write-Host "`nActivando entorno virtual..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Verificar puerto disponible
$port = 8443
$portInUse = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "`nWARNING: Puerto $port está en uso" -ForegroundColor Yellow
    Write-Host "Deteniendo proceso existente..." -ForegroundColor Cyan
    $processId = (Get-NetTCPConnection -LocalPort $port).OwningProcess
    Stop-Process -Id $processId -Force
    Start-Sleep -Seconds 2
    Write-Host "✓ Proceso detenido" -ForegroundColor Green
}

# Crear directorio de señales si no existe
if (-not (Test-Path "example_signals")) {
    New-Item -ItemType Directory -Path "example_signals" | Out-Null
    Write-Host "✓ Creado directorio example_signals\" -ForegroundColor Green
}

if (-not (Test-Path "example_signals\archived")) {
    New-Item -ItemType Directory -Path "example_signals\archived" | Out-Null
    Write-Host "✓ Creado directorio example_signals\archived\" -ForegroundColor Green
}

Write-Host "`n================================" -ForegroundColor Green
Write-Host "Iniciando Bridge Server..." -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "Host: 127.0.0.1 (LOCALHOST)" -ForegroundColor Cyan
Write-Host "Port: $port" -ForegroundColor Cyan
Write-Host "Queue: example_signals\" -ForegroundColor Cyan
Write-Host "`nPresiona Ctrl+C para detener" -ForegroundColor Yellow
Write-Host "================================`n" -ForegroundColor Green

# Iniciar servidor
# IMPORTANTE: Bind en 127.0.0.1 (solo localhost, no toda la red)
python -m uvicorn core.bridge_server:app --host 127.0.0.1 --port $port --log-level info
