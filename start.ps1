# DataChart One-Click Start Script
param(
    [switch]$NoBrowser
)

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DataChart - Financial Visualization" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Kill existing process on port 3000
$p = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue).OwningProcess
if ($p) {
    Write-Host "[*] Port 3000 occupied (PID: $p), releasing..." -ForegroundColor Gray
    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Start backend
Write-Host "[1/2] Starting backend (Express)..." -ForegroundColor Green
$serverProcess = Start-Process -FilePath "node" -ArgumentList "index.js" `
    -WorkingDirectory "$rootDir\server" `
    -WindowStyle Minimized `
    -PassThru
Write-Host "     Waiting for backend..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Start frontend via cmd to ensure npx is found
Write-Host "[2/2] Starting frontend (Vite)..." -ForegroundColor Green
$clientProcess = Start-Process -FilePath "cmd" `
    -ArgumentList "/c `"cd /d $rootDir\client && npx vite --host`"" `
    -WindowStyle Minimized `
    -PassThru
Write-Host "     Waiting for frontend..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Open browser
if (-not $NoBrowser) {
    Write-Host "[*] Opening browser..." -ForegroundColor Gray
    Start-Process "http://localhost:5173"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Startup complete!" -ForegroundColor Green
Write-Host "  Dashboard : http://localhost:5173" -ForegroundColor White
Write-Host "  Admin Login: http://localhost:5173/login" -ForegroundColor White
Write-Host "  Account   : admin / admin123" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend PID: $($serverProcess.Id) | Frontend PID: $($clientProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to stop all services..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
Write-Host "`n[*] Stopping services..." -ForegroundColor Gray
if (-not $serverProcess.HasExited) { Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue }
if (-not $clientProcess.HasExited) { Stop-Process -Id $clientProcess.Id -Force -ErrorAction SilentlyContinue }
Write-Host "    Services stopped. Bye!" -ForegroundColor Green
