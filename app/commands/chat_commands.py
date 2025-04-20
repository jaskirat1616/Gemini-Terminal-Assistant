import json
import asyncio

from rich.panel import Panel
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text
from rich import box
from rich.live import Live


from app.ui.styles import STYLE_INFO, STYLE_WARNING, STYLE_ERROR, STYLE_BORDER


async def handle_summary_command(terminal, console):
    """Ask the LLM to summarize the current conversation history."""
    if not terminal.history:
        console.print(f"[{STYLE_WARNING}]No conversation history to summarize.[/]")
        return

    console.print(f"[{STYLE_INFO}]Requesting conversation summary...[/]")
    condensed_history = "\n".join([f"{msg['role']}: {str(msg['parts'][0])[:100]}..." for msg in terminal.history if msg.get('parts')]) # Ensure parts exist
    context_str = f"Current Context: {json.dumps(terminal.context)}\n\n" if terminal.context else ""
    summary_prompt = f"{context_str}Summarize the following conversation history:\n\n{condensed_history}\n\nSummary:" # Use the prompt in send_message

    spinner = Spinner("line", text=Text(" Summarizing...", style=STYLE_INFO))
    live_panel = Panel(spinner, title="📝 Summarizing", border_style=STYLE_BORDER, box=box.SQUARE, expand=False, padding=(0, 0)) # expand=False

    summary_response = ""
    summary_error = None
    with Live(live_panel, console=console, refresh_per_second=12, transient=True, vertical_overflow="visible") as live:
        try:
            # Use a temporary chat session so summary request doesn't pollute main history
            # Send the actual summary request prompt
            temp_chat = terminal.model.start_chat(history=terminal.history) # Include full history for context
            response = await asyncio.to_thread(
                temp_chat.send_message,
                summary_prompt, # Send the constructed prompt
                stream=True
            )
            async for chunk in terminal._async_iterator(response):
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
        console.print(f"[{STYLE_ERROR}]Error generating summary:[/] {str(summary_error)}")
    elif summary_response.strip():
        console.print(Panel(Markdown(summary_response), title="📝 Conversation Summary", border_style=STYLE_INFO, expand=True, box=box.SQUARE, padding=(0, 1)))
    else:
        console.print(f"[{STYLE_WARNING}]Failed to generate a summary (or summary was empty).[/]") 