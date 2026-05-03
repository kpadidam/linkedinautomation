"""
Flask API server to connect the HTML dashboard with LinkedIn scraper and Google Sheets
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.google_sheets_service import GoogleSheetsService
from services.resume_matcher import ResumeMatcher
from scrapers.linkedin_scraper_playwright import LinkedInJobScraper
from database.db_manager import JobDatabase
from models.job_model import JobListing
import asyncio
from datetime import datetime
import threading

app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS for all routes

# Initialize services
sheets_service = GoogleSheetsService()
resume_matcher = ResumeMatcher()
job_db = JobDatabase()
scraper = None  # Will be initialized on demand

# Serve the dashboard
@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# API Routes
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics from database and Google Sheets"""
    try:
        # Get stats from database
        recent_jobs = job_db.get_recent_jobs(limit=100)
        
        # Calculate statistics
        total_jobs = len(recent_jobs)
        avg_match = sum([job.resume_match_score or 0 for job in recent_jobs]) / max(total_jobs, 1)
        
        # Get active searches (mock for now)
        active_searches = 0  # Would track running scrapers
        
        # Get sheets sync info
        sheets_info = sheets_service.get_spreadsheet_info() if sheets_service.sheets_id else {}
        sheets_synced = sheets_info.get('total_rows', 0)
        
        return jsonify({
            'totalJobs': total_jobs,
            'activeSearches': active_searches,
            'averageMatch': round(avg_match, 1),
            'sheetsSynced': sheets_synced,
            'recentActivity': get_recent_activity()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/search', methods=['POST'])
def search_jobs():
    """Start a new job search"""
    try:
        data = request.json
        keywords = data.get('keywords', '')
        location = data.get('location', '')
        job_type = data.get('jobType', '')
        
        # Run scraper in background
        def run_scraper():
            global scraper
            scraper = LinkedInJobScraper(headless=True)
            
            # Run the async scraper
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            jobs = loop.run_until_complete(
                scraper.search_jobs(
                    keywords=keywords,
                    location=location,
                    job_type=job_type,
                    num_jobs=50
                )
            )
            
            # Process each job
            for job_data in jobs:
                # Create JobListing object
                job = JobListing(**job_data)
                
                # Calculate match score
                if data.get('aiMatching'):
                    analysis = resume_matcher.analyze_job_fit(
                        job_description=job.description,
                        job_requirements=job.requirements
                    )
                    job.resume_match_score = analysis.overall_match_score
                
                # Save to database
                job_db.save_job(job)
                
                # Sync to Google Sheets if enabled
                if data.get('googleSheets'):
                    sheets_service.append_job(job)
            
            loop.close()
            return len(jobs)
        
        # Start search in background thread
        thread = threading.Thread(target=run_scraper)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Search started',
            'searchId': f'search_{datetime.now().timestamp()}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/recent', methods=['GET'])
def get_recent_jobs():
    """Get recent jobs from database"""
    try:
        limit = request.args.get('limit', 50, type=int)
        jobs = job_db.get_recent_jobs(limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(jobs),
            'jobs': [job.dict() for job in jobs]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_details(job_id):
    """Get detailed job information"""
    try:
        job = job_db.get_job_by_id(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Get AI analysis if not already done
        if not job.resume_match_score:
            analysis = resume_matcher.analyze_job_fit(
                job_description=job.description,
                job_requirements=job.requirements
            )
            job.resume_match_score = analysis.overall_match_score
            job.match_reasons = analysis.matching_skills
            job_db.update_job(job)
        
        return jsonify(job.dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/save', methods=['POST'])
def save_job(job_id):
    """Save a job for later"""
    try:
        job = job_db.get_job_by_id(job_id)
        if job:
            job.status = 'saved'
            job_db.update_job(job)
            return jsonify({'success': True, 'message': 'Job saved'})
        return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/apply', methods=['POST'])
def mark_applied(job_id):
    """Mark job as applied"""
    try:
        job = job_db.get_job_by_id(job_id)
        if job:
            job.status = 'applied'
            job.applied_date = datetime.now()
            job_db.update_job(job)
            return jsonify({'success': True, 'message': 'Marked as applied'})
        return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/sheets', methods=['POST'])
def export_to_sheets():
    """Export jobs to Google Sheets"""
    try:
        data = request.json
        job_ids = data.get('job_ids', [])
        
        if not job_ids:
            # Export all recent jobs
            jobs = job_db.get_recent_jobs(limit=100)
        else:
            jobs = [job_db.get_job_by_id(jid) for jid in job_ids]
        
        # Sync to sheets
        success_count = 0
        for job in jobs:
            if job and sheets_service.append_job(job):
                success_count += 1
        
        sheets_url = f"https://docs.google.com/spreadsheets/d/{sheets_service.sheets_id}"
        
        return jsonify({
            'success': True,
            'sheetsUrl': sheets_url,
            'jobsExported': success_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sheets/data', methods=['GET'])
def get_sheets_data():
    """Get current data from Google Sheets"""
    try:
        data = sheets_service.get_all_data()
        return jsonify({
            'success': True,
            'data': data,
            'rowCount': len(data) if data else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/profile/resume', methods=['POST'])
def upload_resume():
    """Upload and analyze resume"""
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        
        # Save file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file.save(tmp.name)
            
            # Extract text and analyze
            resume_text = resume_matcher.extract_text_from_pdf(tmp.name)
            skills = resume_matcher.extract_skills(resume_text)
            
            # Update resume profile
            resume_matcher.update_profile(resume_text=resume_text)
            
            os.unlink(tmp.name)  # Delete temp file
        
        return jsonify({
            'success': True,
            'analysis': {
                'skills': skills,
                'textLength': len(resume_text),
                'matchingKeywords': skills[:10]
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_recent_activity():
    """Get recent activity for dashboard"""
    activities = []
    
    # Get recent high-match jobs
    recent_jobs = job_db.get_recent_jobs(limit=10)
    for job in recent_jobs:
        if job.resume_match_score and job.resume_match_score > 85:
            activities.append({
                'type': 'success',
                'title': f'{job.title} at {job.company}',
                'description': f'{job.resume_match_score}% match',
                'time': format_time_ago(job.scraped_at)
            })
    
    # Add sheets sync activity (mock)
    activities.append({
        'type': 'info',
        'title': 'Synced to Google Sheets',
        'description': f'{len(recent_jobs)} jobs synced',
        'time': '5 hours ago'
    })
    
    return activities[:5]  # Return top 5

def format_time_ago(dt):
    """Format datetime as 'X hours/days ago'"""
    if not dt:
        return 'recently'
    
    delta = datetime.now() - dt
    if delta.days > 0:
        return f'{delta.days} day{"s" if delta.days > 1 else ""} ago'
    
    hours = delta.seconds // 3600
    if hours > 0:
        return f'{hours} hour{"s" if hours > 1 else ""} ago'
    
    minutes = delta.seconds // 60
    return f'{minutes} minute{"s" if minutes > 1 else ""} ago'

if __name__ == '__main__':
    print("Starting Job Automator API Server...")
    print("Dashboard available at: http://localhost:5000")
    print("\nMake sure to:")
    print("1. Set up your Google Sheets credentials")
    print("2. Configure your OpenAI/Groq API keys in config.py")
    print("3. Have Chrome/Chromium installed for web scraping")
    
    app.run(debug=True, port=5000)