from pygments.styles import get_all_styles
from rich.table import Table

from app.ui.styles import STYLE_WARNING, STYLE_SUCCESS, STYLE_COMMAND, STYLE_EMPHASIS


async def handle_theme_command(terminal, console, args_str: str):
    """List available themes or set the syntax theme."""
    theme_name = args_str.strip()
    available_themes = sorted(list(get_all_styles()))

    if theme_name:
        if theme_name in available_themes:
            terminal.config.theme = theme_name
            terminal.config._save_config()
            console.print(f"[{STYLE_SUCCESS}]Syntax theme changed to: {terminal.config.theme}[/]")
        else:
            console.print(f"[{STYLE_WARNING}]Unknown theme: {theme_name}. Use /theme to list.[/{STYLE_WARNING}]")
    else:
        theme_table = Table(title="Available Syntax Themes", box=None, show_header=False, padding=(0, 2), expand=True)
        num_columns = 4
        num_themes = len(available_themes)
        themes_per_col = (num_themes + num_columns - 1) // num_columns

        rows = []
        for i in range(themes_per_col):
             row = [available_themes[i + j * themes_per_col] if (i + j * themes_per_col) < num_themes else "" for j in range(num_columns)]
             rows.append(row)

        for _ in range(num_columns):
             theme_table.add_column()

        for row in rows:
             theme_table.add_row(*row)

        console.print(theme_table)
        console.print(f"\nCurrent theme: [{STYLE_EMPHASIS}]{terminal.config.theme}[/]")
        console.print(f"Usage: [{STYLE_COMMAND}]/theme <theme_name>[/]") 