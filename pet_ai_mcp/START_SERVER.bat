@echo off
setlocal enabledelayedexpansion
title Pet AI - MCP Server

:: ============================================================
::  Pet AI MCP Server - Windows Auto-Installer
::  Double-click this file. That's it!
:: ============================================================

echo.
echo  =========================================
echo   Welcome to Pet AI MCP Server!
echo  =========================================
echo.

:: ── 1. Check if Python is already installed ─────────────────
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] Python is already installed.
    goto :install_deps
)

:: ── 2. Python not found — download and install silently ──────
echo  [..] Python not found. Downloading Python installer...
echo       This will take about 1-2 minutes. Please wait!
echo.

set PYTHON_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe
set PYTHON_INSTALLER=%TEMP%\python_installer.exe

:: Download using PowerShell (built into every modern Windows)
powershell -Command "& { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' }"

if not exist "%PYTHON_INSTALLER%" (
    echo.
    echo  [ERROR] Could not download Python.
    echo          Please check your internet connection and try again.
    pause
    exit /b 1
)

echo  [..] Installing Python silently (no windows will pop up)...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1

:: Refresh PATH so python command works in this session
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312\;%LOCALAPPDATA%\Programs\Python\Python312\Scripts\;%PATH%"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Python installation failed.
    echo          Try restarting this script, or visit https://python.org to install manually.
    pause
    exit /b 1
)

echo  [OK] Python installed successfully!
del "%PYTHON_INSTALLER%" >nul 2>&1

:: ── 3. Install the MCP library ───────────────────────────────
:install_deps
echo.
echo  [..] Installing required libraries (only happens once)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet mcp

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Could not install libraries.
    echo          Check your internet connection and try again.
    pause
    exit /b 1
)

echo  [OK] Libraries ready!

:: ── 4. Start the MCP server ──────────────────────────────────
echo.
echo  =========================================
echo   Pet AI MCP Server is now RUNNING!
echo.
echo   Keep this window open while using Claude.
echo   Close it to stop the server.
echo  =========================================
echo.

:: Get the folder where THIS batch file lives
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%server.py"

:: If server exits, pause so user can read any error
echo.
echo  Server stopped.
pause
