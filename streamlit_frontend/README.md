# ZTA-AI Streamlit Frontend

## Overview

The ZTA-AI frontend has been migrated from HTML/JavaScript to Streamlit for a better development experience and easier integration.

## Features

- 🔐 **Mock Google OAuth Authentication** - Test users dropdown for quick login
- 💬 **Real-time Chat Interface** - Ask questions about your data
- 👤 **Persona-based Access Control** - View your access rights and masked fields
- 📊 **Visual User Profile** - See your allowed/denied domains, persona badge
- 💡 **Query Suggestions** - Smart suggestions based on your persona
- ⏱️ **Response Metrics** - View source and latency for each query
- 🎨 **Modern UI** - Clean, professional interface with custom styling

## Running the Application

### Using Docker Compose (Recommended)

```bash
# From the repository root
docker compose up -d

# Access the application
# Streamlit: http://localhost:8501
# API: http://localhost:8000
# Backend Health: http://localhost:8000/health
```

### Local Development

```bash
cd streamlit_frontend

# Install dependencies
pip install -r requirements.txt

# Set API base URL (optional, defaults to http://localhost:8000)
export API_BASE_URL="http://localhost:8000"

# Run Streamlit
streamlit run streamlit_app.py
```

## Test Users

The application includes 6 pre-configured test users:

| Persona | Email | Department | Allowed Domains | Chat Enabled |
|---------|-------|------------|-----------------|--------------|
| 👨‍🎓 Student | student@campusa.edu | CSE | academic, finance_self, notices | ✅ Yes |
| 👨‍🏫 Faculty | faculty@campusa.edu | CSE | academic, hr_self, notices | ✅ Yes |
| 👨‍💼 IT Head | it.head@campusa.edu | IT | admin | ❌ No (Dashboard only) |
| 👔 IPEDS Executive | executive@ipeds.local | Executive Office | campus, ipeds, analytics, reports | ✅ Yes |
| 📋 Admissions Staff | admissions@ipeds.local | Admissions | admissions, analytics | ✅ Yes |
| 🔧 IPEDS IT Head | ithead@ipeds.local | Information Technology | admin | ❌ No |

## Usage

1. **Login**: Select a test user from the dropdown and click "Login"
2. **View Profile**: Check sidebar for your persona, department, and access rights
3. **Try Suggestions**: Click on suggested queries based on your persona
4. **Ask Questions**: Type your query in the input box and click "Send"
5. **View History**: Scroll through your chat history with timestamps and metrics

## Example Queries

### For Students
- "How many students are enrolled?"
- "What's my GPA?"
- "Show me course enrollment"

### For Faculty
- "Show me my courses"
- "What's the attendance for CSE101?"

### For IPEDS Executive
- "How many institutions are there?"
- "Total enrollment across all institutions"
- "Show me HBCU demographics"

## Architecture

```
User Browser
    ↓
Streamlit Frontend (port 8501)
    ↓ HTTP/REST
Backend API (port 8000)
    ↓
Database / Redis / Workers
```

## Configuration

The Streamlit app can be configured via Streamlit secrets or environment variables:

**Streamlit Secrets** (`~/.streamlit/secrets.toml`):
```toml
api_base_url = "http://api:8000"  # For Docker
# or
api_base_url = "http://localhost:8000"  # For local dev
```

**Environment Variable**:
```bash
export API_BASE_URL="http://localhost:8000"
```

## Ports

- **8501**: Streamlit frontend (main access point)
- **8000**: Backend API
- **5432**: PostgreSQL database
- **6379**: Redis cache

## Removed Old Frontend

The previous HTML/JavaScript frontend has been replaced. The following files are no longer used:
- `/frontend/index.html`
- `/frontend/script.js`
- `/frontend/style.css`
- `/frontend/nginx.conf`
- `/frontend/Dockerfile`

## Notes

- Mock authentication is enabled by default for development
- Real Google OAuth can be enabled by setting `USE_MOCK_GOOGLE_OAUTH=false` in backend `.env`
- JWT tokens expire after 30 minutes
- Chat history is stored in the backend and persists across sessions
- IT Head personas have chat disabled (they use admin dashboard instead)

## Troubleshooting

**Cannot connect to backend:**
- Ensure API container is running: `docker compose ps`
- Check backend health: `curl http://localhost:8000/health`
- View API logs: `docker compose logs api`

**Streamlit not loading:**
- Check Streamlit logs: `docker compose logs streamlit`
- Ensure port 8501 is not in use: `lsof -i :8501`
- Restart container: `docker compose restart streamlit`

**Authentication fails:**
- Verify database is seeded: `docker compose logs db-init`
- Check if users exist: Query `users` table in PostgreSQL
- Ensure `USE_MOCK_GOOGLE_OAUTH=true` in backend `.env`

## Development

To modify the Streamlit app:

1. Edit `streamlit_frontend/streamlit_app.py`
2. Rebuild container: `docker compose up --build streamlit -d`
3. Or run locally with hot reload: `streamlit run streamlit_app.py`

Streamlit provides hot reloading during development - changes to the Python file will automatically refresh the browser.
