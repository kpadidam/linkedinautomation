@echo off
REM =================================================================
REM LinkedIn Job Automation - Windows one-click launcher
REM Starts the FastAPI backend AND the Vite dashboard UI in parallel.
REM Each runs in its own console window so you can read logs / Ctrl+C.
REM =================================================================

setlocal

cd /d "%~dp0"

REM --- sanity checks ---
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Python venv not found. Run setup-windows.bat first.
    pause
    exit /b 1
)

if not exist "dashboard-ui\node_modules" (
    echo [ERROR] dashboard-ui\node_modules missing. Run setup-windows.bat first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [WARNING] .env not found. The backend may fail to load secrets.
)

echo.
echo Starting backend (http://localhost:8000) and dashboard UI (http://localhost:5173)...
echo Close the spawned windows or press Ctrl+C in each to stop.
echo.

REM --- backend: activate venv and run as module (so 'config' import works) ---
start "linkedin-backend" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python -m app.main"

REM --- frontend: vite dev server ---
start "linkedin-dashboard-ui" cmd /k "cd /d %~dp0dashboard-ui && npm run dev"

echo Both services launching in new windows.
echo  - Backend:   http://localhost:8000  (API docs: /docs)
echo  - Dashboard: http://localhost:5173
echo.
endlocal
