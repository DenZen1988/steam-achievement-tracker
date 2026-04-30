"""Utility functions for the Steam Achievement Tracker application.
"""
from datetime import datetime

def format_date(timestamp):
    """Convert a UNIX timestamp to a human-readable date format."""
    if not timestamp or timestamp == 0:
        return 'Never'
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%b %d, %Y')
