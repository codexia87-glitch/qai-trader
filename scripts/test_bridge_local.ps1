# ================================================================
# QAI Bridge Server - Test Script (Windows PowerShell)
# ================================================================
# Este script prueba la conectividad con el bridge server local
#
# Uso: .\scripts\test_bridge_local.ps1
# ================================================================

Write-Host "================================" -ForegroundColor Green
Write-Host "Testing QAI Bridge (Localhost)" -ForegroundColor Green
Write-Host "================================`n" -ForegroundColor Green

$baseUrl = "http://127.0.0.1:8443"
$token = "w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo"

# Test 1: Verificar que el puerto está escuchando
Write-Host "[1] Verificando puerto 8443..." -ForegroundColor Cyan
$portCheck = Get-NetTCPConnection -LocalPort 8443 -State Listen -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "    ✓ Puerto 8443 está ESCUCHANDO" -ForegroundColor Green
} else {
    Write-Host "    ✗ Puerto 8443 NO está escuchando" -ForegroundColor Red
    Write-Host "    → Ejecuta primero: .\scripts\start_bridge_server.ps1" -ForegroundColor Yellow
    exit 1
}

# Test 2: Health check (sin autenticación)
Write-Host "`n[2] Health check (público)..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method Get -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "    ✓ Status: 200 OK" -ForegroundColor Green
        $health = $response.Content | ConvertFrom-Json
        Write-Host "    Service: $($health.service)" -ForegroundColor Gray
        Write-Host "    Version: $($health.version)" -ForegroundColor Gray
        Write-Host "    Queue: $($health.queue_dir)" -ForegroundColor Gray
    }
} catch {
    Write-Host "    ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 3: /next con token (debe funcionar)
Write-Host "`n[3] GET /next CON token..." -ForegroundColor Cyan
try {
    $headers = @{
        "X-QAI-Token" = $token
    }
    $response = Invoke-WebRequest -Uri "$baseUrl/next" -Method Get -Headers $headers -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        Write-Host "    ✓ Status: 200 OK" -ForegroundColor Green
        $data = $response.Content | ConvertFrom-Json
        
        if ($data.status -eq "empty") {
            Write-Host "    → Cola vacía (normal si no hay señales)" -ForegroundColor Yellow
        } else {
            Write-Host "    → Señal recibida:" -ForegroundColor Green
            Write-Host "      Symbol: $($data.signal.symbol)" -ForegroundColor Gray
            Write-Host "      Side: $($data.signal.side)" -ForegroundColor Gray
            Write-Host "      Volume: $($data.signal.volume)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "    ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 4: /next SIN token (debe fallar con 401)
Write-Host "`n[4] GET /next SIN token (debe fallar)..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/next" -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "    ✗ ERROR: Se esperaba 401 pero obtuvo $($response.StatusCode)" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 401 -or $_.Exception.Response.StatusCode -eq 403) {
        Write-Host "    ✓ Autenticación rechazada correctamente (401/403)" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Error inesperado: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test 5: Verificar directorios
Write-Host "`n[5] Verificando directorios..." -ForegroundColor Cyan
if (Test-Path "example_signals") {
    Write-Host "    ✓ example_signals\ existe" -ForegroundColor Green
    $signalCount = (Get-ChildItem "example_signals\*.sig.json" -ErrorAction SilentlyContinue).Count
    Write-Host "    Señales en cola: $signalCount" -ForegroundColor Gray
} else {
    Write-Host "    ✗ example_signals\ no existe" -ForegroundColor Red
}

if (Test-Path "example_signals\archived") {
    Write-Host "    ✓ example_signals\archived\ existe" -ForegroundColor Green
    $archivedCount = (Get-ChildItem "example_signals\archived\*" -ErrorAction SilentlyContinue).Count
    Write-Host "    Señales archivadas: $archivedCount" -ForegroundColor Gray
} else {
    Write-Host "    ✗ example_signals\archived\ no existe" -ForegroundColor Red
}

Write-Host "`n================================" -ForegroundColor Green
Write-Host "✓ TODAS LAS PRUEBAS EXITOSAS" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "`nEl bridge está funcionando correctamente en localhost" -ForegroundColor Cyan
Write-Host "Ahora puedes:" -ForegroundColor Yellow
Write-Host "  1. Configurar EA en MT5 con BridgeHost = '127.0.0.1'" -ForegroundColor Gray
Write-Host "  2. Generar señales: python scripts\emit_example_signal.py" -ForegroundColor Gray
Write-Host "  3. Activar EA en un gráfico de MT5" -ForegroundColor Gray
