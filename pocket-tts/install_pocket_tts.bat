@echo off
setlocal EnableExtensions

title Pocket TTS - Installer

echo ========================================
echo Pocket TTS - Installer
echo ========================================
echo.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

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
    echo.
    echo [ERROR] Python 3.10+ not found.
    if not defined CALLED_FROM_PREPARE pause
    exit /b 1
)

for /f "tokens=2" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set PYTHON_VERSION=%%i

echo [OK] Using Python %PYTHON_VERSION%
echo.

:: ============================================================
:: Create / Verify Virtual Environment
:: ============================================================

set "VENV_DIR=%ROOT%\venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

set "RECREATE_VENV=0"

set "NEW_INSTALL=0"

if exist "%VENV_DIR%\pyvenv.cfg" (

    findstr /I /C:"%PYTHON_EXE%" "%VENV_DIR%\pyvenv.cfg" >nul

    if errorlevel 1 (
        echo.
        echo Existing virtual environment was created with another Python.
        echo Recreating virtual environment...
        set "RECREATE_VENV=1"
    )
)

if not exist "%VENV_PYTHON%" (
    set "RECREATE_VENV=1"
    set "NEW_INSTALL=1"
)

if "%RECREATE_VENV%"=="1" (

    if exist "%VENV_DIR%" (
        rmdir /S /Q "%VENV_DIR%"
    )

    echo.
    set "NEW_INSTALL=1"
    echo Creating virtual environment...

    "%PYTHON_EXE%" -m venv "%VENV_DIR%"

    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment.
        if not defined CALLED_FROM_PREPARE pause
        exit /b 1
    )
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo.
    echo [ERROR] Virtual environment is corrupted.
    if not defined CALLED_FROM_PREPARE pause
    exit /b 1
)
echo.
echo ========================================
echo Installing Dependencies
echo ========================================
echo.

echo [1/5] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to upgrade pip.
    if not defined CALLED_FROM_PREPARE pause
    exit /b 1
)

echo.
echo [2/5] Checking FFmpeg...

ffmpeg -version >nul 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] Bundled FFmpeg not found.
    echo Expected:
    echo    %ROOT%\..\ffmpeg\bin\ffmpeg.exe
    if not defined CALLED_FROM_PREPARE pause
    exit /b 1
)

echo [OK] FFmpeg ready.

echo.
echo [3/5] Installing PyTorch...

"%VENV_PYTHON%" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install PyTorch.
    if not defined CALLED_FROM_PREPARE pause
    exit /b 1
)

echo.
echo [4/5] Installing requirements...

if exist "%ROOT%\requirements.txt" (
    "%VENV_PYTHON%" -m pip install -r "%ROOT%\requirements.txt"

    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install requirements.
        if not defined CALLED_FROM_PREPARE pause
        exit /b 1
    )
)

echo.
echo [5/5] Installing Pocket TTS...

"%VENV_PYTHON%" -m pip install --upgrade pocket-tts

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install Pocket TTS.
    if not defined CALLED_FROM_PREPARE pause
    exit /b 1
)

:: ============================================================
:: Create folders
:: ============================================================

if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
if not exist "%ROOT%\output" mkdir "%ROOT%\output"
if not exist "%ROOT%\temp" mkdir "%ROOT%\temp"
if not exist "%ROOT%\voices-celebrities" mkdir "%ROOT%\voices-celebrities"
echo.
echo [6/6] Checking HuggingFace authentication...

call "%ROOT%\venv\Scripts\activate.bat"

hf auth whoami >nul 2>&1

if errorlevel 1 (
    echo.
    echo HuggingFace login required...
    call "%ROOT%\preflight_checks.bat"

    if errorlevel 1 (
        echo.
        echo [ERROR] HuggingFace authentication failed.
        if not defined CALLED_FROM_PREPARE pause
        exit /b 1
    )
) else (
    echo [OK] HuggingFace already authenticated.
)
echo.
echo ========================================
echo Installation Complete
echo ========================================
echo.
echo Python : %PYTHON_VERSION%
echo Venv   : %ROOT%\venv
echo.

if defined CALLED_FROM_PREPARE exit /b 0

echo.
choice /C YN /N /M "Run Pocket TTS now? (Y/N): "

if errorlevel 2 exit /b 0

call "%ROOT%\run_pocket_tts.bat"

exit /b 0