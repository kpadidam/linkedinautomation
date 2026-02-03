# Configuration Setup Guide

This folder contains the configuration files needed to run the LinkedIn Job Automation system.

## 📋 Required Files

### 1. `credentials.json` - Google Sheets API Credentials

**How to get your Google Cloud credentials:**

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project (or select existing one)
   - Remember your project ID for reference

2. **Enable Google Sheets API**
   - Navigate to **APIs & Services** → **Library**
   - Search for "Google Sheets API"
   - Click **Enable**

3. **Create Service Account**
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **Service Account**
   - Enter details:
     - **Name**: `linkedinautomation` (or any descriptive name)
     - **Description**: "Service account for LinkedIn job automation"
   - Click **Create and Continue**
   - Skip role assignment (click **Continue**)
   - Click **Done**

4. **Generate Credentials File**
   - Click on your newly created service account
   - Go to **Keys** tab
   - Click **Add Key** → **Create New Key**
   - Select **JSON** format
   - Download the file
   - **Rename it to `credentials.json`** and place it in this `/config` folder

5. **Share Your Google Sheet**
   - Create a new Google Sheet for storing job data (can be completely empty)
   - Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`
   - Share the sheet with the service account email from your `credentials.json` file
   - Give **Editor** permissions

**What happens automatically:**
The system will create these 16 column headers on first run:
- `Job ID`, `Date`, `Time`, `Role`, `Company`, `Location`
- `Job Type`, `Level`, `Link`, `Job Responsibilities` 
- `Preferred Skills`, `Matching Skills`, `Role Match %`
- `Salary`, `Posted`, `Number of Applicants`

**Example row data:**
```
123456 | 2026-02-03 | 14:30:25 | Data Analyst | TechCorp | San Francisco, CA |
Full-time | Mid-level | https://linkedin.com/jobs/123456 | • Analyze data trends... |
Python, SQL, Tableau | Python, SQL | 85% | $80,000 - $100,000 | 2 days ago | 15 applicants
```

### 2. `job_preferences.json` - Job Search Criteria

This file controls what jobs to search for. Edit the categories, keywords, and preferences to match your job search needs.

**Key sections to customize:**
- `keywords`: Job titles you're interested in
- `skills`: Technologies/skills to match against
- `location`: Geographic preferences
- `remote_ok`: Whether to include remote jobs
- `max_results`: Number of jobs to find per category

### 3. `user_profile.json` - Your Profile Information

Update this file with your personal information:
- Name and contact details
- Skills and experience level
- Current job title and preferences

## 🔧 Setup Checklist

- [ ] Created Google Cloud project
- [ ] Enabled Google Sheets API
- [ ] Created service account
- [ ] Downloaded `credentials.json` to this folder
- [ ] Created Google Sheet for job data
- [ ] Shared Google Sheet with service account email
- [ ] Updated `job_preferences.json` with your search criteria
- [ ] Updated `user_profile.json` with your information
- [ ] Added Google Sheet ID to `.env` file (`GOOGLE_SHEETS_ID`)

## 🔒 Security Notes

- **Never commit `credentials.json` to version control**
- The service account only has access to sheets you explicitly share with it
- Keep your Google Cloud project private
- Regularly rotate service account keys if needed

## 🐛 Troubleshooting

**"Permission denied" errors:**
- Verify the Google Sheet is shared with the service account email
- Check that the service account has Editor permissions

**"API not enabled" errors:**
- Ensure Google Sheets API is enabled in your Google Cloud project

**Authentication errors:**
- Verify `credentials.json` is valid JSON
- Check that the file path in `.env` is correct (`GOOGLE_SHEETS_CREDENTIALS_PATH`)

## 📄 Example File Structure

Your `/config` folder should contain:
```
config/
├── README.md (this file)
├── credentials.json (your Google Cloud service account key)
├── job_preferences.json (job search criteria)
└── user_profile.json (your profile information)
```

---

**Need help?** Check the main project README for additional troubleshooting steps.