@echo off

:: ============================================================
::  CONFIG - Change these to match your setup
:: ============================================================

set KITTEN_TTS_DIR=C:\games\start-package\kitten-tts
set MCP_DIR=C:\games\start-package\pet_ai_mcp

:: ============================================================
::  Do not edit below this line
:: ============================================================

set LOG=%~dp0prepare_log.txt
echo [LOG START] %date% %time% > %LOG%
echo KITTEN_TTS_DIR=%KITTEN_TTS_DIR% >> %LOG%
echo MCP_DIR=%MCP_DIR% >> %LOG%

echo.
echo  [1/3] Starting 9router...
echo [1/3] Starting 9router >> %LOG%
start "9router" cmd /k "9router"
echo [1/3] Done >> %LOG%

echo  [2/3] Starting Docker + kitten-tts...
echo [2/3] Writing PS1 script >> %LOG%
set PS_SCRIPT=%TEMP%\kitten_prepare.ps1
echo PS_SCRIPT=%PS_SCRIPT% >> %LOG%
echo Write-Host "Starting Docker Desktop..." -ForegroundColor Cyan > "%PS_SCRIPT%"
echo Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" >> "%PS_SCRIPT%"
echo Write-Host "Waiting for Docker engine..." -ForegroundColor Yellow >> "%PS_SCRIPT%"
echo $timeout = 120 >> "%PS_SCRIPT%"
echo $elapsed = 0 >> "%PS_SCRIPT%"
echo do { >> "%PS_SCRIPT%"
echo     Start-Sleep -Seconds 3 >> "%PS_SCRIPT%"
echo     $elapsed += 3 >> "%PS_SCRIPT%"
echo     $dockerOut = docker info 2^>^&1 >> "%PS_SCRIPT%"
echo     $ready = ($LASTEXITCODE -eq 0) >> "%PS_SCRIPT%"
echo     Write-Host "  ...$($elapsed)s elapsed" -ForegroundColor DarkGray >> "%PS_SCRIPT%"
echo } while (-not $ready -and $elapsed -lt $timeout) >> "%PS_SCRIPT%"
echo if (-not $ready) { >> "%PS_SCRIPT%"
echo     Write-Host "Timed out!" -ForegroundColor Red >> "%PS_SCRIPT%"
echo } else { >> "%PS_SCRIPT%"
echo     Write-Host "Docker ready! Starting kitten-tts..." -ForegroundColor Green >> "%PS_SCRIPT%"
echo     Set-Location $env:KITTEN_TTS_DIR >> "%PS_SCRIPT%"
echo     docker compose up -d --build >> "%PS_SCRIPT%"
echo } >> "%PS_SCRIPT%"
echo [2/3] PS1 complete >> %LOG%
start "docker-up" powershell -NoExit -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
echo [2/3] PowerShell started >> %LOG%

echo  [3/3] Starting Pet AI MCP server...
echo [3/3] Starting MCP >> %LOG%

set PYTHON_EXE=
where python >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%i in ('where python') do (
        if not defined PYTHON_EXE set PYTHON_EXE=%%i
    )
)

if not defined PYTHON_EXE (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
    ) do (
        if not defined PYTHON_EXE (
            if exist %%P set PYTHON_EXE=%%~P
        )
    )
)

if not defined PYTHON_EXE (
    echo [3/3] ERROR: Python not found >> %LOG%
    echo.
    echo  [ERROR] Python not found!
    pause
    goto :eof
)

echo [3/3] Installing mcp library if needed >> %LOG%
"%PYTHON_EXE%" -m pip install --quiet mcp
echo [3/3] pip done >> %LOG%

:: Save the detected Python path to a file so Airi setup can read it
echo %PYTHON_EXE%> %~dp0python_path.txt
echo [3/3] Python path saved to python_path.txt >> %LOG%

echo [3/3] Launching MCP >> %LOG%
start "pet-ai-mcp" cmd /k ""%PYTHON_EXE%" "%MCP_DIR%\server.py""
echo [3/3] MCP launched >> %LOG%

:: Write airi_mcp_config.json next to this bat file
echo [4/4] Writing airi_mcp_config.json... >> %LOG%
set JSON_OUT=%~dp0airi_mcp_config.json
powershell -ExecutionPolicy Bypass -Command "$py = '%PYTHON_EXE%'; $srv = '%MCP_DIR%\server.py'; @{ mcpServers = @{ 'pet-ai' = @{ command = $py; args = @($srv) } } } | ConvertTo-Json -Depth 5 | Set-Content -Path '%JSON_OUT%' -Encoding UTF8"
echo [4/4] airi_mcp_config.json written >> %LOG%

echo [LOG END] %date% %time% >> %LOG%
echo.
echo  All services started!
echo.
echo  airi_mcp_config.json has been created next to this file.
echo  Open it, copy the contents, and paste into Airi MCP settings.
echo.
