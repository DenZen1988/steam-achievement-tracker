"""UI helper functions for the Steam Achievement Tracker application.
"""
from nicegui import ui
from app.utils import format_date

def build_stat_col(value, label, color='white'):
    """Build a column displaying a statistic with a label."""
    with ui.column().classes('gap-0'):
        ui.label(str(value)).classes(f'text-2xl font-bold text-{color}')
        ui.label(label).classes('text-[8px] text-gray-400 tracking-widest')

def show_details(game: dict):
    """Display a detailed view of a game's achievement stats in a dialog."""
    game_name = game.get('name', 'Unknown')
    app_id = game.get('app_id', 0) or 0
    unlocked = game.get('unlocked', 0) or 0
    total = game.get('total', 0) or 0
    percent = game.get('percent', 0.0) or 0
    last_played = game.get('last_played', 0) or 0

    with ui.dialog() as dialog, ui.card().classes('bg-slate-900 text-white w-[500px] p-0 overflow-hidden border border-blue-500/30'):
        ui.image(f'https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg').classes('w-full h-48 object-cover')
        with ui.column().classes('p-6 w-full gap-4'):
            with ui.row().classes('w-full justify-between items-start'):
                with ui.column():
                    ui.label(game_name).classes('text-3xl font-black text-blue-400 leading-none')
                    ui.label(f'LAST SESSION: {format_date(last_played)}').classes('text-[10px] font-bold text-gray-500 mt-2 tracking-widest')
                badge_color = 'emerald-500' if percent == 100 else 'blue-500'
                ui.label('COMPLETED' if percent == 100 else 'IN PROGRESS').classes(f'text-[10px] font-bold px-2 py-1 rounded bg-{badge_color}')

            ui.separator().classes('bg-gray-700')

            with ui.row().classes('w-full justify-around text-center'):
                build_stat_col(unlocked, 'UNLOCKED')
                build_stat_col(total - unlocked, 'REMAINING')
                build_stat_col(f'{percent:.2f}%', 'COMPLETE', color='blue-400')

            bar_color = 'green' if percent > 99 else 'blue' if percent > 25 else 'orange'
            ui.linear_progress(percent / 100, show_value=False).props(f'color={bar_color} size=12px').classes('rounded-full')

            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('CLOSE', on_click=dialog.close).classes('grow').props('outline color=white')
                with ui.link('', f'https://store.steampowered.com/app/{app_id}', new_tab=True).classes('grow'):
                    ui.button('STORE', icon='shopping_cart').classes('w-full bg-blue-600')
    dialog.open()
