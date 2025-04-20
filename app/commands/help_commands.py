from rich.table import Table
from rich import box
from rich.text import Text
from rich.panel import Panel

from app.ui.styles import STYLE_TITLE, STYLE_BORDER, STYLE_COMMAND, STYLE_INFO, STYLE_EMPHASIS, LOGO


async def show_help_command(console):
    """Show help information using Rich Table."""
    help_table = Table(title=f"[{STYLE_TITLE}]Available Commands[/]", box=box.ROUNDED, show_header=True, header_style="bold magenta", expand=True, padding=(0,1))
    help_table.add_column("Command", style=STYLE_COMMAND, width=20, no_wrap=True)
    help_table.add_column("Arguments", style=STYLE_INFO, width=25)
    help_table.add_column("Description")

    commands_desc = {
        "/help": ("", "Show this help message"),
        "/clear": ("", "Clear the terminal screen"),
        "/exit": ("", "Exit the application"),
        "/models": ("[name]", "List models or switch to [name]"),
        "/save": ("[filename]", "Save conversation (optional filename)"),
        "/load": ("<filename>", "Load conversation from file"),
        "/tools": ("", "List available tools and their usage"),
        "/config": ("", "Show current configuration"),
        "/system": ("[message]", "View or set the system message for the LLM"),
        "/theme": ("[name]", "List themes or set syntax highlighting theme"),
        "/execute": ("<command>", "Execute a shell command directly"),
        "/summary": ("", "Ask the LLM to summarize the conversation"),
        "/git_status": ("[path]", "Show Git status for a directory (default: .)"),
        "/lint": ("[path]", "Run code linter (flake8) on path (default: .)"),
        "/git_diff": ("<file1> <file2>", "Show Git diff between two files"),
        "/ps": ("", "List running processes"),
        "/git_log": ("[path] [--count=N]", "Show Git commit log (default: 15 commits)"),
        "/find_large": ("[path] [--count=N]", "Find largest files (default: 10 files)"),
        "/ping": ("<host>", "Ping a network host"),
        "/curl": ("<url>", "Fetch content from a URL"),
        "/interpret": ("<phrase>", "Interpret a natural language command"),
        "/context": ("[key=value|clear]", "View, set, or clear context")
    }
    for cmd, (args, desc) in commands_desc.items():
         help_table.add_row(cmd, args, desc)

    console.print(help_table)


async def show_welcome_command(terminal, console):
    """Show welcome message."""
    welcome_content = Text.from_markup(
        f"[bold {STYLE_INFO}]{LOGO}[/]\n"
        f"[bold {STYLE_TITLE}]Gemini Terminal Assistant[/]\n\n"
        f"[{STYLE_EMPHASIS}]Model:[/] {terminal.config.model}\n"
        f"[{STYLE_EMPHASIS}]Theme:[/] {terminal.config.theme}\n"
        f"\nType [{STYLE_COMMAND}]/help[/] for available commands."
    )
    console.print(Panel(
        welcome_content,
        box=box.DOUBLE_EDGE,
        border_style=STYLE_BORDER,
        padding=(1, 2),
        expand=False
    )) 