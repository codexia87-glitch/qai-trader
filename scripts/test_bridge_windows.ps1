# Test Bridge from Windows (PowerShell)
# Save as: test_bridge.ps1
# Usage: .\test_bridge.ps1

param(
    [string]$HostMac = "192.168.0.100",
    [int]$Port = 8443,
    [string]$Token = "w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo"
)

Write-Host "================================" -ForegroundColor Green
Write-Host "QAI Bridge Test - Windows Client" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

$BaseUrl = "http://${HostMac}:${Port}"
Write-Host "Testing: $BaseUrl" -ForegroundColor Yellow
Write-Host ""

# Test 1: Health Check (no auth)
Write-Host "Test 1: Health Check (no authentication)" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/health" -Method GET -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] Health check successful" -ForegroundColor Green
        $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
    }
} catch {
    Write-Host "[ERROR] Health check failed" -ForegroundColor Red
    Write-Host $_.Exception.Message
}
Write-Host ""

# Test 2: Get Next Signal (with token)
Write-Host "Test 2: Get Next Signal (with authentication)" -ForegroundColor Yellow
try {
    $headers = @{
        "X-QAI-Token" = $Token
    }
    $response = Invoke-WebRequest -Uri "$BaseUrl/next" -Headers $headers -Method GET -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] Request successful" -ForegroundColor Green
        $json = $response.Content | ConvertFrom-Json
        
        if ($json.status -eq "empty") {
            Write-Host "Queue is empty (no signals)" -ForegroundColor Cyan
        } elseif ($json.status -eq "ok") {
            Write-Host "Signal received!" -ForegroundColor Green
            $json | ConvertTo-Json -Depth 10
        }
    }
} catch {
    Write-Host "[ERROR] Request failed" -ForegroundColor Red
    Write-Host "Status: $($_.Exception.Response.StatusCode.Value__)"
    Write-Host "Message: $($_.Exception.Message)"
}
Write-Host ""

# Test 3: Get Next Signal (without token - should fail)
Write-Host "Test 3: Get Next Signal (without token - should fail)" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/next" -Method GET -UseBasicParsing
    Write-Host "[UNEXPECTED] Request should have failed but got: $($response.StatusCode)" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    if ($statusCode -eq 401 -or $statusCode -eq 403) {
        Write-Host "[OK] Correctly rejected (HTTP $statusCode)" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Unexpected status: $statusCode" -ForegroundColor Red
    }
}
Write-Host ""

# Test 4: Network connectivity
Write-Host "Test 4: Network Connectivity" -ForegroundColor Yellow
try {
    $result = Test-NetConnection -ComputerName $HostMac -Port $Port -InformationLevel Quiet
    if ($result) {
        Write-Host "[OK] Port $Port is reachable on $HostMac" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Cannot reach $HostMac`:$Port" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Network test failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "================================" -ForegroundColor Green
Write-Host "Tests Completed" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "If all tests passed, your EA should work!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure MT5 WebRequest URL whitelist:" -ForegroundColor White
Write-Host "   Tools -> Options -> Expert Advisors" -ForegroundColor White
Write-Host "   Add: $BaseUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Copy QAI_Bridge_Client.mq5 to MT5 Experts folder" -ForegroundColor White
Write-Host "3. Compile in MetaEditor (F7)" -ForegroundColor White
Write-Host "4. Attach to chart with these inputs:" -ForegroundColor White
Write-Host "   BridgeHost: $HostMac" -ForegroundColor Cyan
Write-Host "   BridgePort: $Port" -ForegroundColor Cyan
Write-Host "   QAI_Token: $Token" -ForegroundColor Cyan
Write-Host ""
