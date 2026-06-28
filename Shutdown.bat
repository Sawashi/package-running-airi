@echo off

:: ============================================================
::  CONFIG — Must match the paths in Prepare.bat
:: ============================================================

set KITTEN_TTS_DIR=your_kitten_tts_dir

:: ============================================================
::  Do not edit below this line
:: ============================================================

echo.
echo  [1/3] Stopping Pet AI MCP server...
taskkill /FI "WINDOWTITLE eq pet-ai-mcp" /F >nul 2>&1

echo  [2/3] Bringing down kitten-tts and Docker...
set PS_SCRIPT=%TEMP%\kitten_shutdown.ps1
(
echo Set-Location '%KITTEN_TTS_DIR%'
echo Write-Host 'Bringing down kitten-tts...' -ForegroundColor Cyan
echo docker compose down
echo Write-Host 'Shutting down Docker Desktop...' -ForegroundColor Yellow
echo Stop-Process -Name 'Docker Desktop' -Force -ErrorAction SilentlyContinue
echo Write-Host 'Done.' -ForegroundColor Green
) > "%PS_SCRIPT%"

start "docker-down" powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

:: Give docker compose down a moment to kick off
timeout /t 2 /nobreak >nul

echo  [3/3] Stopping 9router...
taskkill /FI "WINDOWTITLE eq 9router" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq docker-up" /F >nul 2>&1

:: Wait for docker-down to finish before exiting
:wait_loop
tasklist /FI "WINDOWTITLE eq docker-down" 2>nul | find "powershell.exe" >nul
if %errorlevel%==0 (
    timeout /t 2 /nobreak >nul
    goto wait_loop
)

echo.
echo  All services stopped!
echo.
