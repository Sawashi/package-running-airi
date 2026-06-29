@echo off
setlocal EnableExtensions

title Shutdown - Start Package

echo.
echo ========================================
echo Stopping Services
echo ========================================

:: ============================================================
:: Stop Pet AI MCP
:: ============================================================

echo.
echo [1/3] Stopping Pet AI MCP...

taskkill /FI "WINDOWTITLE eq Pet AI MCP" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq pet-ai-mcp" /F >nul 2>&1

:: ============================================================
:: Stop Pocket TTS
:: ============================================================

echo.
echo [2/3] Stopping Pocket TTS...

taskkill /FI "WINDOWTITLE eq Pocket TTS" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq pocket-tts" /F >nul 2>&1

:: Kill any Python process running Pocket TTS
for /f "skip=1 tokens=2 delims=," %%P in ('tasklist /FO CSV /NH ^| findstr /I "python.exe"') do (
    wmic process where "ProcessId=%%~P" get CommandLine 2>nul | findstr /I "pocket_tts pocket_tts_api.py" >nul
    if not errorlevel 1 (
        taskkill /PID %%~P /F >nul 2>&1
    )
)

:: Kill uvicorn if used
taskkill /IM uvicorn.exe /F >nul 2>&1

:: ============================================================
:: Stop 9router
:: ============================================================

echo.
echo [3/3] Stopping 9router...

taskkill /FI "WINDOWTITLE eq 9router" /F >nul 2>&1

echo.
echo ========================================
echo All services have been stopped.
echo ========================================
echo.

pause
exit /b 0