from rich.table import Table
from rich import box
from pathlib import Path

from app.ui.styles import STYLE_TITLE, STYLE_BORDER, STYLE_INFO, STYLE_DIM

async def show_config_command(terminal, console):
    """Show current configuration."""
    config_table = Table(title=f"[{STYLE_TITLE}]Current Configuration[/]", box=box.ROUNDED, border_style=STYLE_BORDER, expand=True, padding=(0, 1), show_header=True, header_style="bold magenta")
    config_table.add_column("Setting", style=STYLE_INFO, justify="right", no_wrap=True)
    config_table.add_column("Value")

    config_to_show = vars(terminal.config).copy()

    if 'api_key' in config_to_show:
         config_to_show['api_key'] = ("*" * (len(config_to_show['api_key']) - 4) + config_to_show['api_key'][-4:]) if config_to_show['api_key'] and len(config_to_show['api_key']) > 4 else "[Set]" if config_to_show['api_key'] else "[Not Set]"
    if 'config_path' in config_to_show and isinstance(config_to_show['config_path'], Path):
         config_to_show['config_path'] = str(config_to_show['config_path'].resolve())

    key_order = ['model', 'theme', 'temperature', 'top_p', 'top_k', 'allow_execution', 'system_message', 'api_key', 'config_path']
    shown_keys = set()

    for key in key_order:
         if key in config_to_show and not key.startswith('_'):
             display_key = key.replace("_", " ").title()
             value = config_to_show[key]
             display_value = str(value)
             if key == "system_message" and value:
                  display_value = f'"{value[:60]}..."' if len(value) > 60 else f'"{value}"'
             elif not value and key == "system_message":
                  display_value = "[Not Set]"
             config_table.add_row(display_key, display_value)
             shown_keys.add(key)

    for key, value in config_to_show.items():
         if not key.startswith('_') and key not in shown_keys:
             display_key = key.replace("_", " ").title()
             config_table.add_row(display_key, str(value))

    console.print(config_table)
    if 'config_path' in config_to_show:
        console.print(f"\n[{STYLE_DIM}]Config loaded from: {config_to_show['config_path']}[/{STYLE_DIM}]") 