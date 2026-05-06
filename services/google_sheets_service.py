"""Google Sheets integration service for real-time job logging."""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import settings
from models.job_model import JobListing, GoogleSheetRow

logger = logging.getLogger(__name__)

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsService:
    """Service for interacting with Google Sheets."""
    
    def __init__(self, spreadsheet_id: Optional[str] = None):
        """
        Initialize Google Sheets service.
        
        Args:
            spreadsheet_id: Google Sheets ID (uses config default if not provided)
        """
        self.spreadsheet_id = spreadsheet_id or settings.google_sheets_id
        self.service = None
        self.credentials = None
        self.cached_job_ids = set()  # Cache for existing job IDs
        self._authenticate()
        self._load_existing_job_ids()  # Load existing IDs on initialization
        
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        try:
            creds_path = settings.google_sheets_credentials_path
            
            # Check if credentials file exists
            if os.path.exists(creds_path):
                # Load credentials from file
                if creds_path.endswith('.json'):
                    # Service account or OAuth2 credentials
                    try:
                        # Try service account first
                        self.credentials = service_account.Credentials.from_service_account_file(
                            creds_path, scopes=SCOPES
                        )
                    except Exception:
                        # Try OAuth2 credentials
                        flow = InstalledAppFlow.from_client_secrets_file(
                            creds_path, SCOPES
                        )
                        self.credentials = flow.run_local_server(port=0)
                
                # Build the service
                self.service = build('sheets', 'v4', credentials=self.credentials)
                logger.info("Successfully authenticated with Google Sheets API")
                
            else:
                logger.warning(f"Credentials file not found at {creds_path}")
                logger.warning("Please set up Google Sheets credentials to enable logging")
                
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            raise
    
    def _load_existing_job_ids(self):
        """Load existing job IDs from the spreadsheet into cache."""
        try:
            if not self.service or not self.spreadsheet_id:
                logger.warning("Cannot load job IDs: service not initialized or no spreadsheet ID")
                return
            
            # Get all job IDs from column A (Job ID column)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='A:A'
            ).execute()
            
            values = result.get('values', [])
            
            # Skip header row and add all job IDs to cache
            for row in values[1:]:  # Skip header
                if row and row[0]:  # Check if row exists and has a value
                    self.cached_job_ids.add(row[0])
            
            logger.info(f"Loaded {len(self.cached_job_ids)} existing job IDs into cache")
            
        except HttpError as e:
            if 'Unable to parse range' in str(e) or '404' in str(e):
                # Spreadsheet might be empty or not exist yet
                logger.info("No existing jobs found or spreadsheet is empty")
            else:
                logger.error(f"Failed to load existing job IDs: {e}")
        except Exception as e:
            logger.warning(f"Could not load existing job IDs: {e}")
    
    def create_spreadsheet(self, title: str = "LinkedIn Jobs") -> str:
        """
        Create a new Google Spreadsheet.
        
        Args:
            title: Title for the new spreadsheet
            
        Returns:
            Spreadsheet ID
        """
        try:
            spreadsheet = {
                'properties': {
                    'title': f"{title} - {datetime.now().strftime('%Y-%m-%d')}"
                },
                'sheets': [{
                    'properties': {
                        'title': 'Jobs',
                        'gridProperties': {
                            'frozenRowCount': 1
                        }
                    }
                }]
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result['spreadsheetId']
            
            logger.info(f"Created new spreadsheet with ID: {spreadsheet_id}")
            
            # Initialize with headers
            self._initialize_headers(spreadsheet_id)
            
            return spreadsheet_id
            
        except HttpError as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            raise
    
    def _initialize_headers(self, spreadsheet_id: Optional[str] = None):
        """Initialize spreadsheet with headers."""
        try:
            sheet_id = spreadsheet_id or self.spreadsheet_id
            headers = GoogleSheetRow.get_headers()
            
            # Add headers to first row
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Format header row
            self._format_header_row(sheet_id)
            
            logger.info("Initialized spreadsheet with headers")
            
        except HttpError as e:
            logger.error(f"Failed to initialize headers: {e}")
            raise
    
    def _format_header_row(self, spreadsheet_id: Optional[str] = None):
        """Format the header row with bold text and background color."""
        try:
            sheet_id = spreadsheet_id or self.spreadsheet_id
            
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.5,
                                'blue': 0.8
                            },
                            'textFormat': {
                                'bold': True,
                                'foregroundColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 1.0
                                }
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }, {
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': 0,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 15
                    }
                }
            }]
            
            body = {'requests': requests}
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=body
            ).execute()
            
        except HttpError as e:
            logger.error(f"Failed to format header row: {e}")
    
    def add_job(self, job: JobListing):
        """
        Add a single job to the spreadsheet.
        
        Args:
            job: JobListing to add
        """
        try:
            if not self.service:
                logger.warning("Google Sheets service not initialized, skipping job logging")
                return
            
            # Check if job already exists in cache
            if job.job_id in self.cached_job_ids:
                logger.info(f"Skipping duplicate job: {job.job_id} - '{job.title}' at '{job.company}'")
                return
            
            # Convert job to Google Sheets row
            row = GoogleSheetRow.from_job_listing(job)
            
            # Append to spreadsheet
            body = {
                'values': [row.to_list()]
            }
            
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='A:P',  # Updated range to include Job ID column
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            # Add job ID to cache after successful addition
            self.cached_job_ids.add(job.job_id)
            
            logger.info(f"Added job '{job.title}' at '{job.company}' to spreadsheet")
            
        except HttpError as e:
            logger.error(f"Failed to add job to spreadsheet: {e}")
            raise
    
    def add_jobs_batch(self, jobs: List[JobListing]):
        """
        Add multiple jobs to the spreadsheet in a batch.
        
        Args:
            jobs: List of JobListings to add
        """
        try:
            if not self.service:
                logger.warning("Google Sheets service not initialized, skipping batch logging")
                return
            
            if not jobs:
                logger.warning("No jobs to add")
                return
            
            # Filter out duplicates using cache
            new_jobs = [job for job in jobs if job.job_id not in self.cached_job_ids]
            
            if not new_jobs:
                logger.info(f"All {len(jobs)} jobs are duplicates, skipping batch")
                return
            
            # Log how many duplicates were filtered
            duplicate_count = len(jobs) - len(new_jobs)
            if duplicate_count > 0:
                logger.info(f"Filtered out {duplicate_count} duplicate jobs")
            
            # Convert new jobs to rows
            rows = [GoogleSheetRow.from_job_listing(job).to_list() for job in new_jobs]
            
            # Batch append to spreadsheet
            body = {
                'values': rows
            }
            
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='A:P',  # Updated range to include Job ID column
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            # Update cache with new job IDs
            for job in new_jobs:
                self.cached_job_ids.add(job.job_id)
            
            logger.info(f"Added {len(new_jobs)} new jobs to spreadsheet in batch")
            
        except HttpError as e:
            logger.error(f"Failed to add jobs batch to spreadsheet: {e}")
            raise
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Retrieve all jobs from the spreadsheet.
        
        Returns:
            List of job dictionaries
        """
        try:
            if not self.service:
                logger.warning("Google Sheets service not initialized")
                return []
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='A:Q'  # Includes Job ID column
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return []
            
            # First row is headers
            headers = values[0]
            jobs = []
            
            # Convert each row to dictionary
            for row in values[1:]:
                job_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        job_dict[header] = row[i]
                    else:
                        job_dict[header] = ""
                jobs.append(job_dict)
            
            return jobs
            
        except HttpError as e:
            logger.error(f"Failed to retrieve jobs from spreadsheet: {e}")
            return []
    
    def update_job_status(self, row_number: int, status: str):
        """
        Update the status of a job in the spreadsheet.
        
        Args:
            row_number: Row number to update (1-indexed, excluding header)
            status: New status value
        """
        try:
            if not self.service:
                logger.warning("Google Sheets service not initialized")
                return
            
            # Status is in column Q (17th column) now that Job ID is first
            range_name = f'Q{row_number + 1}'  # +1 for header
            
            body = {
                'values': [[status]]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"Updated job status in row {row_number} to '{status}'")
            
        except HttpError as e:
            logger.error(f"Failed to update job status: {e}")
            raise
    
    def refresh_cache(self):
        """
        Refresh the cache of existing job IDs.
        Useful for long-running sessions or when external changes occur.
        """
        logger.info("Refreshing job ID cache...")
        self.cached_job_ids.clear()
        self._load_existing_job_ids()
    
    def check_duplicate(self, job_id: str) -> bool:
        """
        Check if a job already exists in the spreadsheet.
        Uses cache for fast lookup.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            True if duplicate exists, False otherwise
        """
        return job_id in self.cached_job_ids
    
    def get_spreadsheet_url(self) -> str:
        """
        Get the URL to view the spreadsheet.
        
        Returns:
            Spreadsheet URL
        """
        if self.spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        return ""
    
    def add_conditional_formatting(self):
        """Add conditional formatting to highlight high-match jobs."""
        try:
            if not self.service:
                return
            
            requests = [{
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': 0,
                            'startColumnIndex': 10,  # Resume Match % column
                            'endColumnIndex': 11
                        }],
                        'gradientRule': {
                            'minpoint': {
                                'color': {
                                    'red': 1.0,
                                    'green': 0.4,
                                    'blue': 0.4
                                },
                                'type': 'MIN'
                            },
                            'midpoint': {
                                'color': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 0.4
                                },
                                'type': 'PERCENTILE',
                                'value': '50'
                            },
                            'maxpoint': {
                                'color': {
                                    'red': 0.4,
                                    'green': 1.0,
                                    'blue': 0.4
                                },
                                'type': 'MAX'
                            }
                        }
                    }
                }
            }]
            
            body = {'requests': requests}
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            logger.info("Added conditional formatting to spreadsheet")
            
        except HttpError as e:
            logger.error(f"Failed to add conditional formatting: {e}")


def test_google_sheets():
    """Test Google Sheets service."""
    try:
        # Initialize service
        sheets_service = GoogleSheetsService()
        
        # Create test job
        test_job = JobListing(
            job_id="test123",
            title="Software Engineer",
            company="Test Company",
            location="San Francisco, CA",
            description="Test job description",
            keywords=["Python", "JavaScript"],
            skills=["Programming", "Problem Solving"],
            resume_match_score=85.5
        )
        
        # Add job to sheet
        sheets_service.add_job(test_job)
        
        print(f"Test successful! View spreadsheet at: {sheets_service.get_spreadsheet_url()}")
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    test_google_sheets()