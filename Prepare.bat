@echo off
setlocal EnableExtensions

title Prepare - Start Package

:: ============================================================
:: Paths
:: ============================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "POCKET_TTS_DIR=%ROOT%\pocket-tts"
set "MCP_DIR=%ROOT%\pet_ai_mcp"

set "FFMPEG_DIR=%ROOT%\ffmpeg\bin"

if exist "%FFMPEG_DIR%\ffmpeg.exe" (
    set "PATH=%FFMPEG_DIR%;%PATH%"
)

set "LOG=%ROOT%\prepare_log.txt"
set "PYTHON_FILE=%ROOT%\python_path.txt"
set "JSON_OUT=%ROOT%\airi_mcp_config.json"

echo [LOG START] %date% %time% > "%LOG%"
echo ROOT=%ROOT%>>"%LOG%"
echo POCKET_TTS_DIR=%POCKET_TTS_DIR%>>"%LOG%"
echo MCP_DIR=%MCP_DIR%>>"%LOG%"

:: ============================================================
:: Detect Python
:: ============================================================

echo.
echo [PRE] Detecting Python...
echo [PRE] Detecting Python>>"%LOG%"

set "PYTHON_EXE="

:: Common install locations
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
        if exist %%~P (
            set "PYTHON_EXE=%%~P"
        )
    )
)

:: Python Launcher
if not defined PYTHON_EXE (
    where py >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
        )
    )
)

:: PATH
if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%i in ('where python') do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
        )
    )
)

:: ============================================================
:: Install Python automatically if missing
:: ============================================================

if not defined PYTHON_EXE (

    echo.
    echo [INFO] Python not found.
    echo [INFO] Downloading Python installer...

    powershell -NoProfile -ExecutionPolicy Bypass ^
        "Invoke-WebRequest https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe -OutFile python-installer.exe"

    if not exist python-installer.exe (
        echo.
        echo [ERROR] Failed to download Python.
        pause
        exit /b 1
    )

    echo.
    echo Installing Python...

    start /wait "" python-installer.exe ^
        /quiet ^
        InstallAllUsers=0 ^
        PrependPath=1 ^
        Include_test=0

    del python-installer.exe

    timeout /t 5 >nul

    for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    ) do (
        if not defined PYTHON_EXE (
            if exist %%~P (
                set "PYTHON_EXE=%%~P"
            )
        )
    )

    if not defined PYTHON_EXE (
        where python >nul 2>&1
        if not errorlevel 1 (
            for /f "delims=" %%i in ('where python') do (
                if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
            )
        )
    )
)

if not defined PYTHON_EXE (
    echo.
    echo [ERROR] Python installation failed.
    pause
    exit /b 1
)

echo %PYTHON_EXE%>"%PYTHON_FILE%"

echo [OK] Python: %PYTHON_EXE%
echo [OK] Python: %PYTHON_EXE%>>"%LOG%"

:: ============================================================
:: Start 9router
:: ============================================================

echo.
echo [1/3] Starting 9router...
echo [1/3] Starting 9router>>"%LOG%"

start "9router" cmd /k "9router"

:: ============================================================
:: Install Pocket TTS
:: ============================================================

echo.
echo [2/3] Installing Pocket TTS...
echo [2/3] Installing Pocket TTS>>"%LOG%"

if not exist "%POCKET_TTS_DIR%\install_pocket_tts.bat" (
    echo [ERROR] install_pocket_tts.bat not found.
    pause
    exit /b 1
)

set "POCKET_TTS_PYTHON=%PYTHON_EXE%"
set "CALLED_FROM_PREPARE=1"

pushd "%POCKET_TTS_DIR%"

call install_pocket_tts.bat
if errorlevel 1 (
    popd
    echo.
    echo [ERROR] Pocket TTS installation failed.
    echo [ERROR] Pocket TTS installation failed>>"%LOG%"
    pause
    exit /b 1
)

popd

echo [OK] Pocket TTS installed>>"%LOG%"

:: ============================================================
:: Run Pocket TTS
:: ============================================================

echo.
echo Starting Pocket TTS...
echo Starting Pocket TTS>>"%LOG%"

start "Pocket TTS" cmd.exe /k ""%POCKET_TTS_DIR%\run_pocket_tts.bat""

:: ============================================================
:: Start MCP
:: ============================================================

echo.
echo [3/3] Starting Pet AI MCP...
echo [3/3] Starting MCP>>"%LOG%"

"%PYTHON_EXE%" -m pip show mcp >nul 2>&1

if errorlevel 1 (
    echo Installing MCP...
    "%PYTHON_EXE%" -m pip install mcp
)

start "Pet AI MCP" cmd /k ""%PYTHON_EXE%" "%MCP_DIR%\server.py""

:: ============================================================
:: Generate Airi config
:: ============================================================

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$py='%PYTHON_EXE%';" ^
"$srv='%MCP_DIR%\server.py';" ^
"@{mcpServers=@{'pet-ai'=@{command=$py;args=@($srv)}}}|ConvertTo-Json -Depth 5|Set-Content -Encoding UTF8 '%JSON_OUT%'"

echo [OK] airi_mcp_config.json written>>"%LOG%"

echo [LOG END] %date% %time%>>"%LOG%"

echo.
echo ========================================
echo All services started successfully.
echo ========================================
echo.
echo Airi MCP configuration has been written:
echo.
echo     %JSON_OUT%
echo.
pause
exit /b 0