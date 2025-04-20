import re
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Rich imports for prompts
from rich.prompt import Prompt, Confirm

# Style imports
from app.ui.styles import STYLE_ERROR, STYLE_INFO, STYLE_WARNING


async def interpret_natural_language(message: str, context: Dict[str, Any], console) -> Optional[Tuple[str, str]]:
    """Interpret natural language commands using regex and map them to tool calls.

    Args:
        message: The user's input message.
        context: The current application context dictionary.
        console: The Rich console instance for potential prompts.

    Returns:
        Optional[Tuple[str, str]]: (tool_name, args_string) if successful, else None.
    """
    lower_message = message.lower()
    original_message = message # Keep original case for extracted args like commands

    # --- File Operations ---
    # Create file: "create file X in Y", "make a file named X"
    # Simple create (empty file): "create (a )?file (called |named )?([\w\.\-\/ ]+)"
    match = re.search(r"create (?:a )?file (?:called |named )?([\w\.\-\/ ]+)", lower_message)
    if match:
        filepath = match.group(1).strip()

        # If no directory is specified, prompt the user or use context
        if not os.path.dirname(filepath):
            current_dir_context = context.get("current_dir")
            if current_dir_context:
                use_current = await Confirm.ask(f"Create file in current context directory ({current_dir_context})?", console=console)
                if use_current:
                    filepath = os.path.join(current_dir_context, filepath)
                else:
                    new_dir = Prompt.ask("Enter directory path to create file in", console=console)
                    filepath = os.path.join(os.path.expanduser(new_dir), filepath)
            else:
                new_dir = Prompt.ask("Enter directory path to create file in", console=console)
                filepath = os.path.join(os.path.expanduser(new_dir), filepath)

        # Ensure path separators are correct for OS
        filepath = str(Path(filepath))
        return "file", f"write {filepath} " # Write empty content

    # Create file in specific dir: "create file X in Y"
    match = re.search(r"create (?:a )?file (?:called |named )?'?([\w\.\-]+)'? in '?([\w\.\-\/ ]+)'?", lower_message)
    if match:
        filename = match.group(1).strip()
        directory = match.group(2).strip()
        filepath = str(Path(directory) / filename)
        return "file", f"write \"{filepath}\" \"\"" # Write empty content

    # Write to file: "write 'CONTENT' to (file) X"
    match = re.search(r"write '(.+?)' to (?:file )?([\w\.\-\/ ]+)", message) # Use original message for content
    if match:
        content = match.group(1)
        filepath = match.group(2).strip()
        filepath = str(Path(filepath)) # Normalize path
        # Escape quotes in content for the command string
        escaped_content = content.replace('"', '\\"')
        return "file", f"write \"{filepath}\" \"{escaped_content}\""

    # Read file: "read (file) X", "show (file) X"
    match = re.search(r"(?:read|show|cat) (?:file )?([\w\.\-\/ ]+)", lower_message)
    if match:
        filepath = match.group(1).strip()
        filepath = str(Path(filepath)) # Normalize path
        return "file", f"read \"{filepath}\""

    # List files: "list files (in X)", "ls (in X)"
    match = re.search(r"(?:list files|ls)(?: in)? ([\w\.\-\/ ]+)", lower_message)
    if match:
        path = match.group(1).strip()
        path = str(Path(path)) # Normalize path
        return "file", f"list \"{path}\""
    # Handle "list files" or "ls" without path -> current dir
    if lower_message in ["list files", "ls"]:
         return "file", "list ."

    # --- Shell Execution ---
    # Run command: "run (command) CMD", "execute CMD" (capture command with original casing)
    match = re.search(r"(?:run|execute) (?:command )?(.+)", original_message, re.IGNORECASE)
    if match:
        command = match.group(1).strip()
        # Remove surrounding quotes if present (e.g., run `ls -l`)
        if command.startswith(('`', '"', "'")) and command.endswith(('`', '"', "'")):
             command = command[1:-1]
        return "shell", command

    # --- Open Files/URLs ---
    # Open: "open X"
    match = re.search(r"open ([\w\.\-\/:]+)", lower_message) # Simple pattern for files/URLs
    if match:
        path_or_url = match.group(1).strip()
        # Basic check if it looks like a URL
        if not path_or_url.startswith(("http://", "https://")):
             path_or_url = str(Path(path_or_url)) # Treat as path if not URL like
        return "open", path_or_url

    # --- System Info ---
    if lower_message in ["system info", "show system info", "sys info", "check system status"]:
        return "sys_info", ""

    # --- Git Status ---
    if lower_message in ["git status", "check git status"]:
        # Potentially add path extraction later: "git status in <path>"
        return "git_status", "" # Default to current dir for now

    # --- Search ---
    # "search for X in Y"
    match = re.search(r"search for '(.+?)'(?: in)? ([\w\.\-\/ ]+)", message)
    if match:
         query = match.group(1)
         path = match.group(2).strip()
         return "search", f"\"{query}\" \"{path}\"" # Quote args

    # "find X in Y" (assuming file name search for now)
    match = re.search(r"find (?:file |files? )?'?([\w\.\-\*]+)'?(?: in)? ([\w\.\-\/ ]+)", lower_message)
    if match:
         query = match.group(1).strip()
         path = match.group(2).strip()
         return "search", f"\"{query}\" \"{path}\"" # Use search tool

    # --- Basic Context Example ---
    # "go to directory X", "cd X"
    match = re.search(r"(?:go to|cd)(?: directory)? ([\w\.\-\/ ]+)", lower_message)
    if match:
         new_dir = match.group(1).strip()
         try:
             resolved_dir = str(Path(new_dir).resolve())
             if Path(resolved_dir).is_dir():
                 # Update context, don't actually change dir
                 context["current_dir"] = resolved_dir
                 console.print(f"[{STYLE_INFO}]Context: Set current directory context to '{context['current_dir']}'[/]")
             else:
                 console.print(f"[{STYLE_WARNING}]Directory not found: {resolved_dir}[/]")
         except Exception as e:
             console.print(f"[{STYLE_ERROR}]Error resolving directory '{new_dir}': {e}[/]")
         # Return None as this isn't a direct tool call, just context update
         return None # Or potentially return ('file', f'list "{new_dir}"') ?

    # Add more interpretations here...

    return None # No interpretation matched 