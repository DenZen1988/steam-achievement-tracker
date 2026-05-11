#!/usr/bin/env python3
"""Script to fetch steam achievements."""
import os
import time
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import requests
# Load environment variables from .env file
load_dotenv()

class SteamTracker:
    """Class to track Steam achievements for a user."""
    def __init__(self, api_key=None, steam_id=None):
        """
        Initialize with API key and Steam ID.
        If not provided, pulls from environment variables.
        """
        self.api_key = api_key or os.getenv("STEAM_API_KEY")
        self.steam_id = steam_id or os.getenv("STEAM_ID")
        self.base_url = "https://api.steampowered.com"

        if not self.api_key:
            raise ValueError("No Steam API Key found! Check your .env file.")
        if not self.steam_id:
            raise ValueError("No Steam ID found! Check your .env file.")

    def get_all_owned_games(self):
        """Fetch all owned games for the user."""
        endpoint = f"{self.base_url}/IPlayerService/GetOwnedGames/v1/"
        params = {
            "key": self.api_key,
            "steamid": self.steam_id,
            "include_appinfo": True,
            "include_played_free_games": True,
            'format': 'json'
        }
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("response", {}).get("games", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching games list: {e}")
            return []

    def get_game_completion(self, app_id):
        """Fetch achievement completion stats for a specific game."""
        endpoint = f"{self.base_url}/ISteamUserStats/GetPlayerAchievements/v1/"
        params = {
            'key': self.api_key, 
            'steamid': self.steam_id, 
            'appid': app_id,
            'l': 'en'
        }

        try:
            resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Some games don't have achievements or have private stats
            if 'playerstats' not in data or 'achievements' not in data['playerstats']:
                return None

            ach = data['playerstats']['achievements']
            total = len(ach)
            unlocked = sum(1 for a in ach if a['achieved'] == 1)

            return {
                "total": total,
                "unlocked": unlocked,
                "percentage": round((unlocked / total) * 100, 2) if total > 0 else 0
            }

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 403:
                # Common if game stats are set to private even if profile is public
                pass
            else:
                print(f"HTTP error for AppID {app_id}: {e}")
        except requests.exceptions.ConnectionError:
            print("Failed to connect to Steam servers.")
        except requests.exceptions.Timeout:
            print(f"Timeout reaching Steam for AppID {app_id}.")
        except (KeyError, ValueError) as e:
            print(f"Unexpected error for AppID {app_id}: {e}")

        return None

    def build_full_report(self, limit=10):
        """Build a report of owned games and their achievement completion."""
        owned_games = self.get_all_owned_games()
        if not owned_games:
            print("No games found or profile is private.")
            return []

        report = []
        # Logic: only check games that have been played to save time/API calls
        played_games = sorted(
            [g for g in owned_games if g.get('playtime_forever', 0) > 0],
            key=lambda x: x.get('playtime_forever', 0),
            reverse=True
        )

        print(f"Analyzing top {min(limit, len(played_games))} played games...")

        report = []
        for pgame in played_games[:limit]:
            gstats = self.get_game_completion(pgame["appid"])
            if gstats:
                report.append({
                    "name": pgame["name"],
                    "app_id": pgame["appid"],
                    **gstats
                })
            # Steam API is more lenient in 2026, but 0.2s is a safe "nice" delay
            time.sleep(0.2)

        return sorted(report, key=lambda x: x["percentage"], reverse=True)

class DatabaseManager:
    """Class to manage SQLite database for storing achievement data."""
    def __init__(self, db_name="steam_achievements.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Initialize the database table for storing achievement data."""
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            app_id INTEGER PRIMARY KEY,
            game_name TEXT,
            total INTEGER,
            unlocked INTEGER,
            percentage REAL,
            last_updated TEXT,
            last_played INTEGER
            )
        ''')
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        self.conn.commit()

    def save_game_stats(self, app_id, name, stats, last_played_timestamp=0):
        """Save or update game stats using the actual Steam last-played time."""
        query = """
        INSERT INTO achievements (app_id, game_name, total, unlocked, percentage, last_updated, last_played)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(app_id) DO UPDATE SET
            total=excluded.total,
            unlocked=excluded.unlocked,
            percentage=excluded.percentage,
            last_updated=excluded.last_updated,
            last_played=excluded.last_played
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # We use the timestamp from Steam for 'last_played'
        self.conn.execute(query, (
            app_id, name, stats['total'], stats['unlocked'], stats['percentage'], now, last_played_timestamp
        ))
        self.conn.commit()

    def get_all_saved_stats(self, sort_mode='Last Played'):
        """Fetch all games from the database with professional SQL sorting."""
        # Map the dropdown options to SQL ORDER BY clauses
        sort_mapping = {
            'Last Played': 'last_played DESC',
            'Completion (High to Low)': 'percentage DESC',
            'Completion (Low to High)': 'percentage ASC',
            'A-Z': 'game_name COLLATE NOCASE ASC'
        }
        order_clause = sort_mapping.get(sort_mode, 'last_played DESC')
        query = f"SELECT * FROM achievements ORDER BY {order_clause}"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def save_sync_time(self):
        """Save the last sync time to the database (for display in the UI)."""
        now = datetime.now().strftime("%b %d, %H:%M")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
        self.cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_sync', ?)", (now,))
        self.conn.commit()

    def get_sync_time(self):
        """Fetch the last sync time from the database."""
        try:
            self.cursor.execute("SELECT value FROM metadata WHERE key='last_sync'")
            result = self.cursor.fetchone()
            return result[0] if result else "Never"
        except sqlite3.Error as e:
            print(f"Error fetching last sync time: {e}")
            return "Never"

    def close(self):
        """Close the database connection."""
        self.conn.close()

if __name__ == "__main__":
    try:
        tracker = SteamTracker()
        db = DatabaseManager()

        print("\nFetching achievement data...\n")
        games_list = tracker.get_all_owned_games()
        # Filter to only games that have been played to save time and API calls
        target_games = sorted(
            [g for g in games_list if g.get('playtime_forever', 0) > 0],
            key=lambda x: x.get('playtime_forever', 0),
            reverse=True
        )

        for game in target_games: #[:10]:  # Limit to top 10 played games for demo
            game_stats = tracker.get_game_completion(game["appid"])
            if game_stats:
                last_played = game.get("rtime_last_played", 0)
                db.save_game_stats(game["appid"], game["name"], game_stats, last_played)
                print(f"Saved stats for {game['name']} - {game_stats['percentage']}% completed (Played: {last_played})")
            time.sleep(0.2)

        print("\nCurrent Achievement Completion Report:")
        for row in db.get_all_saved_stats():
            print(f"{row[1]}: {row[4]}% completed (Played: {row[6]})")

        db.close()

    except ValueError as e:
        print(f"Configuration error: {e}")
