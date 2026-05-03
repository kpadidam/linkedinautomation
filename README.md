# LinkedIn Job Automation System

An AI-powered LinkedIn job scraper that automatically discovers relevant jobs, analyzes them with resume matching, and logs everything to Google Sheets in real-time.

## Features

- **AI-Powered Browser Automation**: Uses Browser-Use with GPT-4 to intelligently navigate LinkedIn
- **Smart Job Matching**: AI analyzes job descriptions and matches them against your resume/skills
- **Real-time Google Sheets Integration**: Automatically logs all jobs with comprehensive metadata
- **SQLite Database**: Local tracking with deduplication to avoid processing the same jobs
- **Web Interface**: Clean, modern UI for managing searches and viewing results
- **FastAPI Backend**: RESTful API for all operations
- **Resume Analysis**: Upload your resume for intelligent job matching
- **Batch Processing**: Efficiently process multiple jobs with rate limiting

## Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy
- **Browser Automation**: Browser-Use, Playwright
- **AI/LLM**: OpenAI GPT-4, Groq (optional)
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **External Services**: Google Sheets API

## Installation

### 1. Clone the repository
```bash
cd /Users/karthikpadidam/Desktop/project/linkedinautomation
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium  # Install browser for automation
```

### 4. Set up environment variables
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- `OPENAI_API_KEY`: Required for Browser-Use AI agent
- `GROQ_API_KEY`: Optional for faster LLM inference
- `GOOGLE_SHEETS_CREDENTIALS_PATH`: Path to Google Sheets credentials JSON
- `GOOGLE_SHEETS_ID`: Your target Google Sheet ID

### 5. Set up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Create credentials (Service Account or OAuth2)
5. Download credentials JSON and save to project directory
6. Update `GOOGLE_SHEETS_CREDENTIALS_PATH` in `.env`

### 6. Initialize the database
```bash
python database/models.py
```

## Usage

### Start the application
```bash
python app/main.py
```

Or use uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access the web interface
Open your browser and navigate to:
```
http://localhost:8000
```

### Using the Web Interface

1. **Job Search Tab**: 
   - Enter keywords (e.g., "Software Engineer")
   - Specify location
   - Set filters (job type, experience level, etc.)
   - Enable/disable AI matching and Google Sheets logging
   - Click "Start Search"

2. **Saved Jobs Tab**:
   - View all scraped jobs
   - Filter by status or match score
   - Click on jobs to see full details
   - Mark jobs as applied or saved

3. **Profile Tab**:
   - Add your resume text for better matching
   - Set your skills
   - Configure preferences

4. **Statistics Tab**:
   - View overall statistics
   - See recent searches
   - Create new Google Sheets
   - Clean up old data

### API Endpoints

The application provides a RESTful API:

- `POST /api/search` - Start a new job search
- `GET /api/search/{search_id}` - Get search status
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{job_id}` - Get specific job details
- `PUT /api/jobs/{job_id}` - Update job status
- `GET /api/profile` - Get user profile
- `PUT /api/profile` - Update user profile
- `GET /api/statistics` - Get system statistics
- `POST /api/sheets/create` - Create new Google Sheet
- `POST /api/cleanup` - Clean up old data

Full API documentation available at: `http://localhost:8000/docs`

## Configuration

Key settings in `config.py`:

- `DEFAULT_LOCATION`: Default search location
- `MAX_RESULTS_PER_SEARCH`: Maximum jobs per search
- `SEARCH_DELAY_SECONDS`: Delay between job scrapes
- `BROWSER_HEADLESS`: Run browser in headless mode

## Google Sheets Format

The system automatically creates a spreadsheet with these columns:

| Column | Description |
|--------|-------------|
| Date | Date job was scraped |
| Time | Time job was scraped |
| Job Title | Position title |
| Company | Company name |
| Location | Job location |
| Job Type | Full-time, Part-time, etc. |
| Experience Level | Entry, Senior, etc. |
| Description Summary | Brief job description |
| Keywords | Extracted keywords |
| Required Skills | Skills required |
| Resume Match % | AI-calculated match score |
| Salary Range | If provided |
| Posted Date | When job was posted |
| Applicants | Number of applicants |
| Job URL | Direct link to job |
| Status | New, Viewed, Applied, etc. |
| Notes | Your notes |

## Troubleshooting

### Browser automation not working
- Ensure Playwright browsers are installed: `playwright install chromium`
- Try running with `BROWSER_HEADLESS=False` to see what's happening

### Google Sheets not updating
- Verify credentials are correctly configured
- Check that the Google Sheets API is enabled
- Ensure the service account has edit access to the sheet

### OpenAI API errors
- Verify your API key is valid
- Check your OpenAI account has sufficient credits
- Consider using Groq as a fallback

### Database issues
- Delete `linkedin_jobs.db` and reinitialize: `python database/models.py`

## Advanced Usage

### Running searches programmatically
```python
from scrapers.linkedin_scraper import LinkedInScraper, JobSearchParams

scraper = LinkedInScraper()
params = JobSearchParams(
    keywords="Python Developer",
    location="Remote",
    max_results=50
)
jobs = await scraper.search_jobs(params)
```

### Scheduling automated searches
You can set up a cron job or use the built-in scheduler (coming soon) to run searches automatically.

## Security Notes

- Never commit your `.env` file with real API keys
- Keep your Google Sheets credentials secure
- Be mindful of LinkedIn's terms of service
- Use rate limiting to avoid being detected as a bot

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - see LICENSE file for details

## Disclaimer

This tool is for educational and personal use. Respect LinkedIn's terms of service and use responsibly. The authors are not responsible for any misuse of this software.