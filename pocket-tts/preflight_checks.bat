@echo off
setlocal EnableExtensions

REM Assumes the virtual environment is already active.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "FFMPEG_DIR=%ROOT%\..\ffmpeg\bin"

echo [CHECK] Checking bundled FFmpeg...

if not exist "%FFMPEG_DIR%\ffmpeg.exe" (
    echo [ERROR] Bundled FFmpeg not found.
    echo Expected:
    echo    %FFMPEG_DIR%\ffmpeg.exe
    exit /b 1
)

set "PATH=%FFMPEG_DIR%;%PATH%"

ffmpeg -version >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Bundled FFmpeg could not be started.
    exit /b 1
)

echo [OK] Using bundled FFmpeg
echo.

echo [CHECK] Checking HuggingFace authentication...

hf auth whoami >nul 2>&1

if errorlevel 1 (
    call :hf_login
) else (
    echo [OK] HuggingFace authentication present
)

echo.
exit /b 0

:hf_login

echo [!] Not logged in to HuggingFace.
echo.
echo Pocket TTS needs HuggingFace credentials to download the
echo voice-cloning model from kyutai/pocket-tts.
echo.
echo Before continuing:
echo.
echo   1. Open:
echo      https://huggingface.co/kyutai/pocket-tts
echo.
echo   2. Click "Agree and access repository"
echo.
echo   3. Create a Read token:
echo      https://huggingface.co/settings/tokens
echo.
echo Press any key to start HuggingFace login...
pause >nul

hf auth login --add-to-git-credential

hf auth whoami >nul 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] HuggingFace login failed.
    echo Please run this installer again after logging in.
    exit /b 1
)

echo.
echo [OK] HuggingFace authentication configured.

exit /b 0