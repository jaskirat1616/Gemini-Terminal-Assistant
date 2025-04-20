import json

from rich.panel import Panel

from app.ui.styles import STYLE_INFO, STYLE_SUCCESS, STYLE_WARNING


async def handle_context_command(terminal, console, args_str: str):
    """Handle /context command and its arguments."""
    if not args_str:
        # Show current context
        context_str = json.dumps(terminal.context, indent=2) if terminal.context else "[Context is empty]"
        console.print(Panel(context_str, title="Current Context", border_style=STYLE_INFO, expand=False))
    elif args_str.lower() == "clear":
         terminal.context = {}
         console.print(f"[{STYLE_SUCCESS}]Context cleared.[/]")
    else:
         # Simple way to add/update context - might need refinement
         # e.g., /context set key=value
         parts = args_str.split('=', 1)
         if len(parts) == 2:
              key, value = parts
              terminal.context[key.strip()] = value.strip()
              console.print(f"[{STYLE_SUCCESS}]Context updated: {key.strip()} = {value.strip()}[/]")
         else:
              console.print(f"[{STYLE_WARNING}]Usage: /context or /context clear or /context <key>=<value>[/]")
    return True 