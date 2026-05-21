@echo off
REM =================================================================
REM LinkedIn Job Automation - Windows one-time setup
REM   * Creates venv
REM   * Installs PINNED Python deps from requirements-lock.txt
REM     (no version-resolver conflicts)
REM   * Installs Playwright Chromium
REM   * Installs dashboard-ui npm deps
REM Run this ONCE on a fresh Windows machine. Then use start.bat.
REM =================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo === LinkedIn Job Automation - Windows setup ===
echo.

REM --- python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Install Python 3.11+ from https://python.org
    echo         and tick "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [INFO] %%i

REM --- node ---
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found in PATH. Install from https://nodejs.org (LTS).
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo [INFO] Node %%i

REM --- venv ---
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo [INFO] Upgrading pip / wheel / setuptools...
python -m pip install --upgrade pip wheel setuptools

REM --- python deps from the LOCK file (avoids resolver conflicts) ---
if not exist "requirements-lock.txt" (
    echo [ERROR] requirements-lock.txt missing.
    pause
    exit /b 1
)
echo [INFO] Installing pinned Python dependencies (this may take a few minutes)...
pip install -r requirements-lock.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. See messages above.
    pause
    exit /b 1
)

REM --- playwright chromium ---
echo [INFO] Installing Playwright Chromium...
playwright install chromium
if errorlevel 1 (
    echo [WARN] Playwright install reported an error - continuing.
)

REM --- .env scaffold ---
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example - edit it before first run.
        copy ".env.example" ".env" >nul
    ) else (
        echo [WARN] .env.example not found. Create .env manually.
    )
)

REM --- dashboard-ui ---
if not exist "dashboard-ui\package.json" (
    echo [ERROR] dashboard-ui\package.json not found.
    pause
    exit /b 1
)
echo [INFO] Installing dashboard-ui npm packages...
pushd dashboard-ui
call npm install
if errorlevel 1 (
    popd
    echo [ERROR] npm install failed.
    pause
    exit /b 1
)
popd

echo.
echo === Setup complete ===
echo Next: edit .env, then run   start.bat
echo.
pause
