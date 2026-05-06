#!/usr/bin/env python3
"""
Test script to verify all components are working
"""

import sys
from pathlib import Path

print("🔧 Testing LinkedIn Job Automation Setup...")
print("=" * 50)

# Test 1: Check required files
print("\n1️⃣ Checking required files...")
required_files = [
    ("config.py", "Configuration"),
    ("credentials.json", "Google Sheets credentials"),
    (".env", "Environment variables"),
    ("Karthik_Fullstack_Developer.pdf", "Resume"),
    ("job_search_config.json", "Job categories"),
    ("karthik_skills.json", "Skills profile")
]

all_files_ok = True
for file, desc in required_files:
    if Path(file).exists():
        print(f"   ✅ {desc}: {file}")
    else:
        print(f"   ❌ {desc}: {file} NOT FOUND")
        all_files_ok = False

# Test 2: Check Python imports
print("\n2️⃣ Checking Python dependencies...")
try:
    import fastapi
    print("   ✅ FastAPI")
except ImportError:
    print("   ❌ FastAPI not installed")
    all_files_ok = False

try:
    import browser_use
    print("   ✅ Browser-Use")
except ImportError:
    print("   ❌ Browser-Use not installed")
    all_files_ok = False

try:
    import openai
    print("   ✅ OpenAI")
except ImportError:
    print("   ❌ OpenAI not installed")
    all_files_ok = False

try:
    from google.oauth2 import service_account
    print("   ✅ Google API Client")
except ImportError:
    print("   ❌ Google API Client not installed")
    all_files_ok = False

try:
    import PyPDF2
    print("   ✅ PyPDF2")
except ImportError:
    print("   ❌ PyPDF2 not installed")
    all_files_ok = False

# Test 3: Check configuration
print("\n3️⃣ Checking configuration...")
try:
    from config import settings
    
    if settings.openai_api_key:
        print(f"   ✅ OpenAI API Key: ...{settings.openai_api_key[-8:]}")
    else:
        print("   ❌ OpenAI API Key not set")
        all_files_ok = False
    
    if settings.google_sheets_id:
        print(f"   ✅ Google Sheets ID: {settings.google_sheets_id[:15]}...")
    else:
        print("   ❌ Google Sheets ID not set")
        all_files_ok = False
    
    if settings.resume_file_path:
        print(f"   ✅ Resume configured: {settings.resume_file_path}")
    else:
        print("   ⚠️  Resume path not set (will use inline profile)")
    
except Exception as e:
    print(f"   ❌ Configuration error: {e}")
    all_files_ok = False

# Test 4: Test Google Sheets connection
print("\n4️⃣ Testing Google Sheets connection...")
try:
    from services.google_sheets_service import GoogleSheetsService
    sheets = GoogleSheetsService()
    url = sheets.get_spreadsheet_url()
    print(f"   ✅ Google Sheets connected")
    print(f"   📊 Sheet URL: {url}")
except Exception as e:
    print(f"   ⚠️  Google Sheets test failed: {e}")
    print("      (This is okay if you haven't shared the sheet yet)")

# Test 5: Load job configuration
print("\n5️⃣ Loading job search configuration...")
try:
    import json
    with open('job_search_config.json', 'r') as f:
        config = json.load(f)
    categories = config['job_categories']
    print(f"   ✅ Loaded {len(categories)} job categories:")
    for cat in categories:
        print(f"      • {cat['category']}")
except Exception as e:
    print(f"   ❌ Failed to load job config: {e}")
    all_files_ok = False

# Summary
print("\n" + "=" * 50)
if all_files_ok:
    print("✅ All tests passed! System is ready.")
    print("\n🚀 You can now run:")
    print("   python3 quick_search.py    # Search all job categories")
    print("   python3 app/main.py        # Start web interface")
else:
    print("❌ Some tests failed. Please fix the issues above.")
    sys.exit(1)