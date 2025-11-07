# ================================================================
# QAI Setup Checker - Verificación de Prerrequisitos
# ================================================================
# Este script verifica que tu sistema Windows está listo
# para ejecutar qai-trader
#
# Uso: .\scripts\check_windows_setup.ps1
# ================================================================

Write-Host "================================" -ForegroundColor Cyan
Write-Host "QAI TRADER - Setup Checker" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

$allGood = $true

# Check 1: Python
Write-Host "[1] Verificando Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Python instalado: $pythonVersion" -ForegroundColor Green
        
        # Check version >= 3.11
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
                Write-Host "    ⚠ Python 3.11+ requerido (tienes $major.$minor)" -ForegroundColor Yellow
                Write-Host "      Descarga: https://www.python.org/downloads/" -ForegroundColor Gray
                $allGood = $false
            }
        }
    }
} catch {
    Write-Host "    ✗ Python NO instalado" -ForegroundColor Red
    Write-Host "      Descarga: https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host "      IMPORTANTE: Marca 'Add Python to PATH' durante instalación" -ForegroundColor Yellow
    $allGood = $false
}

# Check 2: Git
Write-Host "`n[2] Verificando Git..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ Git instalado: $gitVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "    ✗ Git NO instalado" -ForegroundColor Red
    Write-Host "      Descarga: https://git-scm.com/download/win" -ForegroundColor Gray
    $allGood = $false
}

# Check 3: Pip
Write-Host "`n[3] Verificando pip..." -ForegroundColor Yellow
try {
    $pipVersion = python -m pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ pip instalado: $pipVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "    ✗ pip NO encontrado" -ForegroundColor Red
    Write-Host "      Solución: python -m ensurepip --upgrade" -ForegroundColor Gray
    $allGood = $false
}

# Check 4: Virtual Environment capability
Write-Host "`n[4] Verificando venv..." -ForegroundColor Yellow
try {
    $venvCheck = python -m venv --help 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ venv disponible" -ForegroundColor Green
    }
} catch {
    Write-Host "    ✗ venv NO disponible" -ForegroundColor Red
    $allGood = $false
}

# Check 5: PowerShell version
Write-Host "`n[5] Verificando PowerShell..." -ForegroundColor Yellow
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -ge 5) {
    Write-Host "    ✓ PowerShell $($psVersion.Major).$($psVersion.Minor)" -ForegroundColor Green
} else {
    Write-Host "    ⚠ PowerShell antiguo (v$($psVersion.Major))" -ForegroundColor Yellow
    Write-Host "      Recomendado: PowerShell 5.1+" -ForegroundColor Gray
}

# Check 6: Execution Policy
Write-Host "`n[6] Verificando Execution Policy..." -ForegroundColor Yellow
$policy = Get-ExecutionPolicy -Scope CurrentUser
if ($policy -eq "Restricted") {
    Write-Host "    ⚠ Execution Policy: Restricted" -ForegroundColor Yellow
    Write-Host "      Solución: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Gray
} else {
    Write-Host "    ✓ Execution Policy: $policy" -ForegroundColor Green
}

# Check 7: Internet Connection
Write-Host "`n[7] Verificando conexión a Internet..." -ForegroundColor Yellow
try {
    $testConnection = Test-NetConnection -ComputerName google.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($testConnection) {
        Write-Host "    ✓ Conexión a Internet OK" -ForegroundColor Green
    } else {
        Write-Host "    ⚠ Sin conexión a Internet" -ForegroundColor Yellow
        Write-Host "      Necesario para: pip install, git clone" -ForegroundColor Gray
    }
} catch {
    Write-Host "    ⚠ No se pudo verificar conexión" -ForegroundColor Yellow
}

# Check 8: Port 8443 availability
Write-Host "`n[8] Verificando puerto 8443..." -ForegroundColor Yellow
$portInUse = Get-NetTCPConnection -LocalPort 8443 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "    ⚠ Puerto 8443 está en uso" -ForegroundColor Yellow
    Write-Host "      Proceso: $($portInUse.OwningProcess)" -ForegroundColor Gray
    Write-Host "      Solución: Stop-Process -Id $($portInUse.OwningProcess) -Force" -ForegroundColor Gray
} else {
    Write-Host "    ✓ Puerto 8443 disponible" -ForegroundColor Green
}

# Check 9: Project Structure
Write-Host "`n[9] Verificando estructura del proyecto..." -ForegroundColor Yellow
$requiredPaths = @(
    "core\bridge_server.py",
    "scripts\emit_example_signal.py",
    "scripts\start_bridge_server.ps1",
    "mt5\QAI_Bridge_Client_Local.mq5",
    "requirements.txt"
)

$structureOK = $true
foreach ($path in $requiredPaths) {
    if (Test-Path $path) {
        Write-Host "    ✓ $path" -ForegroundColor Green
    } else {
        Write-Host "    ✗ $path NO encontrado" -ForegroundColor Red
        $structureOK = $false
    }
}

if (-not $structureOK) {
    Write-Host "`n    ⚠ Estructura incompleta" -ForegroundColor Yellow
    Write-Host "      ¿Estás en la carpeta raíz de qai-trader?" -ForegroundColor Gray
    $allGood = $false
}

# Check 10: MetaTrader 5 (optional)
Write-Host "`n[10] Verificando MetaTrader 5..." -ForegroundColor Yellow
$mt5Paths = @(
    "C:\Program Files\MetaTrader 5",
    "C:\Program Files (x86)\MetaTrader 5",
    "$env:APPDATA\MetaQuotes\Terminal"
)

$mt5Found = $false
foreach ($path in $mt5Paths) {
    if (Test-Path $path) {
        Write-Host "    ✓ MT5 encontrado: $path" -ForegroundColor Green
        $mt5Found = $true
        break
    }
}

if (-not $mt5Found) {
    Write-Host "    ⚠ MT5 NO encontrado" -ForegroundColor Yellow
    Write-Host "      Descarga: https://www.metatracker5.com/en/download" -ForegroundColor Gray
    Write-Host "      (No crítico para testing del bridge)" -ForegroundColor Gray
}

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "✓ SISTEMA LISTO PARA INSTALACIÓN" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "`nPróximos pasos:" -ForegroundColor Yellow
    Write-Host "  1. Si no tienes el repo: git clone https://github.com/codexia87-glitch/qai-trader.git" -ForegroundColor Gray
    Write-Host "  2. cd qai-trader" -ForegroundColor Gray
    Write-Host "  3. python -m venv .venv" -ForegroundColor Gray
    Write-Host "  4. .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "  5. pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "  6. .\scripts\start_bridge_server.ps1" -ForegroundColor Gray
} else {
    Write-Host "⚠ ACCIÓN REQUERIDA" -ForegroundColor Yellow
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "`nInstala el software faltante marcado con ✗" -ForegroundColor Yellow
    Write-Host "Luego vuelve a ejecutar este script para verificar." -ForegroundColor Gray
}

Write-Host ""
