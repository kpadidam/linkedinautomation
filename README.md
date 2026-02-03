# LinkedIn Job Automation System

An intelligent job search automation tool that scrapes LinkedIn jobs, matches them with your resume using AI, and logs everything to Google Sheets automatically.

Instead of spending hours manually browsing LinkedIn, this tool finds over 1000 relevant jobs in approximately one hour and provides each with a match score based on your resume.

---

## Getting Started

Choose the setup path that matches your experience level:

### For Complete Beginners

<details>
<summary><strong>New to programming tools? Start here for detailed guidance</strong></summary>

### What This Tool Does

This automation system acts like a personal job search assistant that:
1. Automatically searches LinkedIn for jobs matching your criteria
2. Analyzes your resume against each job posting using AI
3. Assigns a compatibility score to each opportunity
4. Saves all results to a Google Spreadsheet for easy review

### Prerequisites: Installing Git

Git is a tool that allows you to download code from repositories like GitHub.

**For Mac users:**
1. Open Terminal (press Cmd + Space, type "terminal", press Enter)
2. Type: `git --version` and press Enter
3. If you see a version number, you're ready. If not, macOS will prompt you to install it.

**For Windows users:**
1. Visit [git-scm.com](https://git-scm.com/download/win)
2. Download and install Git for Windows using all default settings

### Setup Process

**Step 1: Download and Install**

**Mac/Linux:**
```bash
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
./setup.sh
```

**Windows:**
```cmd
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
setup.bat
```

The setup script will automatically install Python, all required packages, and create configuration templates. This process takes 5-15 minutes.

**Step 2: Obtain API Keys**

API keys are authentication tokens that allow this tool to communicate with AI services.

**OpenAI (Required)** - Estimated cost: $5-20/month
1. Create an account at [platform.openai.com](https://platform.openai.com)
2. Navigate to [API Keys](https://platform.openai.com/api-keys)
3. Create a new secret key and copy it (begins with "sk-proj-...")

**Groq (Recommended)** - Free tier available, significantly faster processing
1. Create an account at [console.groq.com](https://console.groq.com)
2. Go to [Keys](https://console.groq.com/keys)
3. Create an API Key and copy it (begins with "gsk_...")

**Step 3: Configure Google Sheets Integration**

Create your results spreadsheet:
1. Go to [sheets.google.com](https://sheets.google.com)
2. Create a new blank spreadsheet and name it "LinkedIn Jobs"
3. Copy the spreadsheet ID from the URL: `https://docs.google.com/spreadsheets/d/[COPY_THIS_PART]/edit`

Set up Google Cloud credentials:
1. Visit [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project and name it "LinkedInJobs"
3. Enable the Google Sheets API:
   - Navigate to "APIs & Services" then "Library"
   - Search for "Google Sheets API" and enable it
4. Create a service account:
   - Go to "APIs & Services" then "Credentials"
   - Click "Create Credentials" and select "Service account"
   - Name it "linkedinbot" and create it
5. Download the credentials file:
   - Click on your new service account
   - Go to the "Keys" tab
   - Click "Add Key" then "Create new key", select JSON format
   - The file will download automatically

**Step 4: Configure Your Settings**

Edit your environment file:
- **Mac:** Run `open .env` in Terminal
- **Windows:** Run `notepad .env` in Command Prompt

Replace the placeholder values:
```env
OPENAI_API_KEY=your_sk-proj_key_here
GROQ_API_KEY=your_gsk_key_here  
GOOGLE_SHEETS_ID=your_sheet_id_here
```

Replace the credentials file:
- Copy your downloaded Google credentials file into the `config/` folder
- Rename it to exactly `credentials.json`

Share your spreadsheet:
1. Open your credentials.json file and find the "client_email" address
2. In your Google Sheet, click "Share"
3. Add that email address with "Editor" permissions

Add your resume:
- Save your resume as `resumes/resume.pdf`

**Step 5: Run the Application**

**Mac/Linux:**
```bash
source venv/bin/activate
python linkedin.py
```

**Windows:**  
```cmd
venv\Scripts\activate.bat
python linkedin.py
```

The tool will analyze multiple job categories and typically finds 1000+ positions in about one hour.

</details>

### Quick Setup for Experienced Users

<details>
<summary><strong>Automated installation for users familiar with development tools</strong></summary>

**Requirements:** Git must be installed

**1. Automated Installation**
```bash
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
./setup.sh  # Linux/Mac
# OR
setup.bat   # Windows
```

**2. Configuration**
Configure these three items:
- `.env` - Add your OpenAI/Groq API keys and Google Sheet ID
- `config/credentials.json` - Replace with your Google Cloud service account JSON
- `resumes/resume.pdf` - Add your resume file

**3. Execution**
```bash
source venv/bin/activate && python linkedin.py
```

For detailed credential setup instructions, see [config/README.md](config/README.md).

</details>

### Manual Installation

<details>
<summary><strong>Traditional step-by-step installation process</strong></summary>

**System Requirements:**
- Python 3.8 or higher
- Google Cloud account
- OpenAI API access

**1. Clone and Install Dependencies**
```bash
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
pip install -r requirements.txt
playwright install chromium
```

**2. Environment Configuration**

Create your environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here  
GOOGLE_SHEETS_ID=your_google_sheet_id_here
```

**Google Sheets Integration:**
1. Create a new Google Cloud project
2. Enable the Google Sheets API
3. Create a service account and download the JSON credentials
4. Replace `config/credentials.json` with your credentials file
5. Create a Google Sheet and share it with the service account email address

**Resume Configuration:**
- Place your resume file at `resumes/resume.pdf`

**3. Customize Search Parameters**
Modify these configuration files according to your preferences:
- `config/job_preferences.json` - Define job categories, keywords, and locations
- `config/user_profile.json` - Update your profile information

**4. Execute the Application**
```bash
python linkedin.py
```

</details>

---

## How It Works

When you run the application, it performs the following operations:

1. **LinkedIn Search**: Conducts searches across configured job categories (currently 5 categories with 7 keywords each, totaling 35 searches)
2. **Data Extraction**: Collects job details including title, company, description, salary, and location
3. **AI Analysis**: Compares each job posting against your resume using Groq or OpenAI
4. **Data Logging**: Automatically saves results to Google Sheets with organized columns

### Google Sheets Output Format

The system creates the following column structure automatically:

```
Job ID | Date | Time | Role | Company | Location | Job Type | Level | 
Link | Job Responsibilities | Preferred Skills | Matching Skills | 
Role Match % | Salary | Posted | Number of Applicants
```

### Sample Output

Your spreadsheet will contain entries like:
```
123456 | 2026-02-03 | 14:30:25 | Data Analyst | TechCorp | San Francisco, CA |
Full-time | Mid-level | https://linkedin.com/jobs/123456 | Analyze data trends |
Python, SQL, Tableau | Python, SQL | 85% | $80,000-$100,000 | 2 days ago | 15 applicants
```

**Expected Results:** 500-1500 job listings processed in approximately one hour with AI-generated compatibility scores.

## Customization

### Job Search Configuration

The system currently searches for these role categories:
- Data Analyst
- Data Engineer  
- Business Intelligence Developer
- Data Scientist (Entry-Level)
- GIS Data Analyst

To add custom categories, edit `config/job_preferences.json`:
```json
{
  "category": "Your Target Role",
  "keywords": ["keyword1", "keyword2"],
  "skills": ["skill1", "skill2"], 
  "location": "United States",
  "max_results": 50
}
```

### Profile Configuration

Update `config/user_profile.json` with your skills, experience level, and preferences to improve AI matching accuracy.

## Cost Information

- **Groq**: Free tier available (recommended for speed)
- **OpenAI**: Approximately $5-20 per month (provides backup and alternative analysis)
- **Google Cloud**: Free for standard usage levels
- **Time Investment**: 30 minutes initial setup versus hours of manual job searching

## Troubleshooting

Common issues and solutions:

| Issue | Resolution |
|-------|------------|
| "Command not found" | Verify Git installation and confirm you're in the correct directory |
| "Permission denied" | Ensure Google Sheet is shared with the service account email |
| "API key invalid" | Verify the complete API key was copied correctly |
| "No module named..." | Re-run the setup script or execute `pip install -r requirements.txt` |

## Features

- **Automated LinkedIn Scraping**: Eliminates manual job browsing
- **AI-Powered Resume Matching**: Uses advanced language models for intelligent job scoring  
- **Google Sheets Integration**: Automatically organizes all data
- **Customizable Search Parameters**: Configure job types, locations, and skill requirements
- **Duplicate Prevention**: Avoids adding the same position multiple times
- **Performance Optimization**: Uses Groq for significantly faster AI analysis
- **Cross-Platform Compatibility**: Supports Mac, Windows, and Linux systems

## Project Architecture

```
linkedin-job-automation/
├── config/
│   ├── README.md               # Detailed Google Cloud setup instructions
│   ├── credentials.json        # Google service account credentials (user-provided)
│   ├── job_preferences.json    # Job search criteria configuration
│   └── user_profile.json       # User skills and profile information
├── resumes/
│   └── resume.pdf             # User resume file (user-provided)
├── scrapers/
│   └── linkedin_scraper_playwright.py  # Primary web scraping module
├── services/
│   ├── google_sheets_service.py        # Google Sheets integration service
│   └── resume_matcher.py               # AI-powered job matching service
├── setup.sh / setup.bat       # Automated setup scripts
├── linkedin.py                # Main application entry point
└── .env                       # Environment variables (user-configured)
```

## Contributing

We welcome contributions to improve this project:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/NewFeature`)
3. Commit your changes (`git commit -m 'Add NewFeature'`)
4. Push to the branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

## Important Considerations

- **LinkedIn Terms of Service**: This tool is designed for educational purposes. Please respect LinkedIn's terms of service and use the tool responsibly.
- **Rate Limiting**: LinkedIn may implement rate limiting if the tool is used excessively. The application includes built-in delays to minimize this risk.
- **Data Security**: Keep your API keys and credentials secure. Never share these in public repositories or communications.
- **Privacy**: Your resume data remains local to your system. Only job descriptions are sent to AI services for analysis.

## License

This project is licensed under the MIT License. You are free to use, modify, and distribute this software in accordance with the license terms. See the LICENSE file for complete details.

---

Ready to automate your job search? Choose your preferred setup method above and get started.