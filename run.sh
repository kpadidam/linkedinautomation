#!/bin/bash

# LinkedIn Job Automation - Startup Script

echo "Starting LinkedIn Job Automation System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies only when requirements.txt changes.
# Stamp the installed hash under venv/ so it survives across runs but
# vanishes if you blow away the venv. Pass --reinstall to force a full
# refresh (pip + playwright browsers).
REQ_HASH=$(shasum -a 256 requirements.txt | awk '{print $1}')
STAMP_FILE="venv/.requirements.sha256"
PW_STAMP="venv/.playwright.version"
NEEDS_PW_INSTALL=0

if [ "$1" = "--reinstall" ] || [ ! -f "$STAMP_FILE" ] || [ "$(cat "$STAMP_FILE" 2>/dev/null)" != "$REQ_HASH" ]; then
    echo "Installing Python dependencies (requirements.txt changed)..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo "$REQ_HASH" > "$STAMP_FILE"
    # Any pip install can bump the playwright version, which invalidates
    # the cached browser binary. Force a browser refresh in lockstep.
    NEEDS_PW_INSTALL=1
else
    echo "Python dependencies up to date — skipping pip install."
fi

# Also refresh browsers if the installed playwright version no longer
# matches the last successful stamp, or if the expected binary is gone.
PW_VERSION=$(python -c "import playwright; print(playwright.__version__)" 2>/dev/null || echo "unknown")
if [ "$NEEDS_PW_INSTALL" = "1" ] \
    || [ "$(cat "$PW_STAMP" 2>/dev/null)" != "$PW_VERSION" ] \
    || ! python -c "from playwright.sync_api import sync_playwright
import os, sys
p = sync_playwright().start()
ok = os.path.exists(p.chromium.executable_path)
p.stop()
sys.exit(0 if ok else 1)" >/dev/null 2>&1; then
    echo "Installing Playwright chromium (playwright=$PW_VERSION)..."
    playwright install chromium
    echo "$PW_VERSION" > "$PW_STAMP"
else
    echo "Playwright chromium matches playwright=$PW_VERSION — skipping browser install."
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Creating .env from template..."
    cp .env.example .env
    echo "Please edit .env and add your API keys before continuing."
    echo "Press Enter when ready..."
    read
fi

# Initialize database if not exists
if [ ! -f "linkedin_jobs.db" ]; then
    echo "Initializing database..."
    python database/models.py
fi

# Create necessary directories
mkdir -p data logs static

# Start the application
echo "Starting FastAPI server..."
echo "Access the application at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"

PYTHONPATH=. python app/main.py