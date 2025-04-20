from typing import Optional

from rich.table import Table
from rich import box
from rich.text import Text
from rich.panel import Panel

from app.ui.styles import STYLE_INFO, STYLE_TITLE, STYLE_BORDER, STYLE_COMMAND, STYLE_WARNING, STYLE_DIM, STYLE_SUCCESS, STYLE_ERROR
from app.utils.helpers import ensure_renderable


async def show_tools_command(terminal, console):
    """Show available tools from ToolManager."""
    tools_info = terminal.tool_manager.get_available_tools()
    if not tools_info:
        console.print("No tools available.", style=STYLE_INFO) # Assuming STYLE_INFO is defined
        return

    table = Table(title=f"[{STYLE_TITLE}]Available Tools[/]", box=box.ROUNDED, border_style=STYLE_BORDER, expand=True, padding=(0, 1), show_header=True, header_style="bold magenta")
    table.add_column("Tool Name", style=STYLE_COMMAND, width=15, no_wrap=True)
    table.add_column("Description", min_width=30)
    table.add_column("Usage Example", style=STYLE_WARNING, min_width=30)

    for tool_name, tool_info in sorted(tools_info.items()):
        table.add_row(
            tool_name,
            tool_info.get("description", "N/A"),
            tool_info.get("usage", "N/A")
        )
    console.print(table)
    console.print(f"\n[{STYLE_DIM}]Tools can often be invoked directly (e.g., 'file list .') or via /execute <tool_command>.[/{STYLE_DIM}]")


async def run_tool_command(terminal, console, tool_name: str, args: str, title: Optional[str] = None):
    """Run a tool command and display the results."""
    result = await terminal.tool_manager._execute_tool(tool_name, args)
    
    # Ensure the result is a Rich-renderable object
    if isinstance(result, dict):
        # If the result is a dictionary, convert it to a Rich Text object
        result_text = Text()
        for key, value in result.items():
            result_text.append(f"{key}: {value}\n", style="white")
        result = Panel(result_text, title=title or f"🔧 {tool_name}", border_style=STYLE_SUCCESS, box=box.ROUNDED, expand=True)
    elif not hasattr(result, "__rich__"):
        # If the result is not Rich-renderable, convert it to a Rich Text object
        result = Panel(Text(str(result)), title=title or f"🔧 {tool_name}", border_style=STYLE_SUCCESS, box=box.ROUNDED, expand=True)
    
    # Print the result using the console
    console.print(result)

    if tool_name == "generate_and_execute_code":
        terminal.last_tool_result = result
        border = STYLE_SUCCESS if not isinstance(result, Text) or STYLE_ERROR not in str(getattr(result,'style','')) else STYLE_ERROR
        console.print(Panel(ensure_renderable(result), title=title or f"🔧 {tool_name}", border_style=border, box=box.ROUNDED, expand=True))
    else:
        # Existing tool command handling
        status_msg = f"Running {tool_name}..."
        actual_title = title or f"🔧 {tool_name}"
        with console.status(f"[{STYLE_DIM}]{status_msg}[/]"):
            result = await terminal.tool_manager._execute_tool(tool_name, args)
        terminal.last_tool_result = result
        border = STYLE_SUCCESS if not isinstance(result, Text) or STYLE_ERROR not in str(getattr(result,'style','')) else STYLE_ERROR
        console.print(Panel(ensure_renderable(result), title=actual_title, border_style=border, box=box.ROUNDED, expand=True)) 