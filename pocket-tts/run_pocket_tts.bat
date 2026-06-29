@echo off
setlocal EnableExtensions

title Pocket TTS - Server

echo ========================================
echo Pocket TTS - Server
echo ========================================
echo.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

cd /d "%ROOT%"

set "FFMPEG_DIR=%ROOT%\..\ffmpeg\bin"

if exist "%FFMPEG_DIR%\ffmpeg.exe" (
    set "PATH=%FFMPEG_DIR%;%PATH%"
)

:: ============================================================
:: Read Python path
:: ============================================================

set "PYTHON_FILE=%ROOT%\..\python_path.txt"
set "PYTHON_EXE="

if exist "%PYTHON_FILE%" (
    set /p PYTHON_EXE=<"%PYTHON_FILE%"
)

if not defined PYTHON_EXE (
    where py >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)"') do (
            set "PYTHON_EXE=%%i"
        )
    )
)

if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%i in ('where python') do (
            set "PYTHON_EXE=%%i"
            goto :PythonFound
        )
    )
)

:PythonFound

if not defined PYTHON_EXE (
    echo [ERROR] Python not found.
    echo Please run Prepare.bat first.
    pause
    exit /b 1
)

echo [OK] Python: %PYTHON_EXE%
echo.

:: ============================================================
:: Verify installation
:: ============================================================

if not exist "%ROOT%\venv" (
    echo [ERROR] Virtual environment not found.
    echo Run install_pocket_tts.bat first.
    pause
    exit /b 1
)

call "%ROOT%\venv\Scripts\activate.bat"

if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: ============================================================
:: Ensure folders
:: ============================================================

if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
if not exist "%ROOT%\output" mkdir "%ROOT%\output"
if not exist "%ROOT%\temp" mkdir "%ROOT%\temp"
if not exist "%ROOT%\voices-celebrities" mkdir "%ROOT%\voices-celebrities"

:: ============================================================
:: Read config.json
:: ============================================================

set "HOST=localhost"
set "PORT=8000"

if exist "%ROOT%\config.json" (

    for /f "tokens=2 delims=:, " %%A in ('findstr /i "\"host\"" "%ROOT%\config.json"') do (
        set "HOST=%%~A"
        set "HOST=%HOST:"=%"
        set "HOST=%HOST: =%"
    )

    for /f "tokens=2 delims=:, " %%A in ('findstr /i "\"port\"" "%ROOT%\config.json"') do (
        set "PORT=%%~A"
        set "PORT=%PORT:"=%"
        set "PORT=%PORT: =%"
    )
)

echo ========================================
echo Pocket TTS Ready
echo ========================================
echo.
echo Web UI  : http://%HOST%:%PORT%
echo API Docs: http://%HOST%:%PORT%/docs
echo Health  : http://%HOST%:%PORT%/health
echo.
echo Press Ctrl+C to stop the server.
echo.

:START

if exist "%ROOT%\pocket_tts_api.py" (
    echo Starting Enhanced API...
    "%ROOT%\venv\Scripts\python.exe" pocket_tts_api.py
) else (
    echo Starting Pocket TTS...
    "%ROOT%\venv\Scripts\python.exe" -m pocket_tts serve --host %HOST% --port %PORT%
)

echo.
echo Server stopped.
echo.

if defined CALLED_FROM_PREPARE exit /b 0

choice /C YN /N /M "Restart server? (Y/N): "

if errorlevel 2 exit /b 0

goto START