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

# Install/update dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Install Playwright browsers if not already installed
echo "Checking Playwright browsers..."
playwright install chromium --with-deps

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

# Create necessary directories if needed
mkdir -p logs

# Start the application
echo "Starting FastAPI server..."
echo "Access the application at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"

python app/main.py