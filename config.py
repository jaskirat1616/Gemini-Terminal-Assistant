# config.py

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
from google.protobuf.struct_pb2 import Struct

# Available models with descriptions
AVAILABLE_MODELS = {
    "gemini-2.5-pro-exp-03-25": "Well-balanced model for most tasks",
    "gemini-2.0-flash": "Can process both images and text",
    "gemini-2.0-flash-lite": "Most powerful model with advanced reasoning",
    "gemini-2.0-flash-exp-image-generation": "Fastest model for quick responses",
    "gemini-2.5-flash-preview-04-17" : "Fastest pro model for quick responses"
}

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gemini-2.5-pro-exp-03-25",
    "system_message": "You are a powerful terminal assistant. You can interact with the system, manage files (read, write, list, search), execute shell commands and Python code, access the clipboard, compare files, manage Python packages, and open files/applications. Help the user with coding, system tasks, and answering questions.",
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 0.95,
    "top_k": 40,
    "theme": "one-dark",
    "allow_execution": True,
    "enable_tools": True,
}

class Config:
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Optional path to config file. If not provided, will use default location.
        """
        # Set up default config
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model = DEFAULT_CONFIG["model"]
        self.system_message = DEFAULT_CONFIG["system_message"]
        self.temperature = DEFAULT_CONFIG["temperature"]
        self.max_tokens = DEFAULT_CONFIG["max_tokens"]
        self.top_p = DEFAULT_CONFIG["top_p"]
        self.top_k = DEFAULT_CONFIG["top_k"]
        self.theme = DEFAULT_CONFIG["theme"]
        self.allow_execution = DEFAULT_CONFIG["allow_execution"]
        self.enable_tools = DEFAULT_CONFIG["enable_tools"]
        
        # Load config from file
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default config path
            self.config_path = Path.home() / ".gemini_terminal" / "config.json"
        
        self._load_config()
        
        # If API key not set, prompt for it
        if not self.api_key:
            self._prompt_api_key()
        
        # Save config if it doesn't exist
        if not self.config_path.exists():
            self._save_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Update attributes from config file
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration.")
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare config data
            config_data = {
                "api_key": self.api_key,
                "model": self.model,
                "system_message": self.system_message,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "theme": self.theme,
                "allow_execution": self.allow_execution,
                "enable_tools": self.enable_tools,
            }
            
            # Write to file
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _prompt_api_key(self) -> None:
        """Prompt user for API key if not set."""
        from rich.console import Console
        from rich.prompt import Prompt
        
        console = Console()
        console.print("[yellow]No Gemini API key found.[/yellow]")
        console.print("Get your API key from: [link=https://ai.google.dev/]https://ai.google.dev/[/link]")
        
        self.api_key = Prompt.ask("Enter your Gemini API key", password=True)
        
        # Save API key to environment variable for current session
        os.environ["GEMINI_API_KEY"] = self.api_key
        
        # Ask if the key should be saved to the config file
        save_key = Prompt.ask(
            "Save API key to config file? [bold](Warning: the key will be stored in plain text)[/bold]",
            choices=["y", "n"],
            default="n"
        )
        
        if save_key.lower() != "y":
            # If not saving to config, remove from config but keep in memory
            self.api_key = ""
            console.print("[green]API key will be used for this session only.[/green]")
    
    def update(self, **kwargs) -> None:
        """Update configuration with new values.
        
        Args:
            **kwargs: Key-value pairs to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Save to file
        self._save_config()

async def some_api_tool(self, args: str) -> Dict[str, Any]:
    try:
        # Perform some operation
        result = {"data": {"some_key": "some_value"}}
        
        # Convert the dictionary to a Struct
        struct = Struct()
        struct.update(result)
        
        return struct
    except Exception as e:
        # Return an error in a dictionary format
        return {"error": str(e)}