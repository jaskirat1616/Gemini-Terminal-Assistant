# main.py

import asyncio
import argparse
import traceback

# Rich imports
from rich.console import Console
from rich.text import Text

# Local imports
from config import Config
from app.terminal import GeminiTerminal
from app.ui.styles import STYLE_ERROR # Import styles needed for error handling here

def main():
    parser = argparse.ArgumentParser(description="Gemini Terminal Assistant")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--model", help="Specify model to use (overrides config)")
    args = parser.parse_args()

    console = Console() # Initialize console here

    try:
        # Initialize Config first
        config = Config(config_path=args.config)

        # Override model if specified via CLI *after* loading config
        if args.model and args.model in config.AVAILABLE_MODELS:
            config.model = args.model
            console.print(f"Using model specified via CLI: {config.model}") # Inform user

        # Pass config and console to Terminal
        terminal = GeminiTerminal(config=config, console=console)
        asyncio.run(terminal.start())

    except Exception as e:
        # Use the initialized console for error reporting
        console.print(f"[{STYLE_ERROR}]Fatal error starting application:[/{STYLE_ERROR}] {str(e)}")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        exit(1)

if __name__ == "__main__":
    main()