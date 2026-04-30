"""Configuration and state management for the Steam Achievement Tracker application.
"""
import os
import sqlite3
from nicegui import app
from dotenv import load_dotenv
from app.get_achievements import DatabaseManager

load_dotenv()

AUTH_USER = os.getenv('DASHBOARD_USER', 'admin')
AUTH_PASS = os.getenv('DASHBOARD_PASS', 'admin')
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '0'))
STORAGE_SECRET = os.getenv('NICEGUI_STORAGE_SECRET', 'fallback_secret')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'warning').upper()  # Default to WARNING if not set

state = {
    'search': '', 
    'sort': 'Last Played', 
    'page': 1, 
    'last_sync': 'Never'
}

def is_authenticated() -> bool:
    """Check if the user is authenticated based on the session storage."""
    return app.storage.user.get('authenticated', False)

def get_last_sync_from_db():
    """Fetch the last sync time from the database to display on the dashboard header."""
    try:
        db = DatabaseManager()
        stats = db.get_all_saved_stats(sort_mode='Last Played')
        db.close()
        if stats:
            return "Ready"
    except(sqlite3.Error, ImportError, AttributeError) as e:
        print(f"Error fetching last sync from DB: {e}")
    return "Never"

state['last_sync'] = get_last_sync_from_db()
