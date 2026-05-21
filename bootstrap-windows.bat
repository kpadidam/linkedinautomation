@echo off
REM =================================================================
REM LinkedIn Job Automation - Brand-new Windows laptop bootstrap
REM
REM This script installs EVERYTHING on a fresh Windows machine:
REM   1. Python 3.12 (via winget) if missing
REM   2. Node.js LTS  (via winget) if missing
REM   3. Git          (via winget) if missing
REM   4. Python venv + pinned dependencies (requirements-lock.txt)
REM   5. Playwright Chromium
REM   6. dashboard-ui npm packages
REM   7. .env scaffold from .env.example
REM
REM AFTER this finishes: edit .env, then double-click start.bat
REM
REM Requires Windows 10 1809+ or Windows 11 (winget is built in).
REM Must be run as Administrator the first time (for winget installs).
REM =================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ===============================================================
echo  LinkedIn Job Automation - Fresh-laptop bootstrap (Windows)
echo ===============================================================
echo.

REM --- admin check (needed for winget package installs) ---
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script must be run as Administrator the first time
    echo         so it can install Python / Node / Git via winget.
    echo         Right-click bootstrap-windows.bat -^> "Run as administrator"
    pause
    exit /b 1
)

REM --- winget check ---
where winget >nul 2>&1
if errorlevel 1 (
    echo [ERROR] winget not found. Update Windows or install
    echo         "App Installer" from the Microsoft Store, then retry.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------
REM 1) Python
REM ---------------------------------------------------------------
echo.
echo --- Checking Python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [INFO] Python not found - installing Python 3.12 via winget...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
    if errorlevel 1 (
        echo [ERROR] Python install failed.
        pause
        exit /b 1
    )
    REM Refresh PATH so 'python' resolves in this session
    call :refresh_path
) else (
    for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i
)

REM ---------------------------------------------------------------
REM 2) Node.js LTS
REM ---------------------------------------------------------------
echo.
echo --- Checking Node.js ---
where node >nul 2>&1
if errorlevel 1 (
    echo [INFO] Node.js not found - installing Node.js LTS via winget...
    winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements --silent
    if errorlevel 1 (
        echo [ERROR] Node install failed.
        pause
        exit /b 1
    )
    call :refresh_path
) else (
    for /f "tokens=*" %%i in ('node --version') do echo [OK] Node %%i
)

REM ---------------------------------------------------------------
REM 3) Git (handy, not strictly required)
REM ---------------------------------------------------------------
echo.
echo --- Checking Git ---
where git >nul 2>&1
if errorlevel 1 (
    echo [INFO] Git not found - installing via winget...
    winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements --silent
    call :refresh_path
) else (
    for /f "tokens=*" %%i in ('git --version') do echo [OK] %%i
)

REM ---------------------------------------------------------------
REM 4) Python venv + pinned deps
REM ---------------------------------------------------------------
echo.
echo --- Creating Python virtual environment ---
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Close this window, open a NEW
        echo         Administrator cmd and re-run bootstrap-windows.bat
        echo         (PATH refresh sometimes needs a new shell).
        pause
        exit /b 1
    )
)
call venv\Scripts\activate.bat

echo [INFO] Upgrading pip / wheel / setuptools...
python -m pip install --upgrade pip wheel setuptools

if not exist "requirements-lock.txt" (
    echo [ERROR] requirements-lock.txt missing from project root.
    pause
    exit /b 1
)
echo [INFO] Installing pinned Python dependencies (several minutes)...
pip install -r requirements-lock.txt
if errorlevel 1 (
    echo [ERROR] pip install failed - see messages above.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------
REM 5) Playwright Chromium
REM ---------------------------------------------------------------
echo.
echo --- Installing Playwright Chromium ---
playwright install chromium
if errorlevel 1 echo [WARN] Playwright install reported an error - continuing.

REM ---------------------------------------------------------------
REM 6) dashboard-ui npm install
REM ---------------------------------------------------------------
echo.
echo --- Installing dashboard-ui npm packages ---
if not exist "dashboard-ui\package.json" (
    echo [ERROR] dashboard-ui\package.json not found.
    pause
    exit /b 1
)
pushd dashboard-ui
call npm install
if errorlevel 1 (
    popd
    echo [ERROR] npm install failed.
    pause
    exit /b 1
)
popd

REM ---------------------------------------------------------------
REM 7) .env scaffold
REM ---------------------------------------------------------------
echo.
echo --- Configuring .env ---
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [INFO] Created .env from .env.example - EDIT IT before running.
    ) else (
        echo [WARN] No .env.example found. Create .env manually.
    )
) else (
    echo [OK] .env already exists.
)

echo.
echo ===============================================================
echo  Bootstrap complete.
echo  Next steps:
echo    1. Edit .env with your API keys / secrets
echo    2. Drop your Google service-account JSON at config\credentials.json
echo    3. Put your resume at resumes\resume.pdf
echo    4. Double-click start.bat
echo ===============================================================
echo.
pause
exit /b 0

REM ---------------------------------------------------------------
REM Helper: reload PATH from registry so freshly-installed tools
REM are visible in THIS cmd session (winget updates the registry
REM but does not push it into already-running shells).
REM ---------------------------------------------------------------
:refresh_path
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul ^| findstr /i "Path"') do set "SYS_PATH=%%B"
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul ^| findstr /i "Path"') do set "USR_PATH=%%B"
set "PATH=%SYS_PATH%;%USR_PATH%"
exit /b 0
