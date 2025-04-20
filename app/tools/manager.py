# tools.py

import os
import re
import sys
import json
import subprocess
import asyncio
import tempfile
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path
from datetime import datetime
import traceback
import platform
from rich.text import Text

from app.tools.file_tools import *
from app.tools.process_tools import *
from app.tools.system_tools import *

# Try importing optional dependencies and provide user-friendly errors if missing
try:
    import psutil
except ImportError:
    psutil = None # type: ignore

try:
    import pyperclip
except ImportError:
    pyperclip = None # type: ignore

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.markdown import Markdown
from rich import box # For panel boxes
from rich.prompt import Confirm

# Google AI Tool Imports
from google.generativeai.types import FunctionDeclaration, Tool
from google.protobuf.struct_pb2 import Struct

console = Console()

# Shared Style Constants (Can be centralized further if needed)
STYLE_SUCCESS = "green"
STYLE_ERROR = "bold red"
STYLE_WARNING = "yellow"
STYLE_INFO = "cyan"
STYLE_COMMAND = "bright_cyan"
STYLE_BORDER = "grey58"
STYLE_TITLE = "bold blue"

# Define available tools
AVAILABLE_TOOLS = {
    "file": {
        "description": "Read, write/overwrite, list directories, and search within files.",
        "usage": "file read|write|list|search <path> [content_to_write|search_pattern]"
    },
    "shell": {
        "description": "Execute shell commands. Use with caution.",
        "usage": "shell <command>"
    },
    "execute_code": {
        "description": "Execute Python code snippet. Use with caution.",
        "usage": "execute_code <python_code>"
    },
    "search_files": {
        "description": "Search for files by name or content.",
        "usage": "search_files <query> [path]"
    },
    "open": {
        "description": "Open a file or URL with the default application.",
        "usage": "open <path_or_url>"
    },
    "sys_info": {
        "description": "Get detailed system information.",
        "usage": "sys_info"
    },
    "clipboard": {
        "description": "Access clipboard contents (copy/paste).",
        "usage": "clipboard [text_to_copy]"
    },
    "diff": {
        "description": "Compare two files or texts (unified diff).",
        "usage": "diff <file1_or_text1> <file2_or_text2>"
    },
    "pip": {
        "description": "Manage Python packages (install/list/uninstall).",
        "usage": "pip install|list|uninstall <package_name>"
    },
    "git_status": {
        "description": "Get Git status for a directory.",
        "usage": "git_status [path]"
    },
    "lint": {
        "description": "Run code linters (flake8 for Python) on a file or directory.",
        "usage": "lint [path]"
    },
    "git_diff": {
        "description": "Show Git diff between two files/commits/branches.",
        "usage": "git_diff <file1> <file2>"
    },
    "ps": {
        "description": "List running processes.",
        "usage": "ps"
    },
    "git_log": {
        "description": "Show Git commit log for a repository.",
        "usage": "git_log [path] [--count=N]"
    },
    "find_large": {
        "description": "Find largest files in a directory.",
        "usage": "find_large [path] [--count=N]"
    },
    "ping": {
        "description": "Ping a network host.",
        "usage": "ping <host>"
    },
    "curl": {
        "description": "Fetch content from a URL using the curl command.",
        "usage": "curl <url>"
    },
    "get_current_datetime": {
        "description": "Get the current date and time.",
        "usage": "get_current_datetime"
    },
    "list_files": {
        "function": list_files,
        "description": "List files in a directory.",
        "usage": "list_files [directory]"
    },
    "get_system_stats": {
        "function": get_system_stats,
        "description": "Get system statistics like CPU and memory usage.",
        "usage": "get_system_stats"
    },
    "list_processes": {
        "function": list_processes,
        "description": "List running processes.",
        "usage": "list_processes"
    },
    "read_file_content": {
        "function": read_file_content,
        "description": "Read the content of a file.",
        "usage": "read_file_content <file_path>"
    },
    "generate_and_execute_code": {
        "function": generate_and_execute_code,
        "description": "Generate code based on a prompt and execute it.",
        "usage": "generate_and_execute_code <prompt>"
    },
}

# --- Tool Function Declarations for Gemini API ---

get_current_datetime_func = FunctionDeclaration(
    name="get_current_datetime",
    description="Get the current date and time.",
    parameters=None # No parameters needed
)

# --- Tool Objects List for Model ---
# This list will be passed to the GenerativeModel
GEMINI_TOOLS = [
    Tool(function_declarations=[get_current_datetime_func]),
    # Add other tool declarations here as they are created
]

class ToolManager:
    def __init__(self):
        """Initialize tool manager."""
        # Register tool handlers
        self.tools: Dict[str, Callable[[str], Any]] = {
            "file": self.file_tool,
            "shell": self.shell_tool,
            "execute_code": self.execute_code_tool,
            "search_files": self.search_files_tool,
            "open": self.open_tool,
            "sys_info": self.sys_info_tool,
            "clipboard": self.clipboard_tool,
            "diff": self.diff_tool,
            "pip": self.pip_tool,
            "git_status": self.git_status_tool,
            "lint": self.lint_tool,
            "git_diff": self.git_diff_tool,
            "ps": self.process_list_tool,
            "git_log": self.git_log_tool,
            "find_large": self.find_large_tool,
            "ping": self.ping_tool,
            "curl": self.curl_tool,
            "get_current_datetime": self.get_current_datetime_tool,
            "list_files": self.list_files_tool,
            "get_system_stats": self.get_system_stats_tool,
            "list_processes": self.list_processes_tool,
            "read_file_content": self.read_file_content_tool,
            "generate_and_execute_code": self.generate_and_execute_code_tool,
        }
        # Store API tool definitions
        self.api_tools = GEMINI_TOOLS
    
    def get_available_tools_for_display(self) -> Dict[str, Dict[str, str]]:
        """Get available tools with descriptions for user display (/tools command)."""
        return AVAILABLE_TOOLS

    def get_api_tools(self) -> List[Tool]:
        """Get the list of Tool objects for the Gemini API."""
        return self.api_tools
    
    async def check_for_tool_calls(self, message: str) -> Optional[Any]:
        """Check if message starts with a tool name and execute if it does."""
        for tool_name in self.tools:
            if message.lower().startswith(tool_name.lower() + " "):
                args_str = message[len(tool_name):].strip()
                console.print(f"🔧 Executing Tool: [{STYLE_COMMAND}]{tool_name}[/] with args: '{args_str[:100]}{'...' if len(args_str) > 100 else ''}'")
                return await self._execute_tool(tool_name, args_str)
        return None
    
    async def _execute_tool(self, tool_name: str, args: str) -> Any:
        """Execute a tool with the given arguments, handling errors."""
        tool_func = self.tools.get(tool_name)
        if not tool_func:
            return {"error": f"Tool not found: {tool_name}"}
        try:
            result = await tool_func(args)
            return result
        except Exception as e:
            return {"error": str(e)}

    async def file_tool(self, args: str) -> Any:
        """File operations: read, write, list, search.
        Usage: file read|write|list|search <path> [content_to_write|search_pattern]
        """
        parts = args.split(maxsplit=1)
        if not parts:
            return Text("🔧 Usage: file read|write|list|search <path> [content_to_write|search_pattern]", style=STYLE_ERROR)

        operation = parts[0].lower()
        op_args_str = parts[1] if len(parts) > 1 else ""

        if operation == "read":
            if not op_args_str:
                return Text("🔧 Usage: file read <path>", style=STYLE_ERROR)
            file_path = Path(op_args_str.strip())
            if not file_path.is_file():
                return Text(f"🔧 Error: File not found or is not a regular file: {file_path}", style=STYLE_ERROR)
            try:
                content = file_path.read_text()
                lang = Syntax.guess_lexer(file_path.name, code=content)
                syntax = Syntax(content, lang, theme="dracula", line_numbers=True, word_wrap=True)
                return Panel(syntax, title=f"📄 {file_path.name}", border_style=STYLE_BORDER, expand=False)
            except Exception as e:
                return Text(f"🔧 Error reading file {file_path}: {e}", style=STYLE_ERROR)

        elif operation == "write":
            write_parts = op_args_str.split(maxsplit=1)
            if len(write_parts) < 2:
                return Text("🔧 Usage: file write <path> <content>", style=STYLE_ERROR)
            file_path = Path(write_parts[0])
            content = write_parts[1]
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                return Text(f"✅ Content ({len(content)} chars) written to {file_path}", style=STYLE_SUCCESS)
            except Exception as e:
                return Text(f"🔧 Error writing to file {file_path}: {e}", style=STYLE_ERROR)

        elif operation == "list":
            dir_path = Path(op_args_str.strip()) if op_args_str else Path.cwd()
            if not dir_path.is_dir():
                return Text(f"🔧 Error: Directory not found or is not a directory: {dir_path}", style=STYLE_ERROR)
            try:
                tree = Tree(f"📁 [link file://{dir_path.resolve()}]{dir_path}", guide_style="bright_blue")
                items = sorted(list(dir_path.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
                for item in items:
                    if item.is_dir():
                        tree.add(f"📁 {item.name}/")
                    elif item.is_file():
                        try:
                            size = item.stat().st_size
                            size_str = self._format_size(size)
                            tree.add(f"📄 {item.name} ({size_str})")
                        except FileNotFoundError:
                            tree.add(f"❓ {item.name} (broken link?)")

                return tree
            except Exception as e:
                return Text(f"🔧 Error listing directory {dir_path}: {e}", style=STYLE_ERROR)

        elif operation == "search":
            search_parts = op_args_str.split(maxsplit=1)
            if len(search_parts) < 2:
                return Text("🔧 Usage: search_files <query> [directory_path]", style=STYLE_ERROR)

            query = search_parts[0]
            path_str = search_parts[1] if len(search_parts) > 1 else "."
            path = Path(path_str)

            if not path.is_dir():
                return Text(f"🔧 Error: Search path is not a valid directory: {path}", style=STYLE_ERROR)

            try:
                name_matches = []
                content_matches = []
                limit = 50

                for file_path in path.rglob(f"*{query}*"):
                    if file_path.is_file():
                        name_matches.append(str(file_path.relative_to(path)))
                    if len(name_matches) >= limit: break
                if len(name_matches) >= limit:
                    name_matches.append(f"... (stopped after {limit} name matches)")

                text_extensions = {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".sh"}
                for file_path in path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                        try:
                            content = file_path.read_text(errors='ignore')
                            if query in content:
                                content_matches.append(str(file_path.relative_to(path)))
                            if len(content_matches) >= limit: break
                        except Exception:
                            continue
                    if len(content_matches) >= limit: break
                if len(content_matches) >= limit:
                    content_matches.append(f"... (stopped after {limit} content matches)")

                output = [f"🔍 Glob Search Results for '{query}' in '{path}':"]
                if name_matches:
                    output.append("\n📄 Files matching name:")
                    output.extend([f"  - {match}" for match in name_matches])
                if content_matches:
                    output.append("\n📄 Files matching content (basic text search):")
                    output.extend([f"  - {match}" for match in content_matches])

                if not name_matches and not content_matches:
                    output.append("\nNo matches found.")

                return Text("\n".join(output), style=STYLE_INFO)
            except Exception as e:
                return Text(f"🔧 Error searching files: {e}", style=STYLE_ERROR)

        else:
            return Text(f"🔧 Error: Unknown file operation '{operation}'. Use read|write|list|search.", style=STYLE_ERROR)

    async def shell_tool(self, command: str) -> Text:
        """Executes a shell command. Use with extreme caution."""
        if not command:
            return Text("🔧 Error: No command provided to shell.", style=STYLE_ERROR)
        try:
            returncode, stdout, stderr = await self._run_subprocess_shell(command, timeout=60)
            output = ""
            if stdout:
                output += f"[bold]Output:[/]\n{stdout.strip()}\n"
            if stderr:
                output += f"[bold {STYLE_ERROR}]Errors:[/]\n{stderr.strip()}\n"

            if not output.strip() and returncode == 0:
                return Text("✅ Command executed successfully (no output).", style=STYLE_SUCCESS)
            elif returncode != 0:
                output += f"[bold {STYLE_ERROR}]Command exited with status {returncode}[/]"
                return Panel(Text(output.strip()), title=f"Shell: '{command[:30]}{'...' if len(command)>30 else ''}'", border_style=STYLE_ERROR, expand=False)
            else:
                return Panel(Text(output.strip()), title=f"Shell: '{command[:30]}{'...' if len(command)>30 else ''}'", border_style=STYLE_BORDER, expand=False)

        except TimeoutError as e:
            return Text(f"⏰ Error executing shell command: {e}", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error executing shell command: {e}", style=STYLE_ERROR)

    async def execute_code_tool(self, code: str) -> Any:
        """Execute Python code and return the result."""
        try:
            # Create a temporary file to store the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            # Execute the code using the shell
            command = f"python {temp_file_path}"
            returncode, stdout, stderr = await self._run_subprocess_shell(command)
            
            # Clean up the temporary file
            import os
            os.remove(temp_file_path)
            
            # Return the execution result
            return {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode
            }
        except Exception as e:
            return {"error": str(e)}

    async def search_files_tool(self, args: str) -> Text:
        """Search for files by name or content using glob."""
        parts = args.split(maxsplit=1)
        if not parts:
            return Text("🔧 Usage: search_files <query> [directory_path]", style=STYLE_ERROR)
        query = parts[0]
        path_str = parts[1] if len(parts) > 1 else "."
        path = Path(path_str)

        if not path.is_dir():
            return Text(f"🔧 Error: Search path is not a valid directory: {path}", style=STYLE_ERROR)

        try:
            name_matches = []
            content_matches = []
            limit = 50

            for file_path in path.rglob(f"*{query}*"):
                if file_path.is_file():
                    name_matches.append(str(file_path.relative_to(path)))
                if len(name_matches) >= limit: break
            if len(name_matches) >= limit:
                name_matches.append(f"... (stopped after {limit} name matches)")

            text_extensions = {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".sh"}
            for file_path in path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                    try:
                        content = file_path.read_text(errors='ignore')
                        if query in content:
                            content_matches.append(str(file_path.relative_to(path)))
                        if len(content_matches) >= limit: break
                    except Exception:
                        continue
                if len(content_matches) >= limit: break
            if len(content_matches) >= limit:
                content_matches.append(f"... (stopped after {limit} content matches)")

            output = [f"🔍 Glob Search Results for '{query}' in '{path}':"]
            if name_matches:
                output.append("\n📄 Files matching name:")
                output.extend([f"  - {match}" for match in name_matches])
            if content_matches:
                output.append("\n📄 Files matching content (basic text search):")
                output.extend([f"  - {match}" for match in content_matches])

            if not name_matches and not content_matches:
                output.append("\nNo matches found.")

            return Text("\n".join(output), style=STYLE_INFO)
        except Exception as e:
            return Text(f"🔧 Error searching files: {e}", style=STYLE_ERROR)

    async def sys_info_tool(self, args: str) -> Any:
        """Display system information using psutil."""
        if not psutil:
            raise ImportError("psutil is required for sys_info. Please install it.")

        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            cpu_freq = psutil.cpu_freq()

            system_info = {
                "System": f"{platform.system()} {platform.release()}",
                "Architecture": f"{platform.machine()} ({platform.processor()})",
                "Hostname": platform.node(),
                "Python": platform.python_version(),
                "CPU Cores": f"{psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical",
                "CPU Freq": f"{cpu_freq.current:.0f} MHz (Max: {cpu_freq.max:.0f} MHz)" if cpu_freq else "N/A",
                "CPU Usage": f"{psutil.cpu_percent(interval=0.1)}%",
                "RAM Total": self._format_size(mem.total),
                "RAM Available": self._format_size(mem.available),
                "RAM Used": f"{mem.percent}%",
                "Disk Total": self._format_size(disk.total),
                "Disk Used": f"{self._format_size(disk.used)} ({disk.percent}%)",
                "Boot Time": boot_time.strftime('%Y-%m-%d %H:%M:%S')
            }

            table = Table(title="🖥️ System Information", box=box.ROUNDED, border_style=STYLE_BORDER, show_header=False)
            table.add_column("Property", style=STYLE_INFO, no_wrap=True)
            table.add_column("Value", style="white")

            for key, value in system_info.items():
                table.add_row(key, str(value))

            return table
        except Exception as e:
            return Text(f"🔧 Error getting system information: {e}", style=STYLE_ERROR)

    async def clipboard_tool(self, args: str) -> Text:
        """Copy text to or paste text from the system clipboard."""
        if not pyperclip:
            raise ImportError("pyperclip is required for clipboard access. Please install it.")

        try:
            if args:
                await asyncio.to_thread(pyperclip.copy, args)
                preview = args[:80] + ('...' if len(args) > 80 else '')
                return Text(f"✅ Copied to clipboard:\n'{preview}'", style=STYLE_SUCCESS)
            else:
                content = await asyncio.to_thread(pyperclip.paste)
                if not content:
                    return Text("📋 Clipboard is empty.", style=STYLE_INFO)
                return Panel(Text(content), title="📋 Clipboard Content", border_style=STYLE_BORDER, expand=False)
        except Exception as e:
            return Text(f"🔧 Error accessing clipboard: {e}. (Is a display environment available?)", style=STYLE_ERROR)

    async def diff_tool(self, args: str) -> Any:
        """Compare two files or texts using unified diff."""
        try:
            import difflib
        except ImportError:
            return Text("🔧 Error: `difflib` module not found (should be standard).", style=STYLE_ERROR)

        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            return Text("🔧 Usage: diff <file1_or_text1> <file2_or_text2>", style=STYLE_ERROR)

        source1, source2 = parts[0], parts[1]
        path1, path2 = Path(source1), Path(source2)
        text1, text2 = None, None
        label1, label2 = source1, source2

        try:
            if path1.is_file():
                text1 = path1.read_text().splitlines()
                label1 = str(path1)
            else:
                text1 = source1.splitlines()

            if path2.is_file():
                text2 = path2.read_text().splitlines()
                label2 = str(path2)
            else:
                text2 = source2.splitlines()

            diff = difflib.unified_diff(
                text1,
                text2,
                fromfile=label1,
                tofile=label2,
                lineterm=''
            )

            diff_text = '\n'.join(diff)
            syntax = Syntax(diff_text, "diff", theme="dracula", line_numbers=False, word_wrap=True)
            return Panel(syntax, title=f"↔️ Diff: {label1} vs {label2}", border_style=STYLE_BORDER, expand=False)

        except Exception as e:
            return Text(f"🔧 Error generating diff: {e}", style=STYLE_ERROR)

    async def pip_tool(self, args: str) -> Text:
        """Manage Python packages using pip (list, install, uninstall)."""
        parts = args.split(maxsplit=1)
        if not parts:
            return Text("🔧 Usage: pip list | install <pkg> | uninstall <pkg>", style=STYLE_ERROR)

        operation = parts[0].lower()
        package_args = parts[1] if len(parts) > 1 else ""

        pip_exec = [sys.executable, "-m", "pip"]

        if operation == "list":
            command = pip_exec + ["list"]
            timeout = 30
            action_desc = "listing packages"
        elif operation == "install":
            if not package_args: return Text("🔧 Usage: pip install <package_name>", style=STYLE_ERROR)
            command = pip_exec + ["install", package_args.strip()]
            timeout = 180
            action_desc = f"installing '{package_args.strip()}'"
        elif operation == "uninstall":
            if not package_args: return Text("🔧 Usage: pip uninstall <package_name>", style=STYLE_ERROR)
            command = pip_exec + ["uninstall", "-y", package_args.strip()]
            timeout = 60
            action_desc = f"uninstalling '{package_args.strip()}'"
        else:
            return Text(f"🔧 Error: Unknown pip operation '{operation}'. Use list|install|uninstall.", style=STYLE_ERROR)

        try:
            console.print(f"Running pip {action_desc}...", style=STYLE_INFO)
            returncode, stdout, stderr = await self._run_subprocess(command, timeout=timeout)

            output = f"Pip {action_desc}:\n"
            if stdout: output += f"\nOutput:\n{stdout.strip()}\n"
            if stderr: output += f"\nErrors/Warnings:\n{stderr.strip()}\n"

            if returncode == 0:
                return Panel(Text(output.strip()), title=f"Pip {operation.capitalize()} Result", border_style=STYLE_SUCCESS, expand=False)
            else:
                output += f"\nPip command failed with exit code {returncode}."
                return Panel(Text(output.strip()), title=f"Pip {operation.capitalize()} Failed", border_style=STYLE_ERROR, expand=False)

        except TimeoutError as e:
            return Text(f"⏰ Pip operation timed out: {e}", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error running pip {action_desc}: {e}", style=STYLE_ERROR)

    async def open_tool(self, path_or_url: str) -> Text:
        """Open a file or URL using the default system application."""
        print(f"DEBUG: open_tool called with path_or_url: {path_or_url}")
        if not path_or_url:
            return Text("🔧 Error: Missing file path or URL to open.", style=STYLE_ERROR)

        is_url = path_or_url.startswith(("http://", "https://", "file://"))
        path = Path(path_or_url)

        target_to_open = path_or_url

        print(f"DEBUG: is_url: {is_url}, path: {path}, target_to_open: {target_to_open}")

        if not is_url and not path.exists():
            # File not found, search for similar files
            similar_files = await self._find_similar_files(path_or_url)
            if similar_files:
                self.console.print(f"File not found: '{path_or_url}'. Did you mean one of these?", style=STYLE_WARNING)
                for idx, filepath in enumerate(similar_files):
                    self.console.print(f"  {idx + 1}. {filepath}")

                selection_index = await self._get_user_selection(f"Choose a file to open (1-{len(similar_files)}, or 0 to cancel): ", len(similar_files))
                if selection_index is not None:
                    if selection_index == -1: # User chose to cancel (input '0')
                        return Text("Operation cancelled by user.", style=STYLE_INFO)
                    target_to_open = similar_files[selection_index]
                    path = Path(target_to_open) # Update path to the selected file
                else:
                    return Text("Invalid selection. Operation cancelled.", style=STYLE_ERROR)
            else:
                # If no similar files, try searching by filename
                filename_search_results = await self._search_by_filename(path_or_url)
                if filename_search_results:
                    self.console.print(f"File not found at '{path_or_url}'. Found these files with similar names:", style=STYLE_WARNING)
                    for idx, filepath in enumerate(filename_search_results):
                        self.console.print(f"  {idx + 1}. {filepath}")

                    selection_index = await self._get_user_selection(f"Choose a file to open (1-{len(filename_search_results)}, or 0 to cancel): ", len(filename_search_results))
                    if selection_index is not None:
                        if selection_index == -1: # User chose to cancel (input '0')
                            return Text("Operation cancelled by user.", style=STYLE_INFO)
                        target_to_open = filename_search_results[selection_index]
                        path = Path(target_to_open) # Update path to the selected file
                    else:
                        return Text("Invalid selection. Operation cancelled.", style=STYLE_ERROR)
                else:
                    # Ask user if they want to search for similar names
                    search_computer = await self._ask_user_confirm(f"File '{path_or_url}' not found. Search computer for similar filenames?", default_answer=True)
                    if search_computer:
                        filename_search_results_computer = await self._search_by_filename_computer_wide(path_or_url)
                        if filename_search_results_computer:
                            self.console.print(f"File not found at '{path_or_url}'. Found these files with similar names on your computer:", style=STYLE_WARNING)
                            for idx, filepath in enumerate(filename_search_results_computer):
                                self.console.print(f"  {idx + 1}. {filepath}")

                            selection_index = await self._get_user_selection(f"Choose a file to open (1-{len(filename_search_results_computer)}, or 0 to cancel): ", len(filename_search_results_computer))
                            if selection_index is not None:
                                if selection_index == -1: # User chose to cancel (input '0')
                                    return Text("Operation cancelled by user.", style=STYLE_INFO)
                                target_to_open = filename_search_results_computer[selection_index]
                                path = Path(target_to_open) # Update path to the selected file
                            else:
                                return Text("Invalid selection. Operation cancelled.", style=STYLE_ERROR)
                        else:
                            print(f"DEBUG: File or directory not found: {path}")
                            return Text(f"🔧 Error: File or directory not found: {path}", style=STYLE_ERROR)
                    else:
                        print(f"DEBUG: File or directory not found: {path}")
                        return Text(f"🔧 Error: File or directory not found: {path}", style=STYLE_ERROR)

        try:
            system = platform.system()
            command: Optional[List[str]] = None
            shell_exec = False

            if system == "Windows":
                command = ["start", "", target_to_open]
                print(f"DEBUG: Windows open command: {command}")
                ret, out, err = await self._run_subprocess(command) # Use helper
            elif system == "Darwin": # macOS
                command = ["open", target_to_open]
                print(f"DEBUG: macOS open command: {command}")
                ret, out, err = await self._run_subprocess(command) # Use helper
            else: # Linux and other Unix-like
                command = ["xdg-open", target_to_open]
                print(f"DEBUG: Linux open command: {command}")
                ret, out, err = await self._run_subprocess(command) # Use helper

            print(f"DEBUG: Subprocess finished, ret: {ret}")
            if ret != 0:
                 return Text(f"🔧 Error opening '{target_to_open}': {err.strip()}", style=STYLE_ERROR)
            else:
                return Text(f"✅ Attempted to open '{target_to_open}'.", style=STYLE_SUCCESS)

        except FileNotFoundError:
            print(f"DEBUG: FileNotFoundError")
            return Text(f"🔧 Error: Command not found (likely 'open', 'start', or 'xdg-open'). Cannot open '{target_to_open}'.", style=STYLE_ERROR)
        except Exception as e:
            print(f"DEBUG: Exception: {e}")
            return Text(f"🔧 Error opening '{target_to_open}': {str(e)}", style=STYLE_ERROR)

    async def _find_similar_files(self, path_or_url: str) -> List[str]:
        """Find similar files on the system."""
        path = Path(path_or_url)
        similar_files = []
        for root, _, files in os.walk(Path.cwd()):
            for file in files:
                if path.name.lower() in file.lower():
                    similar_files.append(str(Path(root) / file))
        return similar_files

    async def _search_by_filename(self, filename: str) -> List[str]:
        """Search for files by filename in common user directories."""
        search_dirs = [Path.home(), Path.home() / "Documents", Path.home() / "Downloads", Path.home() / "Desktop"] # You can customize these
        found_files = []
        for search_dir in search_dirs:
            for root, _, files in os.walk(search_dir):
                for file in files:
                    if filename.lower() == file.lower(): # Case-insensitive filename match
                        found_files.append(str(Path(root) / file))
        return found_files

    async def _search_by_filename_computer_wide(self, filename: str) -> List[str]:
        """Search for files by filename across the entire computer (more extensive search)."""
        found_files = []
        for root, _, files in os.walk(Path.home().parent): # Start search from the parent of home directory to cover more of the computer
            for file in files:
                if filename.lower() == file.lower(): # Case-insensitive filename match
                    found_files.append(str(Path(root) / file))
        return found_files

    async def _get_user_selection(self, prompt: str, max_selection: int) -> Optional[int]:
        """Prompt the user to select an option."""
        console = Console()
        while True:
            selection = await asyncio.to_thread(console.input, prompt)
            try:
                selection = int(selection)
                if selection == 0: # Allow 0 to cancel
                    return -1 # Signal for cancel
                if 1 <= selection <= max_selection:
                    return selection - 1
                else:
                    console.print(f"🔧 Error: Selection must be between 1 and {max_selection} or 0 to cancel.", style=STYLE_ERROR)
            except ValueError:
                console.print("🔧 Error: Please enter a valid number.", style=STYLE_ERROR)

    async def _ask_user_confirm(self, prompt: str, default_answer: bool = True) -> bool:
        """Ask user for confirmation using rich.Confirm."""
        console = Console()
        return await asyncio.to_thread(Confirm.ask, prompt, console=console, default=default_answer)

    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human-readable format.
        
        Args:
            size_bytes: Size in bytes
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    async def git_status_tool(self, path_str: str) -> Any:
        """Get Git repository status."""
        path = Path(path_str.strip()) if path_str.strip() else Path.cwd()

        if not path.is_dir():
            return Text(f"🔧 Error: Not a valid directory: {path}", style=STYLE_ERROR)

        try:
            # Check if it's a git repository *root* or subdirectory first
            git_dir_check_cmd = ["git", "rev-parse", "--is-inside-work-tree"]
            # Run in the target directory
            ret_check, out_check, err_check = await self._run_subprocess(git_dir_check_cmd, cwd=str(path), timeout=10) # Short timeout for check

            if ret_check != 0 or out_check.strip() != 'true':
                # Handle cases where it's not a git repo or git command fails slightly differently
                if "not a git repository" in err_check.lower():
                    return Text(f"⚠️ Not a Git repository: {path}", style=STYLE_WARNING)
                else: # Other git error during check
                    return Text(f"🔧 Error checking Git repository status for {path}: {err_check.strip()}", style=STYLE_ERROR)

            # If the check passed, proceed to get status
            command = ["git", "status", "--porcelain=v1"] # v1 provides untracked files too
            returncode, stdout, stderr = await self._run_subprocess(command, cwd=str(path), timeout=15)

            if returncode != 0:
                return Text(f"🔧 Error getting Git status for {path}: {stderr.strip()}", style=STYLE_ERROR)

            status_output = stdout.strip()

            if not status_output:
                return Text(f"✅ Git status for '{path.name}': Clean working directory.", style=STYLE_SUCCESS)

            # Parse porcelain v1 output
            status_tree = Tree(f"🌲 Git Status: '{path.name}'", guide_style="bright_blue")
            status_map = {
                'M': ('📝', 'Modified', 'yellow'),
                'A': ('✅', 'Added', 'green'),
                'D': ('❌', 'Deleted', 'red'),
                'R': ('➡️', 'Renamed', 'cyan'),
                'C': ('📄', 'Copied', 'blue'),
                'U': ('🔥', 'Unmerged', 'bold red'),
                '?': ('❓', 'Untracked', 'grey50'), # Dimmer grey
                '!': ('🙈', 'Ignored', 'dim'), # Very dim
            }

            staged_changes = Tree("Staged Changes")
            unstaged_changes = Tree("Unstaged Changes")
            untracked_files = Tree("Untracked Files")
            has_staged = has_unstaged = has_untracked = False

            for line in status_output.splitlines():
                 if not line: continue
                 xy = line[:2] # Status codes (index and worktree)
                 filepath = line[3:] # File path (can contain spaces)

                 # Handle renamed/copied files format "R  orig -> new"
                 if ' -> ' in filepath:
                     orig_path, new_path = filepath.split(' -> ', 1)
                     display_path = f"{orig_path} -> {new_path}"
                 else:
                     display_path = filepath

                 index_status = xy[0]
                 worktree_status = xy[1]

                 # Staged changes (based on index status X)
                 if index_status != ' ' and index_status != '?':
                      icon, desc, color = status_map.get(index_status, ('❓', 'Unknown', 'white'))
                      staged_changes.add(f"{icon} [{color}]{desc}[/]: {display_path}")
                      has_staged = True

                 # Unstaged changes (based on worktree status Y)
                 if worktree_status != ' ' and worktree_status != '?':
                      icon, desc, color = status_map.get(worktree_status, ('❓', 'Unknown', 'white'))
                      # Avoid double listing if staged and unstaged are same type but different content (e.g. MM)
                      if index_status == ' ' or index_status == '?': # Only add if not already covered by staged
                          unstaged_changes.add(f"{icon} [{color}]{desc}[/]: {display_path}")
                          has_unstaged = True
                      elif index_status != worktree_status: # e.g., AM (Added then Modified)
                          # Represent the worktree state change distinctly
                          unstaged_changes.add(f"{icon} [{color}]{desc}[/] (unstaged): {display_path}")
                          has_unstaged = True

                 # Untracked files (XY == '??')
                 if xy == '??':
                     icon, desc, color = status_map.get('?', ('❓', 'Untracked', 'grey50'))
                     untracked_files.add(f"{icon} [{color}]{desc}[/]: {display_path}")
                     has_untracked = True

                 # Ignored files could be added here if using 'git status --porcelain=v2 --ignored'

            # Add sub-trees only if they have content
            if has_staged: status_tree.add(staged_changes)
            if has_unstaged: status_tree.add(unstaged_changes)
            if has_untracked: status_tree.add(untracked_files)

            return status_tree

        except FileNotFoundError:
            # This catches if 'git' command itself is not found
            return Text("🔧 Error: Git command not found. Is Git installed and in PATH?", style=STYLE_ERROR)
        except Exception as e:
            # Catch errors during the subprocess execution or status parsing
            return Text(f"🔧 Error processing Git status for {path}: {e}", style=STYLE_ERROR)

    async def lint_tool(self, path_str: str) -> Any: # Returns Text or Table
        """Run code linter (flake8 for Python) on a file or directory.

        Args:
            path_str: Path to file or directory to lint
        """
        path = Path(path_str) if path_str else Path.cwd()

        try:
            if not path.exists():
                return Text(f"🔧 Error: Path not found: {path}", style=STYLE_ERROR)

            if path.is_file() and path.suffix.lower() != ".py":
                return Text("⚠️ Warning: Lint tool is optimized for Python files. Results may vary for other file types.", style=STYLE_WARNING)

            command = ["flake8", str(path)] # Run flake8
            returncode, stdout, stderr = await self._run_subprocess(command, timeout=60)

            if returncode == 0: # flake8 returns 0 even with warnings/errors
                output = stdout.decode().strip()
                if not output:
                    return Text(f"✅ Linting passed for '{path}'. No issues found.", style=STYLE_SUCCESS)
                else:
                    # Format linting issues with Rich Table
                    lint_table = Table(title=f"🔬 Linting Issues for '{path}'", box=box.ROUNDED, border_style=STYLE_WARNING, show_header=True, header_style="bold magenta")
                    lint_table.add_column("Location", style="cyan", width=20)
                    lint_table.add_column("Code", style="yellow", width=7)
                    lint_table.add_column("Message")
                    for line in output.splitlines():
                        parts = line.split(":", 3) # Split into file:line:column:message
                        if len(parts) == 4:
                            loc, lnum, cnum, msg = parts
                            code_match = re.search(r'\b([A-Z]+\d+)\b', msg) # Extract code like E501
                            code = code_match.group(1) if code_match else "N/A"
                            lint_table.add_row(f"{Path(loc).name}:{lnum}:{cnum}", code, msg.strip())
                        else: # Fallback for unexpected output format
                            lint_table.add_row("N/A", "N/A", line) # Just display as is
                    return lint_table

            else: # Real error with flake8 itself
                error_msg = stderr.decode()
                return Text(f"🔧 Error running linter: {error_msg}", style=STYLE_ERROR)

        except FileNotFoundError:
            return Text("🔧 Error: flake8 not found. Make sure flake8 is installed and in your PATH. You can install it with: pip install flake8", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error during linting: {str(e)}", style=STYLE_ERROR)

    async def git_diff_tool(self, args: str) -> Any: # Returns Text or Panel
        """Show Git diff between two files.

        Args:
            args: Two file paths separated by space.
        """
        files = args.split()
        if len(files) != 2:
            return Text("🔧 Error: Please provide two file paths to compare (e.g., git_diff file1 file2).", style=STYLE_ERROR)

        file1_path = Path(files[0])
        file2_path = Path(files[1])

        if not file1_path.exists() or not file2_path.exists():
            return Text(f"🔧 Error: One or both files not found: {file1_path}, {file2_path}", style=STYLE_ERROR)

        try:
            command = ["git", "diff", "--no-index", "--", str(file1_path), str(file2_path)] # --no-index for files outside git repo
            returncode, stdout, stderr = await self._run_subprocess(command)

            if returncode == 0:
                diff_output = stdout.decode().strip()
                if not diff_output:
                    return Text(f"✅ No differences found between '{file1_path}' and '{file2_path}'.", style=STYLE_SUCCESS)
                else:
                    # Use Rich Syntax to highlight diff
                    syntax = Syntax(diff_output, "diff", theme="dracula", line_numbers=True, word_wrap=True)
                    return Panel(syntax, title=f"↔️ Diff: {file1_path} vs {file2_path}", border_style=STYLE_INFO, expand=True)
            else:
                error_msg = stderr.decode()
                return Text(f"🔧 Error getting Git diff: {error_msg}", style=STYLE_ERROR)

        except FileNotFoundError:
            return Text("🔧 Error: Git command not found. Make sure Git is installed and in your PATH.", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error during git diff: {str(e)}", style=STYLE_ERROR)

    async def process_list_tool(self, args: str) -> Any: # Returns Text or Table
        """List running processes using psutil.

        Args:
            args: Not used.
        """
        if not psutil:
            raise ImportError("psutil") # Raise standard error

        try:
            # Get process info efficiently
            processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'cmdline', 'create_time']))

            # Sort processes, e.g., by memory or cpu usage descending
            processes.sort(key=lambda p: p.info.get('memory_percent', 0), reverse=True)

            process_table = Table(title="📊 Running Processes", box=box.ROUNDED, border_style=STYLE_INFO, expand=True)
            process_table.add_column("PID", style=STYLE_COMMAND, justify="right", no_wrap=True)
            process_table.add_column("User", style="cyan", max_width=15, overflow="ellipsis")
            process_table.add_column("CPU %", style="magenta", justify="right")
            process_table.add_column("MEM%", style="blue", justify="right")
            # process_table.add_column("Started", style="dim", justify="right") # Optional: start time
            process_table.add_column("Name", style="green", max_width=30, overflow="ellipsis")
            process_table.add_column("Command Line", style="dim", no_wrap=False, overflow="ellipsis", min_width=30) # Allow wrapping

            for proc in processes[:50]: # Limit output to top 50 processes
                try:
                    info = proc.info
                    # Handle potential None values gracefully
                    pid = info.get('pid', 'N/A')
                    user = info.get('username', 'N/A') or 'N/A' # Ensure not None
                    cpu = info.get('cpu_percent', 0.0)
                    mem = info.get('memory_percent', 0.0)
                    # started = datetime.fromtimestamp(info.get('create_time', 0)).strftime('%H:%M:%S') if info.get('create_time') else 'N/A'
                    name = info.get('name', 'N/A') or 'N/A'
                    cmdline = " ".join(info.get('cmdline', [])) if info.get('cmdline') else ""

                    process_table.add_row(
                        str(pid),
                        user,
                        f"{cpu:.1f}",
                        f"{mem:.1f}",
                        # started,
                        name,
                        cmdline
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass # Ignore processes we can't access

            if not processes:
                 return Text("No processes found (or unable to list any).", style=STYLE_WARNING)

            return process_table

        except Exception as e:
            return Text(f"🔧 Error getting process list: {str(e)}", style=STYLE_ERROR)

    # --- New Tools ---

    async def git_log_tool(self, args: str) -> Any: # Returns Text or Panel
        """Show Git commit log."""
        parts = args.split()
        path_str = "."
        count = 15 # Default number of commits
        for part in parts:
            if part.startswith("--count="):
                try:
                    count = int(part.split("=")[1])
                except (ValueError, IndexError):
                    return Text("🔧 Error: Invalid count value. Use --count=N", style=STYLE_ERROR)
            elif not part.startswith("--"):
                path_str = part # Assume it's the path

        path = Path(path_str)
        try:
            if not path.is_dir(): return Text(f"🔧 Error: Not a directory: {path}", style=STYLE_ERROR)
            if not (path / ".git").exists(): return Text(f"⚠️ Warning: Not a Git repository: {path}", style=STYLE_WARNING)

            # Use a pretty format for easier parsing or just display formatted output
            # format_str = "%C(auto)%h %s %C(dim cyan)(%cr) <%an>%d%C(reset)" # Example pretty format
            command = ["git", "log", f"--max-count={count}", "--color=always"] # Keep colors
            returncode, stdout, stderr = await self._run_subprocess(command, cwd=path)

            if returncode != 0:
                return Text(f"🔧 Error getting Git log: {stderr}", style=STYLE_ERROR)

            log_output = stdout.strip()
            if not log_output:
                return Text(f"📜 No commits found in '{path.name}'.", style=STYLE_INFO)

            # Use Syntax with 'ansi' lexer to preserve Git's colors
            syntax = Syntax(log_output, "ansi", theme="default", background_color="default", word_wrap=True)
            return Panel(syntax, title=f"📜 Git Log: '{path.name}' (Last {count})", border_style=STYLE_INFO, expand=True)

        except FileNotFoundError:
             return Text("🔧 Error: Git command not found.", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error getting Git log: {e}", style=STYLE_ERROR)

    async def find_large_tool(self, args: str) -> Any: # Returns Text or Table
        """Find largest files in a directory."""
        parts = args.split()
        path_str = "."
        count = 10 # Default number of files
        for part in parts:
            if part.startswith("--count="):
                try:
                    count = int(part.split("=")[1])
                except (ValueError, IndexError):
                    return Text("🔧 Error: Invalid count value. Use --count=N", style=STYLE_ERROR)
            elif not part.startswith("--"):
                path_str = part

        path = Path(path_str)
        if not path.is_dir():
            return Text(f"🔧 Error: Not a directory: {path}", style=STYLE_ERROR)

        try:
            files = []
            # Walk through directory, handling potential permission errors
            for root, _, filenames in os.walk(path, onerror=lambda e: print(f"Permission error: {e}", file=sys.stderr)):
                for filename in filenames:
                    try:
                        filepath = Path(root) / filename
                        if filepath.is_file(): # Avoid symlinks pointing to non-files etc.
                            files.append((filepath, filepath.stat().st_size))
                    except (FileNotFoundError, PermissionError):
                        continue # Skip files we can't access

            # Sort by size descending and take top N
            large_files = sorted(files, key=lambda x: x[1], reverse=True)[:count]

            if not large_files:
                return Text(f"No files found in '{path}'.", style=STYLE_INFO)

            table = Table(title=f"🐘 Largest Files: '{path.name}' (Top {count})", box=box.ROUNDED, border_style=STYLE_INFO, expand=True)
            table.add_column("Size", style="magenta", justify="right", no_wrap=True)
            table.add_column("File Path", style="green")

            for file_path, size in large_files:
                relative_path = file_path.relative_to(path) # Show relative path
                table.add_row(self._format_size(size), str(relative_path))

            return table

        except Exception as e:
            return Text(f"🔧 Error finding large files: {e}", style=STYLE_ERROR)

    async def ping_tool(self, host: str) -> Text:
        """Ping a network host."""
        if not host:
            return Text("🔧 Error: No host provided to ping.", style=STYLE_ERROR)

        # Use system ping command
        system = platform.system()
        if system == "Windows":
            command = ["ping", "-n", "4", host] # 4 pings on Windows
        else: # Linux/macOS
            command = ["ping", "-c", "4", host] # 4 pings

        try:
            returncode, stdout, stderr = await self._run_subprocess(command, timeout=10) # 10s timeout for ping

            output = f"[bold]Ping Results for {host}:[/]\n\n"
            output += stdout.strip()
            if stderr.strip():
                 output += f"\n\n[bold red]Errors:[/]\n{stderr.strip()}"

            # Check return code for success/failure (ping often exits non-zero on failure)
            if returncode == 0:
                 return Text(output, style=STYLE_SUCCESS)
            else:
                 return Text(output, style=STYLE_WARNING) # Use warning for failed ping, not error

        except FileNotFoundError:
             return Text("🔧 Error: 'ping' command not found. Please ensure it's installed.", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error running ping: {e}", style=STYLE_ERROR)

    async def curl_tool(self, url: str) -> Any: # Returns Text or Panel
        """Fetch content from a URL using the curl command."""
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return Text("🔧 Error: Invalid or missing URL. Must start with http:// or https://", style=STYLE_ERROR)

        # Use system curl command for simplicity and power
        # Flags: -s (silent), -S (show error), -L (follow redirects)
        command = ["curl", "-s", "-S", "-L", url]

        try:
            # Timeout needs to be longer for network requests
            returncode, stdout, stderr = await self._run_subprocess(command, timeout=30)

            if returncode != 0:
                return Text(f"🔧 Error fetching URL with curl: {stderr.strip() or 'Unknown error'}", style=STYLE_ERROR)

            output = stdout # Don't strip leading/trailing whitespace from content

            # Try to guess content type for syntax highlighting
            try:
                # Quick check for JSON/HTML structure
                 if output.strip().startswith(("{", "[")) and output.strip().endswith(("}", "]")):
                     lexer = "json"
                 elif "<html" in output.lower():
                     lexer = "html"
                 else:
                     lexer = "text" # Default to plain text

                 syntax = Syntax(output, lexer, theme="dracula", line_numbers=True, word_wrap=True)
                 return Panel(syntax, title=f"🌐 Curl Result: {url}", border_style=STYLE_INFO, expand=True)

            except Exception: # Fallback if syntax highlighting fails
                 return Text(f"🌐 Curl Result for {url}:\n\n{output}")


        except FileNotFoundError:
             return Text("🔧 Error: 'curl' command not found. Please ensure it's installed.", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error running curl: {e}", style=STYLE_ERROR)

    async def _run_subprocess(self, command: List[str], timeout: int = 30, cwd: Optional[str] = None) -> Tuple[int, str, str]:
        """Helper to run subprocess commands with timeout and error handling."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode or 0, stdout.decode(errors='ignore'), stderr.decode(errors='ignore')
        except asyncio.TimeoutError:
            raise TimeoutError(f"Command timed out after {timeout} seconds: {' '.join(command)}")
        except Exception as e:
            raise RuntimeError(f"Error running command {' '.join(command)}: {e}")

    async def _run_subprocess_shell(self, command: str, timeout: int = 30, cwd: Optional[str] = None) -> Tuple[int, str, str]:
        """Helper to run shell commands with timeout and error handling."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode or 0, stdout.decode(errors='ignore'), stderr.decode(errors='ignore')
        except asyncio.TimeoutError:
            raise TimeoutError(f"Command timed out after {timeout} seconds: {command}")
        except Exception as e:
            raise RuntimeError(f"Error running command {command}: {e}")

    async def execute_code_tool(self, args: str) -> Any:
        """Generate code based on a prompt and execute it."""
        if not args:
            return Text("🔧 Usage: generate_and_execute_code <prompt>", style=STYLE_ERROR)
        return await generate_and_execute_code(args)

    async def list_files_tool(self, path_str: str) -> Struct:
        """API Tool: List all files in a specified directory.

        Args:
            path_str: Path to the directory to list files from. Can be a string path
                      or a dictionary like {'directory': '/path/to/dir'}.
        """
        struct = Struct()
        try:
            # Extract the directory path correctly, handling both string and dict inputs
            if isinstance(path_str, dict) and 'directory' in path_str:
                directory = path_str['directory']
            elif isinstance(path_str, str):
                 # Handle potential dictionary passed as string "{'directory': '...'}"
                 try:
                      path_dict = json.loads(path_str.replace("'", "\""))
                      if isinstance(path_dict, dict) and 'directory' in path_dict:
                          directory = path_dict['directory']
                      else:
                           directory = path_str # Assume it's just a path string
                 except json.JSONDecodeError:
                      directory = path_str # Assume it's just a path string
            else:
                # Default or fallback if input is unclear
                directory = "." # Or handle error appropriately

            # Call the actual file listing function
            files_dict = list_files(directory) # This now returns Dict[str, Union[List[str], str]]

            # Update the Struct with the result from list_files
            struct.update(files_dict)
            return struct

        except Exception as e:
            # Ensure errors are also captured in the Struct
            struct.update({"error": f"Error in list_files_tool wrapper: {e}"})
            console.print(f"Exception in list_files_tool: {traceback.format_exc()}", style=STYLE_ERROR)
            return struct

    async def get_current_datetime_tool(self, args: str) -> Dict[str, Any]:
        """Returns the current date and time."""
        now = datetime.now()
        response_data = {
            "current_datetime": now.isoformat(),
            "timezone": str(now.astimezone().tzinfo)
        }
        return response_data

    async def get_system_stats_tool(self, args: str) -> Struct: # Ensure return type is Struct
        """API Tool: Returns system statistics."""
        struct = Struct() # Initialize Struct here
        if psutil is None:
            struct.update({"error": "psutil library is required but not installed."})
            return struct
        try:
            target_func = get_system_stats
            if asyncio.iscoroutinefunction(target_func):
                stats = await target_func()
            else:
                stats = await asyncio.to_thread(target_func)

            if not isinstance(stats, dict):
                 struct.update({"error": "Tool function get_system_stats did not return a dictionary."})
                 return struct

            # Update the Struct with the stats dictionary
            struct.update(stats)
            return struct
        except NameError:
             struct.update({"error": "get_system_stats function not imported correctly."})
             return struct
        except Exception as e:
            console.print(f"Exception in get_system_stats_tool: {traceback.format_exc()}", style=STYLE_ERROR)
            struct.update({"error": f"Error getting system statistics: {e}"})
            return struct # Return the Struct even on error

    async def list_processes_tool(self, args: str) -> List[Dict[str, Any]]:
        """Returns a list of running processes."""
        if not psutil:
            raise ImportError("psutil is required for list_processes. Please install it.")

        try:
            processes = list_processes()
            return processes
        except Exception as e:
            return Text(f"🔧 Error getting process list: {e}", style=STYLE_ERROR)

    async def read_file_content_tool(self, file_path: str) -> Dict[str, Any]:
        """Returns the content of a file."""
        if not file_path:
            return Text("🔧 Error: No file path provided.", style=STYLE_ERROR)

        try:
            content = read_file_content(file_path)
            return content
        except Exception as e:
            return Text(f"🔧 Error reading file: {e}", style=STYLE_ERROR)

    async def generate_and_execute_code_tool(self, args: str) -> Any:
        """Generate code based on a prompt and execute it."""
        if not args:
            return Text("🔧 Usage: generate_and_execute_code <prompt>", style=STYLE_ERROR)
        return await generate_and_execute_code(args)
        



