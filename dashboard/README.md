# Job Automator AI Dashboard

## 🚀 Quick Start

### Option 1: Static Dashboard (No Backend Required)
Simply open `index.html` in your browser to view the dashboard with mock data.

```bash
cd dashboard
open index.html  # On Mac
# OR
python -m http.server 8000  # Then visit http://localhost:8000
```

### Option 2: Live Dashboard with Backend (Connected to Google Sheets & LinkedIn)

1. **Install Requirements**
```bash
pip install flask flask-cors
```

2. **Configure Your Credentials**
Edit `../config.py` with your API keys:
- OpenAI/Groq API key for AI matching
- Google Sheets credentials
- LinkedIn login (if needed)

3. **Start the Backend Server**
```bash
python backend_server.py
```

4. **Access Dashboard**
Open http://localhost:5000 in your browser

## 🔗 Live Connection Status

### Currently Connected ✅
When running `backend_server.py`:
- **Database**: Reads/writes jobs to local SQLite database
- **AI Matching**: Uses OpenAI/Groq for resume matching
- **Google Sheets**: Syncs jobs in real-time
- **LinkedIn Scraper**: Searches and scrapes jobs

### Mock Mode 🎭
When opening `index.html` directly:
- Uses simulated data
- All features work with demo data
- No external connections required

## 📊 API Endpoints

The backend server provides these endpoints to connect the dashboard with your automation:

| Endpoint | Method | Description | Connected to |
|----------|---------|-------------|--------------|
| `/api/dashboard/stats` | GET | Dashboard statistics | Database + Sheets |
| `/api/jobs/search` | POST | Start LinkedIn search | LinkedIn Scraper |
| `/api/jobs/recent` | GET | Get recent jobs | Database |
| `/api/jobs/<id>` | GET | Job details + AI analysis | Database + AI |
| `/api/export/sheets` | POST | Export to Google Sheets | Google Sheets API |
| `/api/sheets/data` | GET | Read from Sheets | Google Sheets API |

## 🔧 How to Make it Fully Live

### 1. Database Connection ✅
Already connected via `database/db_manager.py`

### 2. Google Sheets Connection 📊
```python
# In config.py, ensure you have:
GOOGLE_SHEETS_ID = "your-sheet-id"
GOOGLE_SHEETS_CREDENTIALS_PATH = "path/to/credentials.json"
```

### 3. LinkedIn Scraper 🔍
The scraper runs when you click "Start Search" in the dashboard:
- Uses Playwright for browser automation
- Scrapes job details
- Saves to database
- Syncs to Google Sheets

### 4. AI Matching 🤖
Configure in `config.py`:
```python
# For OpenAI
OPENAI_API_KEY = "sk-..."

# OR for Groq
GROQ_API_KEY = "gsk_..."
AI_PROVIDER = "groq"  # or "openai"
```

## 📁 File Structure

```
dashboard/
├── index.html           # Main dashboard
├── css/
│   └── dashboard.css    # Styling
├── js/
│   ├── dashboard.js     # Core functionality
│   ├── api.js          # API calls (modify baseURL here)
│   └── charts.js       # Chart.js visualizations
├── backend_server.py   # Flask API server (NEW)
└── README.md          # This file
```

## 🔄 Real-Time Updates

The dashboard includes WebSocket support for real-time updates:
- Job search progress
- New jobs found
- Sync status

To enable WebSocket, add to `backend_server.py`:
```python
from flask_socketio import SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")
```

## 🎨 Customization

### Change API Endpoint
Edit `js/api.js` line 5:
```javascript
this.baseURL = 'http://localhost:5000/api';  // Your backend URL
```

### Modify Mock Data
Edit the `getMock*` functions in `js/api.js` to change demo data.

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Sync Offline" status | Start `backend_server.py` |
| No data showing | Check browser console for errors |
| Can't connect to Sheets | Verify credentials in `config.py` |
| Search not working | Ensure Chrome/Chromium is installed |

## 📝 Notes

- The dashboard works standalone with mock data
- Backend server required for live Google Sheets integration
- All LinkedIn scraping happens server-side for security
- API keys are never exposed to the frontend