"""Main dashboard application for the Steam Achievement Tracker. Handles routing, authentication, and background syncing.
"""
import asyncio
import sqlite3
from nicegui import app, ui
from fastapi.responses import RedirectResponse
import requests
from app.get_achievements import SteamTracker, DatabaseManager
# Modular Imports
from app.config import AUTH_USER, AUTH_PASS, SYNC_INTERVAL, STORAGE_SECRET, LOG_LEVEL, state, is_authenticated
from app.ui_components import header_status, global_stats_header, achievements_grid, wallboard_grid

async def run_sync_process():
    """Run the synchronization process to fetch latest achievement data from Steam and update the database."""
    tracker = SteamTracker()
    loop = asyncio.get_event_loop()
    def sync_logic():
        db = DatabaseManager()
        games = tracker.get_all_owned_games()
        played = [g for g in games if g.get('playtime_forever', 0) > 0]
        for g in played:
            s = tracker.get_game_completion(g["appid"])
            if s:
                db.save_game_stats(g["appid"], g["name"], s, g.get("rtime_last_played", 0))
        db.close()
    await loop.run_in_executor(None, sync_logic)

async def background_sync():
    """Trigger the background synchronization process and update the UI components upon completion."""
    try:
        await run_sync_process()
        db = DatabaseManager()
        state['last_sync'] = db.get_sync_time()
        db.close()
        header_status.refresh()
        global_stats_header.refresh()
        achievements_grid.refresh()
    except (requests.exceptions.RequestException, sqlite3.Error) as e:
        # Catching specific "External" errors
        print(f"CRON ERROR (Network/DB): {e}")
        ui.notify(f'Sync failed (Expected): {e}', color='warning')
    except Exception as e:
        print(f"CRON FATAL ERROR: {e}")
        ui.notify('A critical system error occurred during sync.', color='negative')
        raise e

async def refresh_data():
    """Manual sync triggered by the button."""
    n = ui.notification('Syncing Steam Library...', spinning=True, timeout=None, type='info', close_button=False)
    try:
        # Reuse the background sync logic we already built
        await run_sync_process()
        # Update last synced time
        db = DatabaseManager()
        db.save_sync_time()  # Update the sync time in the DB
        state['last_sync'] = db.get_sync_time()
        db.close()
        # Update UI
        header_status.refresh()  # pylint: disable=no-member
        global_stats_header.refresh() # pylint: disable=no-member
        achievements_grid.refresh()   # pylint: disable=no-member
        ui.notify('Library Synced Successfully!', color='green', icon='done')
    except (requests.exceptions.RequestException, sqlite3.Error) as e:
        print(f"SYNC ERROR (Network/DB): {e}")
        ui.notify(f'Connection failed: {e}', color='warning')
    except Exception as e:
        print(f"CRITICAL SYNC ERROR: {e}")
        ui.notify('A critical system error occurred.', color='negative')
        raise e
    finally:
        n.dismiss()

@ui.page('/login')
def login_page():
    """Login page for the dashboard. Validates credentials and sets authentication state."""
    def try_login():
        if username.value == AUTH_USER and password.value == AUTH_PASS:
            app.storage.user.update({'authenticated': True})
            ui.navigate.to('/')
        else:
            ui.notify('Invalid credentials', color='negative')
    with ui.card().classes('absolute-center w-80 p-8 bg-slate-800'):
        username = ui.input('User').classes('w-full').props('dark')
        password = ui.input('Pass', password=True).classes('w-full').props('dark')
        ui.button('SIGN IN', on_click=try_login).classes('w-full mt-4')

def logout():
    """Clear the authentication session and redirect to login."""
    app.storage.user.update({'authenticated': False})
    ui.navigate.to('/login')

@ui.page('/')
async def main_page():
    """Main dashboard page. Displays stats and achievement grid. Requires authentication."""
    if not is_authenticated():
        return RedirectResponse('/login')

    # Get last sync state from DB
    db = DatabaseManager()
    state['last_sync'] = db.get_sync_time()
    db.close()

    # Dark mode and header
    ui.dark_mode().enable()
    ui.add_head_html('<style>.q-linear-progress__label { display: none !important; }</style>')

    with ui.column().classes('w-full items-center p-8 gap-6'):
        header_status()
        # Title Section
        with ui.column().classes('items-center mb-4'):
            ui.label('Steam Achievement Dashboard').classes('text-4xl font-black text-blue-500')
            ui.label('PERSONAL STATS & COMPLETION TRACKER').classes('text-[14px] font-bold text-gray-500 tracking-[.4em] uppercase mt-[-8px]')
        # THE CONTROL BAR (Search, Sort, Sync, Logout)
        # Added 'mx-auto' and ensured it is max-w-7xl to match the grid
        with ui.row().classes('w-full max-w-7xl items-center justify-between mb-8 gap-4 mx-auto'):
            # Wallboard button
            with ui.button(icon='monitor', on_click=lambda: ui.navigate.to('/fullscreen')) \
                .classes('rounded-xl h-14 w-14 px-4 bg-slate-800').props('flat color=white'):
                ui.tooltip('View Fullscreen Wallboard')
            # Search Input
            ui.input(placeholder='Search your game library...',
                on_change=lambda: (state.update({'page': 1}), achievements_grid.refresh())) \
                .bind_value(state, 'search') \
                .classes('grow bg-slate-800 rounded-xl h-14 px-4 text-white border-none shadow-inner') \
                .props('dark borderless hide-bottom-space')
            # Sort Dropdown
            ui.select(
                options=['Last Played', 'Completion (High to Low)', 'Completion (Low to High)', 'A-Z'],
                on_change=achievements_grid.refresh
            ).bind_value(state, 'sort').classes('w-64 bg-slate-800 rounded-xl px-4').props('dark borderless')
            # Action Buttons
            with ui.row().classes('items-center gap-2'):
                with ui.button(icon='sync', on_click=refresh_data).classes('rounded-xl h-14 w-14').props('color=blue-7'):
                    ui.tooltip('Refresh Achievements from Steam').classes('bg-blue-800 text-white font-bold')
                with ui.button(icon='logout', on_click=logout) \
                    .classes('rounded-xl h-14 w-14 hover:bg-red-900/20 transition-colors') \
                    .props('color=red-4 flat'):
                    ui.tooltip('Logout of Dashboard').classes('bg-red-900 text-white font-bold')
        # Main Content
        global_stats_header()
        achievements_grid()

# Fullscreen page / kiosk mode for wallboard display
@ui.page('/fullscreen')
async def wallboard_page():
    """A simplified, fullscreen view of the achievement grid for display purposes."""
    if not is_authenticated():
        return RedirectResponse('/login')

    # Hide scrollbars and set a dark background for the wallboard
    ui.query('body').style('background-color: #020617; overflow: hidden;')
    ui.dark_mode().enable()

    def refresh_wallboard():
        """Refresh the wallboard data."""
        global_stats_header.refresh()
        wallboard_container.refresh()
        ui.notify('Wallboard Updated', color='dark', icon='sync', pos='bottom-right')

    @ui.refreshable
    def wallboard_container():
        wallboard_grid()

    ui.timer(300, refresh_wallboard)

    wallboard_container()

    with ui.row().classes('items-center gap-2 opacity-50'):
        ui.element('div').classes('w-4 h-2 rounded-full bg-emerald-500 animate-pulse')
        ui.label('WALLBOARD MODE ACTIVE').classes('text-[10px] text-emerald-500 font-bold tracking-[0.3em]')

if __name__ in {"__main__", "__mp_main__"}:
    if SYNC_INTERVAL > 0:
        app.timer(SYNC_INTERVAL, background_sync)
    ui.run(
        host='0.0.0.0',
        port=8080,
        title='Steam Achievement Tracker',
        favicon='https://store.steampowered.com/favicon.ico',
        uvicorn_logging_level=LOG_LEVEL.lower(),
        dark=True,
        storage_secret=STORAGE_SECRET
    )
