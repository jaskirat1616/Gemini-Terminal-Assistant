# app/terminal.py

import os
import asyncio
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import platform

# Google AI and Rich imports
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, GenerateContentResponse, HarmCategory, HarmBlockThreshold, FunctionDeclaration, Tool
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich import box
from rich.spinner import Spinner
from rich.tree import Tree
from rich.theme import Theme

# Pygments import for theme listing
from pygments.styles import get_all_styles

# Prompt Toolkit imports
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

# Local imports
from config import Config, AVAILABLE_MODELS
from app.tools.manager import ToolManager
from app.ui.styles import * # Import all styles
from app.utils.helpers import get_timestamp, ensure_renderable, save_conversation, load_conversation
from app.nlp.interpreter import interpret_natural_language
from app.commands.config_commands import show_config_command
from app.commands.model_commands import show_models_command
from app.commands.tool_commands import show_tools_command, run_tool_command
from app.commands.chat_commands import handle_summary_command
from app.commands.context_commands import handle_context_command
from app.commands.theme_commands import handle_theme_command
from app.commands.help_commands import show_help_command, show_welcome_command

# --- Command Definitions ---
# Moved command list here for easier access within the class
COMMANDS = sorted([
    "/help", "/clear", "/exit", "/models",
    "/save", "/load", "/tools", "/config",
    "/system", "/theme", "/execute", "/summary",
    "/git_status", "/lint", "/git_diff", "/ps",
    "/git_log", "/find_large", "/ping", "/curl",
    "/interpret", "/context"
])

# Define your detailed system prompt here
# This could also be loaded from the config file or another source
# Make sure this is consistent between model_commands.py and terminal.py
# ... existing code ...
DETAILED_SYSTEM_PROMPT = """
You are Gemini Terminal Assistant, an AI specialized in assisting users within a command-line interface environment. Your primary goal is to provide accurate, concise, and actionable help for a wide range of tasks, including programming, system administration, text manipulation, and general knowledge queries.

**Core Directives:**

1.  **Be Precise and Concise:** Terminal users value efficiency. Provide answers directly addressing the query without unnecessary verbosity. Get straight to the point.
2.  **Use Markdown Effectively:** Format your responses for readability in a terminal.
    *   Use code blocks (```language\\ncode\\n```) for all code snippets, commands, or file contents. Specify the language where appropriate (e.g., ```python, ```bash, ```json).
    *   Use inline backticks (`code`) for commands, filenames, variables, and technical terms.
    *   Use lists (`*` or `-`) for steps or multiple items.
    *   Use bold (`**text**`) for emphasis on key terms or actions.
3.  **Acknowledge Tool Use (When Implemented):** You may have access to tools to interact with the local system (e.g., run commands, read files).
    *   *If* you need to use a tool to answer a question (e.g., "What files are in the current directory?"), state that you will use the tool.
    *   *Before* executing potentially impactful tools (like running code or modifying files, if such tools are provided), explicitly ask the user for confirmation.
    *   Clearly present the results obtained from tools.
4.  **Code Generation and Explanation:**
    *   When generating code, ensure it is correct and follows best practices for the specified language.
    *   Provide brief explanations of the code's purpose and how to use it.
    *   If asked to debug code, identify the error, explain the cause, and suggest a fix.
5.  **Command-Line Assistance:**
    *   Provide accurate command-line examples for various shells (bash, zsh, fish, PowerShell, etc.), adapting to the user's likely environment if possible (though you cannot know it directly without a tool).
    *   Explain what complex commands do, breaking down pipelines and options.
6.  **Context Awareness:** Maintain context within the current conversation session. Refer to previous messages if relevant to the ongoing query. Use the chat history to provide more relevant answers.
7.  **Safety and Limitations:**
    *   Adhere strictly to safety guidelines. Do not generate harmful, unethical, biased, or inappropriate content.
    *   If a request is ambiguous, ask clarifying questions.
    *   If you cannot fulfill a request due to limitations (e.g., lack of real-time data, inability to perform an action), state this clearly and explain why. Offer alternatives if possible.
    *   Do not guess if you don't know the answer. State that you don't have the information.
8.  **Persona:** Act as an expert, helpful, and slightly formal assistant. Be reliable and trustworthy.

**Available Tools:**
*   `list_files`: List files in a directory.
*   `get_system_stats`: gets all the system stats like cpu-percent, memory usage, and disk usage.
"""

# ... existing code ...

class GeminiTerminal:
    def __init__(self, config: Config, console: Console):
        self.config = config
        self.console = console

        # Initialize Gemini
        try:
            genai.configure(api_key=self.config.api_key)
            self.generation_config = GenerationConfig(
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                # max_output_tokens is often model-specific, let model decide unless needed
            )
            self.tool_manager = ToolManager()
            self.api_tools = self.tool_manager.get_api_tools()
            self.model = genai.GenerativeModel(
                self.config.model,
                generation_config=self.generation_config,
                system_instruction=DETAILED_SYSTEM_PROMPT,
                tools=self.api_tools
            )
        except Exception as e:
            self.console.print(f"[{STYLE_ERROR}]Fatal Error Initializing Gemini:[/{STYLE_ERROR}] {e}")
            self.console.print(f"[{STYLE_ERROR}]Please ensure your API key is correct and you have internet access.[/{STYLE_ERROR}]")
            exit(1)

        self.history = []
        self.last_tool_result = None
        self.context = {} # Simple context storage

        # Set up prompt session
        history_file = os.path.expanduser("~/.gemini_terminal_history")
        try:
             Path(history_file).parent.mkdir(parents=True, exist_ok=True)
             self.session = PromptSession(
                 history=FileHistory(history_file),
                 auto_suggest=AutoSuggestFromHistory(),
                 style=PROMPT_STYLE
             )
        except Exception as e:
             self.console.print(f"[{STYLE_WARNING}]Warning: Could not initialize prompt history: {e}[/{STYLE_WARNING}]")
             self.session = PromptSession(style=PROMPT_STYLE)

        self.command_completer = WordCompleter(COMMANDS, ignore_case=True)


    async def start(self):
        """Main application loop."""
        self._show_welcome()

        while True:
            try:
                user_input = await self._get_user_input()
                if not user_input:
                    continue

                if user_input.startswith('/'):
                    if await self._handle_command(user_input):
                        continue
                else:
                    await self._process_message(user_input)

            except KeyboardInterrupt:
                self.console.print(f"\n[{STYLE_WARNING}]Interrupted. Type /exit to quit.[/{STYLE_WARNING}]")
            except EOFError:
                 self.console.print(f"\n[{STYLE_WARNING}]Exiting...[/{STYLE_WARNING}]")
                 break
            except Exception as e:
                self.console.print(f"[{STYLE_ERROR}]An unexpected error occurred:[/{STYLE_ERROR}]")
                self.console.print_exception(show_locals=False)


    async def _get_user_input(self) -> str:
        """Get user input using prompt_toolkit."""
        history_len = len([m for m in self.history if m['role'] == 'user'])
        prompt_message = [
             ('class:info', f'({history_len} msgs) '),
             ('class:path', f'[{self.config.model}] '),
             ('class:prompt', '> ')
        ]
        try:
            user_input = await asyncio.to_thread(
                self.session.prompt,
                prompt_message,
                completer=self.command_completer,
                complete_while_typing=True,
                refresh_interval=0.5
            )
            return user_input.strip()
        except Exception as e:
            self.console.print(f"[{STYLE_WARNING}]Error getting input: {e}[/{STYLE_WARNING}]")
            return ""

    async def _process_message(self, message: str):
        """Process a user message: Interpret NL, check tools, intercept, or send to LLM."""
        # 1. Natural Language Command Interpretation
        interpretation = await interpret_natural_language(message, self.context, self.console)
        if interpretation:
            tool_name, args_string = interpretation
            await self._run_tool_command(tool_name, args_string, title=f"Interpreted: {tool_name}")
            return

        # 2. Direct Tool Call Check (If NL fails)
        tool_result = await self.tool_manager.check_for_tool_calls(message)
        if tool_result is not None:
            self.last_tool_result = tool_result
            tool_name = message.split()[0].lower()
            title = f"🔧 Tool Result ({tool_name})"
            border = STYLE_SUCCESS if not isinstance(tool_result, Text) or STYLE_ERROR not in str(getattr(tool_result,'style','')) else STYLE_ERROR
            self.console.print(Panel(ensure_renderable(tool_result), title=title, border_style=border, box=box.ROUNDED, expand=True))
            return

        # 3. Intercept Common Phrases (Keep simple ones for quick actions)
        if await self._intercept_phrase(message):
            return

        # 4. Send to LLM
        await self._send_to_llm(message)

    async def _send_to_llm(self, message: str):
        """Send message to the Gemini LLM, handle function calls, and display the final response."""
        self.history.append({"role": "user", "parts": [message]})

        spinner_text_index = 0
        spinner = Spinner(SPINNER_STYLE, text=SPINNER_ANALYZING_TEXTS[0] + f" ({self.config.model})", style=STYLE_INFO)
        live_panel = Panel(spinner, title=f"🤖 Gemini Thinking...", border_style=STYLE_BORDER, box=box.ROUNDED, expand=False)
        full_response_text = ""
        llm_error = None

        try:
            with Live(live_panel, console=self.console, refresh_per_second=10, transient=True) as live:
                try:
                    # Create chat session with current history
                    chat = self.model.start_chat(history=self.history[:-1])

                    # --- Send message and check for function call ---
                    response = await asyncio.to_thread(
                        chat.send_message,
                        self.history[-1]['parts'] # Send the latest user message content
                    )

                    # Check the first part of the first candidate for a function call
                    candidate = response.candidates[0]
                    first_part = candidate.content.parts[0] if candidate.content.parts else None

                    if first_part and first_part.function_call:
                        function_call = first_part.function_call
                        tool_name = function_call.name
                        tool_args = dict(function_call.args) if function_call.args else {}

                        # Append the model's function call request to history
                        self.history.append({"role": "model", "parts": [{"function_call": function_call}]})

                        spinner.update(text=f"🛠️ Requesting Tool: {tool_name}()...", style=STYLE_INFO)
                        live.update(live_panel)

                        # --- Execute the tool function ---
                        api_response = await self.tool_manager._execute_tool(tool_name, tool_args)

                        # Format the tool's response for the model
                        function_response_part = {
                            "function_response": {
                                "name": tool_name,
                                "response": api_response # Must be a dict
                            }
                        }

                        # Append the function response to history
                        self.history.append({"role": "function", "parts": [function_response_part]}) # Use 'function' role

                        spinner.update(text=f"🔄 Processing Tool Response...", style=STYLE_INFO)
                        live.update(live_panel)

                        # --- Send the function response back to the model ---
                        response = await asyncio.to_thread(
                             chat.send_message,
                             function_response_part # Send only the function response back
                        )
                        # The final response should now contain the text answer
                        candidate = response.candidates[0] # Re-check candidate
                        first_part = candidate.content.parts[0] if candidate.content.parts else None


                    # --- Process the final text response (either initial or after function call) ---
                    if first_part and first_part.text:
                        full_response_text = first_part.text
                    elif response.prompt_feedback and response.prompt_feedback.block_reason:
                         full_response_text = f"[{STYLE_WARNING}]Request blocked: {response.prompt_feedback.block_reason}[/]"
                         if response.prompt_feedback.block_reason_message:
                              full_response_text += f"\nDetails: {response.prompt_feedback.block_reason_message}"
                    elif candidate.finish_reason != 'STOP':
                         full_response_text = f"[{STYLE_WARNING}]Model stopped unexpectedly. Finish Reason: {candidate.finish_reason}[/]"
                    # Handle potential errors or empty responses more robustly here if needed

                except Exception as e_inner:
                    llm_error = e_inner
                    error_type = type(e_inner).__name__
                    error_msg = str(e_inner)
                    # Display error outside the Live context if it fails
                    # Need to store it to show after Live exits
                    llm_error_display = f"\\n[{STYLE_ERROR}]API Error ({error_type}):[/{STYLE_ERROR}] {error_msg}"


        # --- Display final result or error ---
        except Exception as e_outer: # Catch errors in Live context management itself
            self.console.print(f"[{STYLE_ERROR}]Error during message processing:[/{STYLE_ERROR}] {type(e_outer).__name__}: {e_outer}")
            self.console.print_exception(show_locals=False)
            return # Exit if Live fails

        if llm_error: # Display error encountered inside the Live block
             self.console.print(llm_error_display)

        if full_response_text.strip():
            md = Markdown(full_response_text, code_theme=self.config.theme)
            final_panel = Panel(md, title=f"🤖 Gemini ({self.config.model})", border_style=STYLE_BORDER, box=box.ROUNDED, expand=True)
            self.console.print(final_panel)
            # Append the final model text response to history
            self.history.append({"role": "model", "parts": [full_response_text]})
            await self._process_code_blocks(full_response_text) # Process code blocks if any
        elif not llm_error:
            self.console.print(f"[{STYLE_WARNING}]Received an empty or non-text response from the model.[/{STYLE_WARNING}]")
        
        # Clean up potential partial history if errors occurred mid-flow
        # This logic might need refinement depending on desired error recovery
        # Commenting out this block as its condition causes an AttributeError when the last part is a string.
        # The error handling above should generally ensure a valid (even if error message) string is added.
        # last_entry = self.history[-1] if self.history else None
        # if last_entry and last_entry["role"] == "model":
        #     # Check the type of the part before accessing attributes
        #     part_content = last_entry["parts"][0]
        #     is_empty_part_object = isinstance(part_content, Part) and not part_content.text and not part_content.function_call
        #     is_empty_string = isinstance(part_content, str) and not part_content.strip()
        #
        #     if is_empty_part_object or is_empty_string:
        #          # If the last model entry is empty (error before text generation), maybe remove it?
        #          # Or handle based on specific error conditions
        #          self.console.print(f"[{STYLE_DIM}]Note: Last model history entry appears empty, potentially due to an error.[/{STYLE_DIM}]")
        #          pass

    async def _process_code_blocks(self, response_text: str):
        """
        Parses the response text for code blocks and potentially offers actions.
        Currently, this is a placeholder.
        """
        # Basic regex to find markdown code blocks ```language\ncode\n```
        code_block_pattern = re.compile(r"```(?:\w+)?\n(.*?)\n```", re.DOTALL)
        matches = code_block_pattern.finditer(response_text)

        code_blocks = [match.group(1) for match in matches]

        if code_blocks:
            # In the future, you could add logic here to:
            # - Display a prompt asking the user if they want to copy or execute the code.
            # - Use pyperclip to copy to clipboard.
            # - Call the 'shell' or 'execute_code' tool after confirmation.
            self.console.print(f"[{STYLE_DIM}]Detected {len(code_blocks)} code block(s). (Action logic not yet implemented)[/{STYLE_DIM}]")
            # For now, just acknowledge detection
            pass
        # No action needed if no code blocks are found

    async def _async_iterator(self, iterable: GenerateContentResponse):
         # This helper is no longer used in the non-streaming _send_to_llm
         # Keep it if you plan to re-introduce streaming for non-function-call responses
         pass

    async def _handle_command(self, command_str: str) -> bool:
        """Handle internal commands starting with /."""
        parts = command_str.split(maxsplit=1)
        cmd = parts[0].lower()
        args_str = parts[1].strip() if len(parts) > 1 else ""
        args = args_str.split()

        if cmd == "/generate_code":
            if not args_str:
                self.console.print(f"[{STYLE_WARNING}]Usage: /generate_code <prompt>[/]")
                return True
            await run_tool_command(self, self.console, "generate_and_execute_code", args_str, title=f"🔧 Generate and Execute Code")
            return True
        elif cmd == "/exit":
            self.console.print(f"[{STYLE_WARNING}]Goodbye![/]", style=STYLE_EMPHASIS)
            raise EOFError
        elif cmd == "/clear":
            self.console.clear()
            return True
        elif cmd == "/help":
            await show_help_command(self.console)
            return True
        elif cmd == "/tools":
            await show_tools_command(self, self.console)
            return True
        elif cmd == "/config":
            await show_config_command(self, self.console)
            return True
        elif cmd == "/models":
            await show_models_command(self, self.console, args_str)
            return True
        elif cmd == "/save":
            filename = args_str if args_str else f"conversation_{get_timestamp()}.json"
            save_conversation(self.history, self.config.model, filename, self.console)
            return True
        elif cmd == "/load":
            if not args_str:
                 self.console.print(f"[{STYLE_WARNING}]Usage: /load <filename>[/]")
                 return True
            loaded_model, loaded_history = load_conversation(args_str, self.console)
            if loaded_history: # Check if loading was successful
                self.history = loaded_history
                if loaded_model and loaded_model != self.config.model:
                    self.config.model = loaded_model
                    # Re-initialize model (important!)
                    try:
                        # Re-initialize with tools
                        self.model = genai.GenerativeModel(
                            self.config.model,
                            generation_config=self.generation_config,
                            system_instruction=DETAILED_SYSTEM_PROMPT, # Make sure prompt is available or loaded
                            tools=self.api_tools # Pass tools here too
                        )
                        self.console.print(f"[{STYLE_SUCCESS}]Model re-initialized to: {self.config.model}[/]")
                    except Exception as e:
                        self.console.print(f"[{STYLE_ERROR}]Error re-initializing model '{loaded_model}': {e}[/]")
            return True
        elif cmd == "/system":
            if not args_str:
                self.console.print(f"[{STYLE_INFO}]Current system message:[/]")
                self.console.print(Panel(self.config.system_message or "[Not Set]", border_style=STYLE_DIM, title="System Message", expand=True))
            else:
                self.config.system_message = args_str
                self.config._save_config() # Persist change
                self.console.print(f"[{STYLE_SUCCESS}]System message updated. It may apply from the next message.[{STYLE_SUCCESS}]")
            return True
        elif cmd == "/theme":
            await handle_theme_command(self, self.console, args_str)
            return True
        elif cmd == "/execute":
            if not args_str:
                self.console.print(f"[{STYLE_WARNING}]Usage: /execute <shell_command>[/]")
                return True
            await run_tool_command(self, self.console, "shell", args_str, title=f"셸 Exec: {args_str[:30]}...")
            return True
        elif cmd == "/summary":
            await handle_summary_command(self, self.console)
            return True
        elif cmd == "/git_status":
            await run_tool_command(self, self.console, "git_status", args_str, title="Git Status")
            return True
        elif cmd == "/lint":
            await run_tool_command(self, self.console, "lint", args_str or ".", title="Code Linting")
            return True
        elif cmd == "/git_diff":
             if len(args_str.split()) != 2:
                  self.console.print(f"[{STYLE_WARNING}]Usage: /git_diff <file1> <file2>[/]")
                  return True
             await run_tool_command(self, self.console, "git_diff", args_str, title=f"Git Diff")
             return True
        elif cmd == "/ps":
            await run_tool_command(self, self.console, "ps", "", title="Process List")
            return True
        elif cmd == "/git_log":
            await run_tool_command(self, self.console, "git_log", args_str, title="Git Log")
            return True
        elif cmd == "/find_large":
            await run_tool_command(self, self.console, "find_large", args_str or ".", title="Find Large Files")
            return True
        elif cmd == "/ping":
             if not args_str:
                  self.console.print(f"[{STYLE_WARNING}]Usage: /ping <host>[/]")
                  return True
             await run_tool_command(self, self.console, "ping", args_str, title=f"Ping: {args_str}")
             return True
        elif cmd == "/curl":
             if not args_str:
                  self.console.print(f"[{STYLE_WARNING}]Usage: /curl <url>[/]")
                  return True
             await run_tool_command(self, self.console, "curl", args_str, title=f"Curl: {args_str}")
             return True
        elif cmd == "/context":
            await handle_context_command(self, self.console, args_str)
            return True
        elif cmd == "/interpret":
            if not args_str:
                self.console.print(f"[{STYLE_WARNING}]Usage: /interpret <natural language phrase>[/]")
                return True
            interpretation = await interpret_natural_language(args_str, self.context, self.console)
            if interpretation:
                tool_name, i_args = interpretation
                self.console.print(Panel(f"Tool: [bold]{tool_name}[/]\nArgs: [cyan]{i_args}[/]", title=f"Interpretation for: '{args_str}'", border_style=STYLE_INFO))
            else:
                self.console.print(Panel(f"Could not interpret phrase as a direct tool command.", title=f"Interpretation for: '{args_str}'", border_style=STYLE_WARNING))
            return True

        self.console.print(f"[{STYLE_WARNING}]Unknown command: {cmd}. Type /help for available commands.[/{STYLE_WARNING}]")
        return True

    async def _run_tool_command(self, tool_name: str, args: str, title: Optional[str] = None):
        """Helper to run a tool via command and display results."""
        status_msg = f"Running {tool_name}..."
        actual_title = title or f"🔧 {tool_name}"
        with self.console.status(f"[{STYLE_DIM}]{status_msg}[/]"):
             result = await self.tool_manager._execute_tool(tool_name, args)
        self.last_tool_result = result
        border = STYLE_SUCCESS if not isinstance(result, Text) or STYLE_ERROR not in str(getattr(result,'style','')) else STYLE_ERROR
        self.console.print(Panel(ensure_renderable(result), title=actual_title, border_style=border, box=box.ROUNDED, expand=True))

    def _show_welcome(self):
        """Show welcome message."""
        welcome_content = Text.from_markup(
            f"[bold {STYLE_INFO}]{LOGO}[/]\n"
            f"[bold {STYLE_TITLE}]Gemini Terminal Assistant[/]\n\n"
            f"[{STYLE_EMPHASIS}]Model:[/] {self.config.model}\n"
            f"[{STYLE_EMPHASIS}]Theme:[/] {self.config.theme}\n"
            f"\nType [{STYLE_COMMAND}]/help[/] for available commands."
        )
        self.console.print(Panel(
            welcome_content,
            box=box.DOUBLE_EDGE,
            border_style=STYLE_BORDER,
            padding=(1, 2),
            expand=False
        ))

    def _show_help(self):
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

        self.console.print(help_table)

    def _show_models(self, args_str: str):
        """Show available models or switch model."""
        model_to_set = args_str.strip()
        if model_to_set:
            if model_to_set in AVAILABLE_MODELS:
                 self.config.model = model_to_set
                 self.config._save_config()
                 try:
                      self.model = genai.GenerativeModel(self.config.model, generation_config=self.generation_config)
                      self.console.print(f"[{STYLE_SUCCESS}]Model changed to: {self.config.model}[/]")
                 except Exception as e:
                      self.console.print(f"[{STYLE_ERROR}]Error initializing model '{model_to_set}': {e}[/]")
                 return
            else:
                self.console.print(f"[{STYLE_WARNING}]Unknown model: {model_to_set}. Use /models to list available ones.[/{STYLE_WARNING}]")

        table = Table(title=f"[{STYLE_TITLE}]Available Models[/]", box=box.ROUNDED, border_style=STYLE_BORDER, expand=True, padding=(0, 1), show_header=True, header_style="bold magenta")
        table.add_column("Alias", style=STYLE_COMMAND, justify="left", no_wrap=True)
        table.add_column("Description", style="")
        table.add_column("Current", justify="center")

        for model_alias, desc in AVAILABLE_MODELS.items():
            is_current = "✅" if model_alias == self.config.model else ""
            table.add_row(model_alias, desc, is_current)
        self.console.print(table)
        self.console.print(f"\nCurrent model: [{STYLE_EMPHASIS}]{self.config.model}[/]")
        self.console.print(f"Usage: [{STYLE_COMMAND}]/models <model_alias>[/] to switch models")

    def _show_tools(self):
        """Show available tools from ToolManager."""
        tools_info = self.tool_manager.get_available_tools()
        if not tools_info:
            self.console.print("No tools available.", style=STYLE_INFO)
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
        self.console.print(table)
        self.console.print(f"\n[{STYLE_DIM}]Tools can often be invoked directly (e.g., 'file list .') or via /execute <tool_command>.[/{STYLE_DIM}]")

    def _show_config(self):
        """Show current configuration."""
        config_table = Table(title=f"[{STYLE_TITLE}]Current Configuration[/]", box=box.ROUNDED, border_style=STYLE_BORDER, expand=True, padding=(0, 1), show_header=True, header_style="bold magenta")
        config_table.add_column("Setting", style=STYLE_INFO, justify="right", no_wrap=True)
        config_table.add_column("Value")

        config_to_show = vars(self.config).copy()

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

        self.console.print(config_table)
        if 'config_path' in config_to_show:
            self.console.print(f"\n[{STYLE_DIM}]Config loaded from: {config_to_show['config_path']}[/{STYLE_DIM}]")

    def _handle_theme_cmd(self, args_str: str):
        """List available themes or set the syntax theme."""
        theme_name = args_str.strip()
        available_themes = sorted(list(get_all_styles()))

        if theme_name:
            if theme_name in available_themes:
                self.config.theme = theme_name
                self.config._save_config()
                self.console.print(f"[{STYLE_SUCCESS}]Syntax theme changed to: {self.config.theme}[/]")
            else:
                self.console.print(f"[{STYLE_WARNING}]Unknown theme: {theme_name}. Use /theme to list.[/{STYLE_WARNING}]")
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

            self.console.print(theme_table)
            self.console.print(f"\nCurrent theme: [{STYLE_EMPHASIS}]{self.config.theme}[/]")
            self.console.print(f"Usage: [{STYLE_COMMAND}]/theme <theme_name>[/]")

    async def _handle_summary_cmd(self):
        """Ask the LLM to summarize the current conversation history."""
        if not self.history:
            self.console.print(f"[{STYLE_WARNING}]No conversation history to summarize.[/]")
            return

        self.console.print(f"[{STYLE_INFO}]Requesting conversation summary...[/]")
        condensed_history = "\n".join([f"{msg['role']}: {str(msg['parts'][0])[:100]}..." for msg in self.history if msg.get('parts')]) # Ensure parts exist
        context_str = f"Current Context: {json.dumps(self.context)}\n\n" if self.context else ""
        summary_prompt = f"{context_str}Summarize the following conversation history:\n\n{condensed_history}\n\nSummary:" # Use the prompt in send_message

        spinner = Spinner("line", text=Text(" Summarizing...", style=STYLE_INFO))
        live_panel = Panel(spinner, title="📝 Summarizing", border_style=STYLE_BORDER, box=box.SQUARE, expand=False, padding=(0, 0)) # expand=False

        summary_response = ""
        summary_error = None
        with Live(live_panel, console=self.console, refresh_per_second=12, transient=True, vertical_overflow="visible") as live:
            try:
                # Use a temporary chat session so summary request doesn't pollute main history
                # Send the actual summary request prompt
                temp_chat = self.model.start_chat(history=self.history) # Include full history for context
                response = await asyncio.to_thread(
                    temp_chat.send_message,
                    summary_prompt, # Send the constructed prompt
                    stream=True
                )
                async for chunk in self._async_iterator(response):
                     try:
                         if chunk.text:
                             summary_response += chunk.text
                             # Update spinner within live context if needed, though it's transient
                             live.update(live_panel)
                     except AttributeError:
                         pass # Ignore chunks without text

            except Exception as e:
                summary_error = e

        if summary_error:
            self.console.print(f"[{STYLE_ERROR}]Error generating summary:[/] {str(summary_error)}")
        elif summary_response.strip():
            self.console.print(Panel(Markdown(summary_response), title="📝 Conversation Summary", border_style=STYLE_INFO, expand=True, box=box.SQUARE, padding=(0, 1)))
        else:
            self.console.print(f"[{STYLE_WARNING}]Failed to generate a summary (or summary was empty).[/]")

    async def _intercept_phrase(self, message: str) -> bool:
         """Check for common phrases that map directly to tools."""
         lower_message = message.lower().strip()
         tool_to_run: Optional[Tuple[str, str]] = None
         title: Optional[str] = None

         # Keep this simple, rely more on NL interpreter
         if lower_message in ["check system", "system info", "sys info", "show system info"]:
             tool_to_run = ("sys_info", "")
             title = "🖥️ System Information"
         elif lower_message == "git status":
             tool_to_run = ("git_status", "")
             title = "Git Status"
         elif lower_message == "show processes" or lower_message == "ps":
             tool_to_run = ("ps", "")
             title = "Process List"
         # Add more simple intercepts if desired, but avoid complex regex here

         if tool_to_run:
             tool_name, args = tool_to_run
             await self._run_tool_command(tool_name, args, title=title)
             return True

         return False

    async def _run_subprocess(self, command: List[str]) -> Tuple[int, str, str]:
        """Run a subprocess command and return the return code, stdout, and stderr."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return process.returncode, stdout.decode().strip(), stderr.decode().strip()
        except Exception as e:
            return -1, "", str(e)

    async def open_tool(self, path_or_url: str) -> Text:
        """Open a file or URL using the system's default application.

        Args:
            path_or_url: The file path or URL to open.
        """
        if not path_or_url:
            return Text("🔧 Error: Missing file path or URL to open.", style=STYLE_ERROR)

        try:
            system = platform.system()
            if system == "Windows":
                # Use 'start' on Windows
                command = ["start", "", path_or_url]
                ret, out, err = await self._run_subprocess(command)
            elif system == "Darwin": # macOS
                command = ["open", path_or_url]
                ret, out, err = await self._run_subprocess(command)
            else: # Linux and other Unix-like
                command = ["xdg-open", path_or_url]
                ret, out, err = await self._run_subprocess(command)

            if ret != 0:
                 return Text(f"🔧 Error opening '{path_or_url}': {err.strip()}", style=STYLE_ERROR)
            else:
                return Text(f"✅ Attempted to open '{path_or_url}'.", style=STYLE_SUCCESS)

        except FileNotFoundError:
            return Text(f"🔧 Error: Command not found (likely 'open', 'start', or 'xdg-open'). Cannot open '{path_or_url}'.", style=STYLE_ERROR)
        except Exception as e:
            return Text(f"🔧 Error opening '{path_or_url}': {str(e)}", style=STYLE_ERROR)