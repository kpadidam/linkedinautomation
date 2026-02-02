# LinkedIn Job Automation System

An intelligent job search automation tool that scrapes LinkedIn jobs, matches them with your resume, and logs everything to Google Sheets.

 🚀 Features

- Automated LinkedIn Job Scraping: Search for jobs based on your preferences without manual browsing
- AI-Powered Resume Matching: Uses OpenAI/Groq to match job descriptions with your resume
- Google Sheets Integration: Automatically logs all jobs with match scores to a spreadsheet
- Customizable Search Criteria: Configure job titles, locations, skills, and more
- Web Dashboard: FastAPI-based interface for monitoring and managing searches
- Database Storage: SQLite database for local job tracking

 📋 Prerequisites

- Python 3.8 or higher
- Google Cloud account (for Sheets API)
- OpenAI API key (for resume matching)
- Chrome/Chromium browser

 🛠️ Installation

# Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/linkedin-job-automation.git
cd linkedin-job-automation
```

# Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

# Step 3: Install Playwright Browsers

```bash
playwright install chromium
```

# Step 4: Set Up Configuration

 4.1 Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your credentials:
```env
# Required
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_SHEETS_ID=your_google_sheet_id_here

# Optional (for faster processing)
GROQ_API_KEY=your_groq_api_key_here
```

 4.2 Google Sheets Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create credentials (Service Account)
5. Download the credentials JSON file
6. Replace the contents of `config/credentials.json` with your service account credentials

 4.3 User Profile Configuration

Edit `config/user_profile.json` with your information:

```json
{
  "name": "Your Name",
  "email": "your.email@example.com",
  "phone": "(555) 123-4567",
  "title": "Your Job Title",
  "years_of_experience": 5,
  "resume_file": "resume.pdf",
  ...
}
```

 4.4 Job Preferences

Edit `config/job_preferences.json` to set your job search criteria:

```json
{
  "job_categories": [
    {
      "category": "Your Target Role",
      "keywords": ["keyword1", "keyword2"],
      "skills": ["skill1", "skill2"],
      "location": "United States",
      "remote_ok": true,
      "job_type": ["full-time"],
      "experience_level": "mid-senior",
      "posted_within": "week",
      "max_results": 50
    }
  ]
}
```

 4.5 Add Your Resume

1. Place your resume PDF in the `resumes` folder
2. Name it exactly: `resume.pdf`

 🎯 Usage

# Quick Start

Run the LinkedIn scraper directly:

```bash
python linkedin.py
```

The scraper will:
1. Load your profile and job preferences from `config/`
2. Search LinkedIn for matching jobs using Playwright
3. Match each job against your resume using AI
4. Log all results to your Google Sheet with match scores

 📁 Project Structure

```
linkedin-job-automation/
├── config/
│   ├── credentials.json         # Google Sheets service account
│   ├── job_preferences.json     # Job search criteria
│   └── user_profile.json        # Your profile and skills
├── resumes/
│   └── resume.pdf               # Your resume
├── scrapers/
│   ├── __init__.py
│   ├── linkedin_scraper_playwright.py  # Main Playwright scraper
│   └── linkedin_scraper_v2.py          # Alternative scraper implementation
├── services/
│   ├── google_sheets_service.py # Google Sheets integration
│   └── resume_matcher.py        # AI-powered job matching
├── models/
│   └── job_model.py             # Job data models
├── app/
│   └── main.py                  # FastAPI web dashboard
├── linkedin.py                  # Main entry point script
├── config.py                    # Configuration management
├── .env                         # Your environment variables
├── .gitignore                   # Git ignore rules
└── requirements.txt             # Python dependencies
```

 🔧 Configuration Guide

# Customizing Job Search

The `config/job_preferences.json` file controls what jobs are searched for:

- category: Name for this search type
- keywords: Job titles to search for
- skills: Required skills to match
- location: Geographic location
- remote_ok: Whether to include remote jobs
- job_type: full-time, part-time, contract, etc.
- experience_level: entry, mid-senior, senior, etc.
- posted_within: 24h, week, month
- max_results: Maximum jobs to scrape per search

# Adjusting Match Scoring

Edit the `min_match_threshold` in `job_preferences.json` to filter jobs by match score (0-100).

 🐛 Troubleshooting

# Common Issues

1. Google Sheets Authentication Error
   - Ensure config/credentials.json has your service account details
   - Check that the service account has edit access to your sheet

2. No Jobs Found
   - Try broader keywords
   - Increase `max_results`
   - Check if LinkedIn's layout has changed

3. Resume Matching Not Working
   - Verify OpenAI API key is valid
   - Ensure resume.pdf exists in resumes folder

# Debug Mode

Enable debug mode in `.env`:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

 📊 Google Sheets Setup

1. Create a new Google Sheet
2. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[SHEET_ID_HERE]/edit
   ```
3. Add the Sheet ID to your `.env` file
4. Share the sheet with the service account email from config/credentials.json

 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

 ⚠️ Disclaimer

This tool is for educational purposes. Please respect LinkedIn's Terms of Service and use responsibly. Consider using LinkedIn's official API for production applications.

 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions

 🔄 Updates

To update to the latest version:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

Note: Always ensure you're complying with LinkedIn's terms of service and robots.txt when using this tool.
