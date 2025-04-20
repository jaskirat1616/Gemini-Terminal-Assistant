import json
from datetime import datetime
from typing import Any, Optional, Tuple
from pathlib import Path

# Rich imports (needed for _ensure_renderable)
from rich.text import Text
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.tree import Tree

# Style imports (needed for _ensure_renderable)
from app.ui.styles import STYLE_ERROR, STYLE_WARNING

def get_timestamp() -> str:
    """Get current timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_renderable(obj: Any) -> Any:
    """Ensure the object is directly renderable by Rich, otherwise convert to Text."""
    if isinstance(obj, (str, Text, Table, Syntax, Markdown, Tree)):
        return obj
    # If it's an error string from a tool, wrap it in Text with error style
    # Check style attribute existence before checking content
    style_attr = getattr(obj, 'style', '')
    is_error_text = isinstance(obj, Text) and (STYLE_ERROR in str(style_attr) or STYLE_WARNING in str(style_attr))

    if not is_error_text and isinstance(obj, str) and ("Error:" in obj or "Warning:" in obj or "⚠️" in obj):
         return Text(obj, style=STYLE_ERROR if "Error:" in obj else STYLE_WARNING)
    # Fallback for other types
    try:
        # Attempt to pretty-print if it looks like JSON
        if isinstance(obj, (dict, list)):
            return Text(json.dumps(obj, indent=2))
        return Text(str(obj))
    except Exception:
        # Ultimate fallback
        return Text(repr(obj))

def save_conversation(history: list, config_model: str, filename: str, console):
    """Save conversation to a file."""
    from app.ui.styles import STYLE_SUCCESS, STYLE_ERROR # Local import to avoid circular dependency if console is passed from terminal
    try:
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump({
                "model": config_model,
                "history": history
            }, f, indent=2)
        console.print(f"[{STYLE_SUCCESS}]Conversation saved to {filepath}[/]")
    except Exception as e:
        console.print(f"[{STYLE_ERROR}]Error saving conversation:[/{STYLE_ERROR}] {str(e)}")

def load_conversation(filename: str, console) -> Tuple[Optional[str], list]:
    """Load conversation from a file. Returns (model_name, history) or (None, []) on error."""
    from app.ui.styles import STYLE_SUCCESS, STYLE_ERROR, STYLE_INFO, STYLE_BORDER # Local import
    from rich.panel import Panel
    from rich.markdown import Markdown
    from config import AVAILABLE_MODELS # Need this to validate model

    filepath = Path(filename)
    if not filepath.exists():
         console.print(f"[{STYLE_ERROR}]Error: File not found: {filepath}[/{STYLE_ERROR}]")
         return None, []

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        loaded_model = data.get("model")
        loaded_history = data.get("history", [])
        model_to_set = None

        if loaded_model and loaded_model in AVAILABLE_MODELS:
            model_to_set = loaded_model # Return the model name to be set by the caller
            console.print(f"[{STYLE_INFO}]Model '{loaded_model}' found in loaded file.[/{STYLE_INFO}]")

        console.print(f"[{STYLE_SUCCESS}]Loaded conversation with {len(loaded_history)//2} messages from {filepath}[/{STYLE_SUCCESS}]")

        if loaded_history:
            console.print(f"[{STYLE_INFO}]Last message:[/]")
            last_exchange = loaded_history[-2:] if len(loaded_history) >= 2 else loaded_history[-1:]
            for item in reversed(last_exchange):
                 role = item.get("role", "unknown")
                 parts = item.get("parts", [""])[0]
                 title = "User" if role == "user" else "Gemini"
                 color = "green" if role == "user" else STYLE_BORDER
                 # Ensure parts is a string before passing to Markdown
                 md_content = str(parts) if parts is not None else ""
                 console.print(Panel(Markdown(md_content, style=""), title=title, border_style=color, expand=False, padding=(0,1)))

        return model_to_set, loaded_history

    except json.JSONDecodeError:
         console.print(f"[{STYLE_ERROR}]Error: Invalid JSON file: {filepath}[/{STYLE_ERROR}]")
         return None, []
    except Exception as e:
        console.print(f"[{STYLE_ERROR}]Error loading conversation:[/{STYLE_ERROR}] {str(e)}")
        return None, [] 