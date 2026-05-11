"""UI components for the Steam Achievement Tracker application.
"""
import random
from nicegui import ui
from app.get_achievements import DatabaseManager
from app.config import state, SYNC_INTERVAL
from app.utils import format_date
from app.ui_helpers import build_stat_col, show_details

@ui.refreshable
def header_status():
    """Display the auto-sync status and last sync time."""
    is_active = SYNC_INTERVAL > 0
    status_color = 'emerald-400' if is_active else 'red-500'
    status_text = 'AUTO-SYNC ACTIVE' if is_active else 'AUTO-SYNC DISABLED'
    time_color = 'text-emerald-400' if state["last_sync"] != "Never" else 'text-slate-500'
    with ui.row().classes('items-center gap-2'):
        ui.label(status_text).classes(f'text-[11px] {status_color} font-bold tracking-widest')
        ui.label('|').classes('text-[11px] text-slate-700')
        ui.label(f'LAST SYNC: {state["last_sync"]}').classes(f'text-[11px] {time_color} font-mono tracking-tighter')

@ui.refreshable
def global_stats_header():
    """Display global stats like average completion across all games."""
    db = DatabaseManager()
    stats = db.get_all_saved_stats()
    db.close()
    avg = sum(row[4] for row in stats) / len(stats) if stats else 0
    random_id = get_random_steam_image()
    img_url = f'https://cdn.akamai.steamstatic.com/steam/apps/{random_id}/header.jpg'

    with ui.card().classes('w-full max-w-7xl bg-slate-900 border border-blue-500/20 p-6 mb-8 shadow-2xl'):
        ui.image(img_url).classes('absolute inset-0 w-full h-full object-cover opacity-20 blur-sm')
        ui.element('div').classes('absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/60 to-transparent')
        with ui.row().classes('w-full justify-between items-end mb-2'):
            ui.label(f'Found {len(stats)} Games').classes('text-s font-mono text-blue-200 bg-blue-400/10 px-5 py-5 rounded')
            with ui.column().classes('gap-0'):
                ui.label('AVERAGE COMPLETION').classes('text-xs text-white font-bold')
                ui.label(f'{avg:.2f}%').classes('text-3xl font-black text-white')
            ui.linear_progress(avg / 100, show_value=False).props('color=blue-6 size=20px')
            with ui.row().classes('w-full justify-between mt-2 text-[10px] text-white font-bold'):
                ui.label('0%')
                ui.label('50%')
                ui.label('100%')

@ui.refreshable
def game_card(row: tuple):
    """Build a card UI element for a single game based on its stats."""
    app_id, name, total, unlocked, percent, _, last_played = row
    game_data = {'app_id': app_id, 'name': name, 'unlocked': unlocked, 'total': total, 'percent': percent, 'last_played': last_played}

    try:
        pct_val = float(percent)
    except (ValueError, TypeError):
        pct_val = 0.0

    with ui.card().tight().classes('bg-slate-800 hover:scale-105 transition-transform cursor-pointer') \
        .on('click', lambda _, gd=game_data: show_details(gd)):
        ui.image(f'https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg').classes('h-32')
        with ui.column().classes('p-4 w-full'):
            ui.label(name).classes('text-lg font-bold text-white truncate')
            ui.label(f'Last Played: {format_date(last_played)}').classes('text-[10px] text-gray-400')

            with ui.row().classes('w-full justify-between mt-2'):
                build_stat_col(unlocked, 'UNLOCKED')
                build_stat_col(f'{percent:.1f}%', 'DONE', color='blue-400')
            with ui.element('div').classes('w-full bg-gray-900 rounded-full h-1.5 mt-4 overflow-hidden'):
                # Determine color based on the float value
                bar_color = 'green' if pct_val > 99 else 'blue' if pct_val > 25 else 'orange'
                # NiceGUI linear_progress needs a value between 0.0 and 1.0
                ui.linear_progress(pct_val / 100, show_value=False).props(f'color={bar_color}-6')

# Helper function to handle page switching
def change_page(delta):
    """Change the current page by a delta and refresh the grid."""
    state['page'] += delta
    achievements_grid.refresh()  # pylint: disable=no-member
    ui.run_javascript('window.scrollTo({top: 0, behavior: "smooth"})')

@ui.refreshable
def achievements_grid():
    """Display a grid of game cards based on the current state (search, sort, pagination)."""
    db = DatabaseManager()
    all_stats = db.get_all_saved_stats(sort_mode=state['sort'])
    db.close()
    filtered = [row for row in all_stats if state['search'].lower() in row[1].lower()]
    # Simple pagination logic
    items_per_page = 12

    filtered = [row for row in all_stats if state['search'].lower() in row[1].lower()]
    total_items = len(filtered)
    max_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

    if state['page'] > max_pages:
        state['page'] = max_pages

    start = (state['page'] - 1) * items_per_page
    page_items = filtered[start : start + items_per_page]

    with ui.grid(columns=3).classes('w-full max-w-7xl gap-8'):
        for row in page_items:
            game_card(row)
        # Pagination Controls
    with ui.row().classes('w-full justify-center items-center mt-12 mb-12 gap-8'):
        btn_prev = ui.button(icon='chevron_left', on_click=lambda: change_page(-1)) \
            .props('flat color=blue-5 size=lg')
        btn_prev.enabled = state['page'] > 1
        ui.label(f"PAGE {state['page']} / {max_pages}").classes('text-sm font-black tracking-[.3em] text-gray-500')
        btn_next = ui.button(icon='chevron_right', on_click=lambda: change_page(1)) \
            .props('flat color=blue-5 size=lg')
        btn_next.enabled = state['page'] < max_pages

def wallboard_grid():
    """A simplified grid for the fullscreen wallboard view."""
    db = DatabaseManager()
    games = db.get_all_saved_stats(sort_mode='Completion')[:15]
    db.close()

    with ui.grid(columns=5).classes('w-full h-full gap-4'):
        for game_data in games:
            game_card(game_data)

def get_random_steam_image():
    """Fetch a random app_id from the database for the background."""
    db = DatabaseManager()
    stats = db.get_all_saved_stats()
    db.close()
    if stats:
        # Pick a random row, grab the app_id (index 0)
        return random.choice(stats)[0]
    return 440  # Fallback to Team Fortress 2 if DB is empty
