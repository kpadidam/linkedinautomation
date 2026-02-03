# 🚀 LinkedIn Job Automation System

An intelligent job search automation tool that scrapes LinkedIn jobs, matches them with your resume using AI, and logs everything to Google Sheets automatically.

**Instead of spending hours manually browsing LinkedIn, this tool finds 1000+ relevant jobs in ~1 hour and gives each a match score based on your resume.**

---

## 📋 Choose Your Setup Path

### 👶 **Complete Beginner** (Never used command line? Start here!)

<details>
<summary><strong>Click here if you've never used programming tools before</strong></summary>

### What This Tool Does (In Simple Terms)
Think of it as having a robot assistant that:
1. **Automatically searches LinkedIn** for jobs matching your criteria
2. **Reads your resume** and compares it to each job posting  
3. **Gives each job a match score** (like "85% match")
4. **Saves everything to a Google Spreadsheet** you can review later

### What You Need First: Install Git

**What is Git?** It's a tool that lets you download code from the internet.

**Mac:**
1. Open Terminal (press `Cmd + Space`, type "terminal", press Enter)
2. Type: `git --version` and press Enter
3. If you see a version number, you're good! If not, it will prompt you to install.

**Windows:**
1. Go to [git-scm.com](https://git-scm.com/download/win)
2. Download and install Git for Windows (use all default settings)

### Step-by-Step Setup

**1. Download the Code**

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

The setup script installs Python, all software, and creates templates automatically (5-15 minutes).

**2. Get API Keys (Think of these as passwords for AI services)**

**OpenAI (Required)** - Costs ~$5-20/month
1. Go to [platform.openai.com](https://platform.openai.com), sign up
2. Go to [API Keys](https://platform.openai.com/api-keys)
3. Create new secret key, copy it (starts with "sk-proj-...")

**Groq (Recommended)** - FREE and 10x faster!
1. Go to [console.groq.com](https://console.groq.com), sign up
2. Go to [Keys](https://console.groq.com/keys) 
3. Create API Key, copy it (starts with "gsk_...")

**3. Set Up Google Sheets**

Create a Google Sheet:
1. Go to [sheets.google.com](https://sheets.google.com)
2. Create blank spreadsheet, name it "LinkedIn Jobs"
3. Copy the ID from URL: `https://docs.google.com/spreadsheets/d/[COPY_THIS_PART]/edit`

Get Google Cloud credentials:
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create new project, name it "LinkedInJobs"
3. Enable Google Sheets API:
   - Menu → "APIs & Services" → "Library" 
   - Search "Google Sheets API" → Enable
4. Create service account:
   - Menu → "APIs & Services" → "Credentials"
   - "Create Credentials" → "Service account"
   - Name: "linkedinbot" → Create
5. Download credentials:
   - Click on "linkedinbot" → "Keys" tab
   - "Add Key" → "Create new key" → JSON → Create
   - File downloads automatically

**4. Configure Your Files**

Edit the `.env` file:
- **Mac:** `open .env`
- **Windows:** `notepad .env`

Replace these lines:
```env
OPENAI_API_KEY=your_sk-proj_key_here
GROQ_API_KEY=your_gsk_key_here  
GOOGLE_SHEETS_ID=your_sheet_id_here
```

Replace `config/credentials.json`:
- Copy your downloaded Google credentials file into the `config/` folder
- Rename it to exactly `credentials.json`

Share your Google Sheet:
1. Open the credentials.json file, find the "client_email"
2. In your Google Sheet, click "Share"
3. Add that email address with "Editor" permission

Add your resume:
- Save your resume as `resumes/resume.pdf`

**5. Run It!**

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

The tool will find 1000+ jobs across all categories in about 1 hour!

</details>

### 🚀 **Quick Start** (For users with technical experience)

<details>
<summary><strong>One-command setup for experienced users</strong></summary>

**Prerequisites:** Git installed

**1. Automated Setup**
```bash
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
./setup.sh  # Linux/Mac
# OR
setup.bat   # Windows
```

**2. Configure (3 files)**
- `.env` - Add OpenAI/Groq API keys + Google Sheet ID
- `config/credentials.json` - Replace with Google Cloud service account JSON
- `resumes/resume.pdf` - Add your resume

**3. Run**
```bash
source venv/bin/activate && python linkedin.py
```

See [config/README.md](config/README.md) for detailed credential setup.

</details>

### 🔧 **Manual Installation** (Traditional method)

<details>
<summary><strong>Step-by-step manual setup</strong></summary>

**Prerequisites:**
- Python 3.8+
- Google Cloud account
- OpenAI API key

**1. Clone and Install**
```bash
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
pip install -r requirements.txt
playwright install chromium
```

**2. Configuration Files**

Copy environment template:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here  
GOOGLE_SHEETS_ID=your_google_sheet_id_here
```

**Google Sheets Setup:**
1. Create Google Cloud project
2. Enable Google Sheets API
3. Create service account, download JSON credentials
4. Replace `config/credentials.json` with your credentials
5. Create Google Sheet, share with service account email

**Resume Setup:**
- Place resume as `resumes/resume.pdf`

**3. Customize Job Search**
Edit these files to match your preferences:
- `config/job_preferences.json` - Job categories, keywords, locations
- `config/user_profile.json` - Your profile information

**4. Run**
```bash
python linkedin.py
```

</details>

---

## 🎯 What Happens When You Run It

1. **Searches LinkedIn** for all configured job categories (5 categories × 7 keywords = 35 searches)
2. **Extracts job details** - title, company, description, salary, location
3. **AI analysis** - Matches each job against your resume using Groq/OpenAI
4. **Auto-logs to Google Sheets** with these columns:

```
Job ID | Date | Time | Role | Company | Location | Job Type | Level | 
Link | Job Responsibilities | Preferred Skills | Matching Skills | 
Role Match % | Salary | Posted | Number of Applicants
```

5. **Shows top matches** in terminal and Google Sheets

**Expected Results:** 500-1500 jobs found, processed in ~1 hour with AI match scores.

## 📊 What Your Google Sheet Will Look Like

The system automatically creates formatted headers and example data:
```
123456 | 2026-02-03 | 14:30:25 | Data Analyst | TechCorp | San Francisco, CA |
Full-time | Mid-level | https://linkedin.com/jobs/123456 | • Analyze data trends... |
Python, SQL, Tableau | Python, SQL | 85% | $80,000-$100,000 | 2 days ago | 15 applicants
```

## 🛠️ Customization

**Job Categories** (`config/job_preferences.json`):
Currently searches for: Data Analyst, Data Engineer, BI Developer, Data Scientist, GIS Analyst

**Add your own categories:**
```json
{
  "category": "Your Target Role",
  "keywords": ["keyword1", "keyword2"],
  "skills": ["skill1", "skill2"], 
  "location": "United States",
  "max_results": 50
}
```

**Your Profile** (`config/user_profile.json`):
Update with your skills, experience, and preferences for better AI matching.

## 💰 Cost Breakdown

- **Groq:** FREE (recommended for speed)
- **OpenAI:** ~$5-20/month (backup/higher quality)
- **Google Cloud:** FREE for normal usage
- **Your time:** 30 minutes setup vs hours of manual searching

## 🆘 Troubleshooting

**Common Issues:**

| Error | Solution |
|-------|----------|
| "Command not found" | Install Git, make sure you're in the right folder |
| "Permission denied" | Share Google Sheet with service account email |
| "API key invalid" | Double-check you copied the full API key |
| "No module named..." | Run setup script again or `pip install -r requirements.txt` |

## 🚀 Features

- **Automated LinkedIn Scraping** - No manual browsing needed
- **AI-Powered Resume Matching** - Uses OpenAI/Groq for smart job scoring
- **Google Sheets Integration** - All data automatically organized
- **Customizable Search** - Configure job types, locations, skills
- **Duplicate Prevention** - Won't add the same job twice
- **Speed Optimized** - Uses Groq for 5-10x faster AI analysis
- **Cross-Platform** - Works on Mac, Windows, Linux

## 📁 Project Structure

```
linkedin-job-automation/
├── config/
│   ├── README.md               # Detailed Google Cloud setup
│   ├── credentials.json        # Google service account (you add this)
│   ├── job_preferences.json    # Job search criteria
│   └── user_profile.json       # Your skills and profile
├── resumes/
│   └── resume.pdf             # Your resume (you add this)
├── scrapers/
│   └── linkedin_scraper_playwright.py  # Main scraper
├── services/
│   ├── google_sheets_service.py        # Sheets integration  
│   └── resume_matcher.py               # AI job matching
├── setup.sh / setup.bat       # Automated setup scripts
├── linkedin.py                # Main script to run
└── .env                       # Your API keys (you configure this)
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## ⚠️ Important Notes

- **Respect LinkedIn's Terms of Service** - This tool is for educational purposes
- **Rate limiting** - LinkedIn may slow down requests if used excessively
- **Keep credentials secure** - Never share your API keys or credentials
- **Resume privacy** - Your resume stays local, only job descriptions are sent to AI

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Ready to automate your job search?** Choose your setup path above and get started! 🚀