# 🚀 Quick Start Guide

Get the LinkedIn Job Automation running in **one command** - no prior setup needed!

## ⚡ Instant Setup

### For Mac/Linux Users:
```bash
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
chmod +x setup.sh
./setup.sh
```

### For Windows Users:
```cmd
git clone https://github.com/kpadidam/linkedinautomation.git
cd linkedinautomation
setup.bat
```

## 🛠️ What the Setup Script Does

The setup script automatically installs:
- ✅ **Python 3.8+** (if not installed)
- ✅ **pip/pip3** (package manager)
- ✅ **Node.js & npm** (for browser dependencies)
- ✅ **All Python packages** from requirements.txt
- ✅ **Playwright** (browser automation)
- ✅ **Chromium browser** (for scraping)
- ✅ **Virtual environment** (isolated Python setup)
- ✅ **Configuration templates** (.env, credentials.json)

## ⚙️ Configuration (3 steps)

After setup completes, configure these 3 files:

### 1. Edit `.env` file:
```env
OPENAI_API_KEY=your_openai_key_here
GROQ_API_KEY=your_groq_key_here  
GOOGLE_SHEETS_ID=your_sheet_id_here
```

### 2. Replace `config/credentials.json`:
- Follow [config/README.md](config/README.md) to get Google Cloud credentials
- Replace the template file with your actual credentials

### 3. Add your resume:
- Place your resume as `resumes/resume.pdf`

## 🏃‍♂️ Run the Project

```bash
# Activate the environment
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate.bat  # Windows

# Run the job search
python linkedin.py
```

## 📊 What Happens

The script will:
1. **Search LinkedIn** for all job categories in your config
2. **Extract job details** (title, company, description, etc.)
3. **Match against your resume** using AI (Groq for speed)
4. **Log everything** to Google Sheets with match scores
5. **Show top matches** in the terminal

## ⚡ Current Speed

- **5 job categories** × **7 keywords each** = **35 searches**
- **Up to 50 jobs per keyword** = **potentially 1,750 jobs**
- **Total runtime**: **~1 hour** (using Groq for fast AI matching)

## 🔧 Customize Your Search

Edit these files to match your preferences:
- **`config/job_preferences.json`** - Job titles, locations, skills to search for
- **`config/user_profile.json`** - Your profile information
- **`.env`** - API keys and settings

## 🆘 Need Help?

1. **Setup Issues**: The script shows detailed error messages
2. **Configuration**: See [config/README.md](config/README.md)
3. **Troubleshooting**: Check the main [README.md](README.md)

## 🎯 Pro Tips

- **Test first**: Run with smaller `max_results` (like 10) to test the setup
- **API Keys**: Get free Groq API key for faster processing
- **Scheduling**: Set up cron/scheduled tasks to run automatically
- **Filtering**: Adjust `min_match_threshold` to filter by match quality

---

**Ready to automate your job search?** Just run the setup script and you'll be finding jobs in minutes! 🚀