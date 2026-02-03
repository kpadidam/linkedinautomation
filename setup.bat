@echo off
REM =================================================================
REM LinkedIn Job Automation - Complete Setup Script (Windows)
REM =================================================================
REM This script will install everything needed to run the project on Windows

setlocal EnableDelayedExpansion

echo.
echo ==========================================
echo LinkedIn Job Automation - Complete Setup
echo ==========================================
echo This script will install everything needed to run the project
echo.

REM Ask for confirmation
set /p "confirm=Do you want to continue? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Setup cancelled
    exit /b 0
)

echo.
echo [INFO] Starting setup for Windows...

REM Check for Python
echo.
echo ==========================================
echo Checking Python Installation
echo ==========================================

python --version >nul 2>&1
if %errorlevel%==0 (
    echo [SUCCESS] Python found
    set PYTHON_CMD=python
    set PIP_CMD=pip
) else (
    python3 --version >nul 2>&1
    if %errorlevel%==0 (
        echo [SUCCESS] Python3 found
        set PYTHON_CMD=python3
        set PIP_CMD=pip3
    ) else (
        echo [ERROR] Python not found!
        echo Please install Python 3.8+ from https://python.org
        echo Make sure to check "Add Python to PATH" during installation
        pause
        exit /b 1
    )
)

REM Display Python version
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [INFO] Using: %PYTHON_VERSION%

REM Check for pip
%PIP_CMD% --version >nul 2>&1
if %errorlevel%==0 (
    echo [SUCCESS] pip found
) else (
    echo [ERROR] pip not found! Please reinstall Python with pip included
    pause
    exit /b 1
)

REM Check for Node.js
echo.
echo ==========================================
echo Checking Node.js Installation
echo ==========================================

node --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo [SUCCESS] Node.js found: !NODE_VERSION!
) else (
    echo [WARNING] Node.js not found
    echo Please install Node.js from https://nodejs.org
    echo This is needed for some browser dependencies
)

REM Create virtual environment
echo.
echo ==========================================
echo Creating Python Virtual Environment
echo ==========================================

if not exist "venv" (
    echo [INFO] Creating virtual environment...
    %PYTHON_CMD% -m venv venv
    echo [SUCCESS] Virtual environment created
) else (
    echo [SUCCESS] Virtual environment already exists
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install Python dependencies
echo.
echo ==========================================
echo Installing Python Dependencies
echo ==========================================

if exist "requirements.txt" (
    echo [INFO] Installing requirements from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel%==0 (
        echo [SUCCESS] Python dependencies installed
    ) else (
        echo [ERROR] Failed to install Python dependencies
        pause
        exit /b 1
    )
) else (
    echo [ERROR] requirements.txt not found!
    pause
    exit /b 1
)

REM Install Playwright browsers
echo.
echo ==========================================
echo Installing Playwright Browsers
echo ==========================================

echo [INFO] Installing Playwright browsers...
playwright install chromium
if %errorlevel%==0 (
    echo [SUCCESS] Playwright and Chromium installed
) else (
    echo [ERROR] Failed to install Playwright browsers
    pause
    exit /b 1
)

REM Setup configuration files
echo.
echo ==========================================
echo Setting Up Configuration Files
echo ==========================================

REM Create .env file from example
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy ".env.example" ".env"
        echo [WARNING] Please edit .env file with your API keys and configuration
    ) else (
        echo [ERROR] .env.example not found!
    )
) else (
    echo [SUCCESS] .env file already exists
)

REM Create config directory and credentials template
if not exist "config" mkdir config

if not exist "config\credentials.json" (
    echo [INFO] Creating Google credentials template...
    (
        echo {
        echo   "type": "service_account",
        echo   "project_id": "your-project-id",
        echo   "private_key_id": "your-private-key-id",
        echo   "private_key": "your-private-key",
        echo   "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
        echo   "client_id": "your-client-id",
        echo   "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        echo   "token_uri": "https://oauth2.googleapis.com/token",
        echo   "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        echo   "client_x509_cert_url": "your-x509-cert-url",
        echo   "universe_domain": "googleapis.com"
        echo }
    ) > config\credentials.json
    echo [WARNING] Please replace config\credentials.json with your actual Google Cloud credentials
) else (
    echo [SUCCESS] Google credentials file already exists
)

REM Check for resume
if not exist "resumes" mkdir resumes
if not exist "resumes\resume.pdf" (
    echo [WARNING] Please add your resume as 'resumes\resume.pdf'
) else (
    echo [SUCCESS] Resume file found
)

REM Test the setup
echo.
echo ==========================================
echo Testing Setup
echo ==========================================

echo [INFO] Testing Python imports...
python -c "import config; print('✓ Config loads successfully')" 2>nul
if %errorlevel%==0 (
    echo [SUCCESS] Python configuration test passed
) else (
    echo [WARNING] Python configuration test failed - you may need to configure your .env file
)

echo [INFO] Testing browser installation...
python -c "from playwright.sync_api import sync_playwright; print('✓ Playwright works')" 2>nul
if %errorlevel%==0 (
    echo [SUCCESS] Playwright test passed
) else (
    echo [WARNING] Playwright test failed
)

REM Final instructions
echo.
echo ==========================================
echo 🎉 Setup Complete!
echo ==========================================
echo.
echo [SUCCESS] Everything is installed and ready to go!
echo.
echo Next steps:
echo 1. Edit .env file with your API keys
echo 2. Replace config\credentials.json with your Google Cloud credentials
echo 3. Add your resume as resumes\resume.pdf
echo 4. Run the project:
echo.
echo    venv\Scripts\activate.bat
echo    python linkedin.py
echo.
echo See config\README.md for detailed configuration help
echo.
pause