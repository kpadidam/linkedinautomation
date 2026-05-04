#!/usr/bin/env python3
"""
Test script to verify Google Sheets integration is working correctly.
Run this after setting up your credentials and sharing your sheet.
"""

import os
import sys
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_google_sheets_connection():
    """Test the Google Sheets API connection and permissions."""
    
    print("=" * 50)
    print("Google Sheets Integration Test")
    print("=" * 50)
    
    # Check for credentials file
    creds_path = "credentials.json"
    if not os.path.exists(creds_path):
        print("❌ ERROR: credentials.json file not found!")
        print("   Please ensure credentials.json exists in the project directory.")
        return False
    
    print("✅ Found credentials.json")
    
    try:
        # Load credentials
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        
        # Get service account email
        with open(creds_path, 'r') as f:
            import json
            creds_data = json.load(f)
            service_account_email = creds_data.get('client_email')
        
        print(f"✅ Loaded credentials for: {service_account_email}")
        
        # Build the service
        service = build('sheets', 'v4', credentials=credentials)
        print("✅ Connected to Google Sheets API")
        
        # Ask for Sheet ID if not in environment
        from dotenv import load_dotenv
        load_dotenv()
        
        sheet_id = os.getenv('GOOGLE_SHEETS_ID')
        
        if not sheet_id:
            print("\n⚠️  No GOOGLE_SHEETS_ID found in .env file")
            print("\nTo get your Sheet ID:")
            print("1. Create a new Google Sheet")
            print(f"2. Share it with: {service_account_email}")
            print("3. Set permission to: Editor")
            print("4. Copy the ID from the URL: https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit")
            print("\nEnter your Google Sheet ID (or press Enter to create a test sheet): ")
            sheet_id = input().strip()
        
        if not sheet_id:
            # Create a test sheet
            print("\nCreating a test Google Sheet...")
            spreadsheet = {
                'properties': {
                    'title': f'LinkedIn Jobs Test - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                }
            }
            
            result = service.spreadsheets().create(body=spreadsheet).execute()
            sheet_id = result['spreadsheetId']
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            
            print(f"✅ Created test sheet!")
            print(f"   Sheet ID: {sheet_id}")
            print(f"   URL: {sheet_url}")
            print(f"\n⚠️  IMPORTANT: You must share this sheet with the service account!")
            print(f"   1. Open: {sheet_url}")
            print(f"   2. Click 'Share'")
            print(f"   3. Add: {service_account_email}")
            print(f"   4. Set to: Editor")
            print(f"   5. Click 'Share'")
            print(f"\nAdd this to your .env file:")
            print(f"GOOGLE_SHEETS_ID={sheet_id}")
            
        else:
            # Test existing sheet
            print(f"\nTesting access to sheet: {sheet_id}")
            
            try:
                # Try to read the sheet
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range='A1:Z1'
                ).execute()
                
                print("✅ Successfully read from sheet")
                
                # Try to write test data
                test_data = [[
                    "Test Date",
                    "Test Time", 
                    "Test Job Title",
                    "Test Company",
                    "Test Location",
                    "This is a test entry from the integration script"
                ]]
                
                body = {'values': test_data}
                
                result = service.spreadsheets().values().append(
                    spreadsheetId=sheet_id,
                    range='A1',
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body=body
                ).execute()
                
                print("✅ Successfully wrote test data to sheet")
                print(f"\n🎉 Google Sheets integration is working perfectly!")
                print(f"\nSheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
                
                # Update .env if needed
                if not os.getenv('GOOGLE_SHEETS_ID'):
                    print(f"\n📝 Add this to your .env file:")
                    print(f"GOOGLE_SHEETS_ID={sheet_id}")
                
                return True
                
            except HttpError as e:
                if e.resp.status == 403:
                    print(f"\n❌ ERROR: Permission denied!")
                    print(f"   The service account doesn't have access to this sheet.")
                    print(f"\n   Please share the sheet with: {service_account_email}")
                    print(f"   And set permission to: Editor")
                elif e.resp.status == 404:
                    print(f"\n❌ ERROR: Sheet not found!")
                    print(f"   The sheet ID '{sheet_id}' doesn't exist or is not accessible.")
                else:
                    print(f"\n❌ ERROR: {e}")
                return False
                
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("\n🔧 Testing Google Sheets Integration...\n")
    
    success = test_google_sheets_connection()
    
    if success:
        print("\n✅ All tests passed! Your Google Sheets integration is ready to use.")
        print("\nYou can now run the main application:")
        print("  python app/main.py")
    else:
        print("\n❌ Tests failed. Please fix the issues above and try again.")
        sys.exit(1)