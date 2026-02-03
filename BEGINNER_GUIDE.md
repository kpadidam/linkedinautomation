# 👶 Complete Beginner's Guide to LinkedIn Job Automation

**Never used the command line? No coding experience? No problem!** This guide assumes you know absolutely nothing about programming and walks you through everything step by step.

## 🤔 What This Tool Does (In Simple Terms)

Instead of manually browsing LinkedIn for jobs for hours, this tool:
1. **Automatically searches LinkedIn** for jobs that match your criteria
2. **Reads your resume** and compares it to each job posting  
3. **Gives each job a match score** (like "85% match")
4. **Saves everything to a Google Spreadsheet** you can review later

Think of it as having a robot assistant that does your job hunting for you 24/7!

## 📋 What You Need Before Starting

### Step 0: Install Git (Required)

**What is Git?** It's a tool that lets you download code from the internet.

**Mac:**
1. Open Terminal (press `Cmd + Space`, type "terminal", press Enter)
2. Type: `git --version` and press Enter
3. If you see a version number, you're good! If not, it will prompt you to install.

**Windows:**
1. Go to [git-scm.com](https://git-scm.com/download/win)
2. Download and install Git for Windows
3. Use all default settings during installation

**How do I know it worked?** Open Terminal/Command Prompt and type `git --version`. You should see something like "git version 2.39.1".

## 🔧 Step-by-Step Setup

### Step 1: Download the Code

**Mac/Linux:**
1. Open Terminal (Applications → Utilities → Terminal)
2. Copy and paste this EXACTLY, then press Enter:
   ```bash
   git clone https://github.com/kpadidam/linkedinautomation.git
   ```
3. Then type: `cd linkedinautomation`
4. Then type: `./setup.sh`

**Windows:**
1. Press `Windows Key + R`, type `cmd`, press Enter
2. Copy and paste this EXACTLY, then press Enter:
   ```cmd
   git clone https://github.com/kpadidam/linkedinautomation.git
   ```
3. Then type: `cd linkedinautomation`  
4. Then type: `setup.bat`

**What's happening?** The setup script is installing Python, all the required software, and setting up everything automatically. This takes 5-15 minutes.

### Step 2: Get Your API Keys (Don't Panic!)

**What are API keys?** Think of them as passwords that let this tool talk to AI services that will read your resume and match it to jobs.

#### 2A. OpenAI Account (REQUIRED)
**What it does:** Reads your resume and job descriptions to calculate match scores
**Cost:** About $5-20/month depending on usage

1. Go to [platform.openai.com](https://platform.openai.com)
2. Click "Sign Up" and create an account
3. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy the key (starts with "sk-proj-...")
6. **IMPORTANT:** Save it somewhere safe - you can't see it again!

#### 2B. Groq Account (RECOMMENDED - Makes it 10x faster!)
**What it does:** Same as OpenAI but much faster
**Cost:** FREE for moderate usage!

1. Go to [console.groq.com](https://console.groq.com)
2. Click "Sign Up" and create an account  
3. Go to [console.groq.com/keys](https://console.groq.com/keys)
4. Click "Create API Key"
5. Copy the key (starts with "gsk_...")

### Step 3: Set Up Google Sheets (Where Your Job Results Go)

#### 3A. Create a Google Sheet
1. Go to [sheets.google.com](https://sheets.google.com)
2. Click "Create a blank spreadsheet"
3. Name it "LinkedIn Jobs" or whatever you want
4. Copy the ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[THIS_LONG_STRING_IS_THE_ID]/edit
   ```

#### 3B. Get Google Cloud Credentials (This is the tricky part!)

**Why do I need this?** So the tool can automatically write job data to your Google Sheet.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Sign in with your Google account
3. Click "Create Project" (top-left)
4. Name it "LinkedInJobs" and click "Create"
5. Wait for project creation (30 seconds)

6. **Enable Google Sheets API:**
   - Click the hamburger menu (three lines) → "APIs & Services" → "Library"
   - Search for "Google Sheets API"
   - Click on it and click "ENABLE"

7. **Create Service Account:**
   - Click hamburger menu → "APIs & Services" → "Credentials"
   - Click "CREATE CREDENTIALS" → "Service account"
   - Name: "linkedinbot"
   - Click "CREATE AND CONTINUE"
   - Skip the role assignment (click "CONTINUE")
   - Click "DONE"

8. **Download Credentials:**
   - Click on the "linkedinbot" service account you just created
   - Click "KEYS" tab
   - Click "ADD KEY" → "Create new key"
   - Choose "JSON" and click "CREATE"
   - A file downloads - this is your credentials!

9. **Share Your Google Sheet:**
   - Open the credentials file you downloaded (it's a text file)
   - Find the line with "client_email" - copy that email address
   - Go back to your Google Sheet
   - Click "Share" button
   - Add that email address
   - Give it "Editor" permission
   - Click "Send"

### Step 4: Configure the Tool

The setup script created template files. Now you need to put in your actual information:

#### 4A. Edit the .env file
1. **Mac:** Type `open .env` in Terminal
2. **Windows:** Type `notepad .env` in Command Prompt

Replace these lines:
```env
OPENAI_API_KEY=your_openai_api_key_here  
# ^ Put your OpenAI key here (the sk-proj-... one)

GROQ_API_KEY=your_groq_api_key_here
# ^ Put your Groq key here (the gsk_... one)

GOOGLE_SHEETS_ID=your_google_sheet_id_here
# ^ Put your Google Sheet ID here (the long string from the URL)
```

#### 4B. Replace credentials.json
1. **Mac:** 
   - Type `open config/` in Terminal (opens folder)
   - Drag your downloaded Google credentials file into this folder
   - Delete the old "credentials.json" file
   - Rename your downloaded file to "credentials.json"

2. **Windows:**
   - Type `explorer config` in Command Prompt (opens folder) 
   - Copy your downloaded credentials file here
   - Delete the old "credentials.json"  
   - Rename your file to "credentials.json"

#### 4C. Add Your Resume
1. Save your resume as a PDF
2. **Mac:** Type `open resumes/` in Terminal
3. **Windows:** Type `explorer resumes` in Command Prompt  
4. Put your resume PDF in this folder
5. Rename it to exactly "resume.pdf"

## 🚀 Run the Tool!

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

**What happens now?**
- The tool opens a Chrome browser
- Logs into LinkedIn (you might need to solve a captcha)
- Searches for jobs based on your criteria
- Analyzes each job against your resume
- Saves everything to your Google Sheet

This takes about 1 hour to find 1000+ jobs!

## 🆘 Getting Help

**Common Issues:**

1. **"Command not found"** → Make sure you installed Git and are in the right folder
2. **"Permission denied"** → Your Google Sheet isn't shared with the service account email
3. **"API key invalid"** → Double-check you copied the full API key correctly
4. **"Python not found"** → Run the setup script again

**Still stuck?** 
- Check the main [README.md](README.md) for more details
- Look at [config/README.md](config/README.md) for Google setup help

## 💰 Costs Summary

- **Groq:** FREE (recommended for speed)
- **OpenAI:** ~$5-20/month (backup/higher quality)  
- **Google Cloud:** FREE (for reasonable usage)
- **Your Time:** 30 minutes setup vs hours of manual job searching!

---

**Remember:** This tool is like having a job search assistant that never gets tired. Set it up once, and it can find relevant jobs for you automatically whenever you run it!