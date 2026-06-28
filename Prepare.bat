@echo off

:: ============================================================
::  CONFIG — Change these paths to match your setup
:: ============================================================

set KITTEN_TTS_DIR=your_kitten_tts_dir
set MCP_SERVER_SCRIPT=your_pet_ai_mcp_dir

:: ============================================================
::  Do not edit below this line
:: ============================================================

echo.
echo  [1/3] Starting 9router...
start "9router" cmd /k "9router"

echo  [2/3] Starting Docker + kitten-tts...
set PS_SCRIPT=%TEMP%\kitten_prepare.ps1
(
echo Write-Host 'Starting Docker Desktop...' -ForegroundColor Cyan
echo Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
echo Write-Host 'Waiting for Docker engine to be ready...' -ForegroundColor Yellow
echo $timeout = 120; $elapsed = 0
echo do {
echo     Start-Sleep -Seconds 3; $elapsed += 3
echo     $ready = docker info 2^>$null; $ready = $?
echo     Write-Host "  ...${elapsed}s elapsed" -ForegroundColor DarkGray
echo } while (-not $ready -and $elapsed -lt $timeout^)
echo if ($elapsed -ge $timeout^) { Write-Host 'Timed out waiting for Docker!' -ForegroundColor Red }
echo else {
echo     Write-Host 'Docker is ready! Starting kitten-tts...' -ForegroundColor Green
echo     Set-Location '%KITTEN_TTS_DIR%'
echo     docker compose up -d --build
echo }
) > "%PS_SCRIPT%"

start "docker-up" powershell -NoExit -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

echo  [3/3] Starting Pet AI MCP server...
start "pet-ai-mcp" cmd /k "python "%MCP_SERVER_SCRIPT%""

echo.
echo  All services started! Keep this window open or close it safely.
echo  (The MCP server and 9router run in their own windows)
echo.
