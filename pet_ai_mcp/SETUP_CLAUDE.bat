@echo off
setlocal enabledelayedexpansion
title Pet AI - Setup Claude Desktop

echo.
echo  =========================================
echo   Pet AI - Claude Desktop Setup
echo  =========================================
echo.

:: ── Find where THIS script lives (that's where server.py is) ─
set "SERVER_PATH=%~dp0server.py"
:: Convert single backslashes to double for JSON
set "SERVER_JSON_PATH=%SERVER_PATH:\=\\%"

:: ── Find Claude Desktop config folder ────────────────────────
set "CONFIG_DIR=%APPDATA%\Claude"
set "CONFIG_FILE=%CONFIG_DIR%\claude_desktop_config.json"

if not exist "%CONFIG_DIR%" (
    echo  [ERROR] Claude Desktop does not seem to be installed.
    echo          Please install it from https://claude.ai/download first.
    echo.
    pause
    exit /b 1
)

:: ── Write the config file ─────────────────────────────────────
echo  [..] Writing Claude Desktop config...

(
echo {
echo   "mcpServers": {
echo     "pet-ai": {
echo       "command": "python",
echo       "args": ["%SERVER_JSON_PATH%"]
echo     }
echo   }
echo }
) > "%CONFIG_FILE%"

echo  [OK] Config written to:
echo       %CONFIG_FILE%
echo.
echo  =========================================
echo   Done! Now do this:
echo.
echo   1. Fully QUIT Claude Desktop
echo      (right-click its icon in the taskbar ^ choose Quit)
echo.
echo   2. Open Claude Desktop again
echo.
echo   3. Start a new chat - you will see a small
echo      tools icon near the message box!
echo  =========================================
echo.
pause
