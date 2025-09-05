# CanillitaBot Dashboard

A simple, focused web interface for monitoring CanillitaBot's processed posts.

## Structure

```
src/dashboard/
├── __init__.py          # Package initialization
├── app.py              # Main Flask application (simplified)
├── templates/          # HTML templates
│   └── dashboard.html  # Main dashboard template
└── static/             # Static assets
    ├── style.css       # Dashboard styles
    └── dashboard.js    # Dashboard JavaScript
```

## Features

The simplified dashboard provides:

- **Clean interface**: Just the title and a table of processed posts
- **Post overview**: View post title, processing result, and date
- **Comment viewing**: Click any post title to see the generated comment in a modal
- **Retry functionality**: Retry button for each post to reprocess if needed
- **Auto-refresh**: Updates every 30 seconds
- **Responsive design**: Works on desktop and mobile devices

## Usage

### Running the Dashboard

```python
from src.dashboard.app import CanillitaDashboard

# Create and run dashboard
dashboard = CanillitaDashboard(host='0.0.0.0', port=5000)
dashboard.run()
```

### Command Line

```bash
python -m src.dashboard.app --host 0.0.0.0 --port 5000
```

### Development Mode

```bash
python -m src.dashboard.app --debug
```

## API Endpoints

The simplified dashboard provides these REST API endpoints:

- `GET /` - Main dashboard page
- `GET /api/posts` - Get recent processed posts with comment data
- `POST /api/retry-post/<post_id>` - Retry processing a specific post
- `GET /api/health` - Basic health check

## Interface

The dashboard shows a clean table with:

1. **Post Title** - Click to view the generated comment in a modal
2. **Result** - ✅ Success or ❌ Error status
3. **Date** - When the post was processed
4. **Action** - Retry button to reprocess the post

All unnecessary complexity has been removed to focus on the core functionality of monitoring what posts have been processed and allowing easy retry of failed posts.
