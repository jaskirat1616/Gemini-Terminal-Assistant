from prompt_toolkit.styles import Style as PromptStyle

# Refined Color Palette (Nord-inspired, softer)
PALETTE = {
    "bg": "#2E3440",          # Dark slate blue (Background)
    "fg": "#ECEFF4",          # Off-white (Foreground/Text)
    "dim": "#4C566A",         # Grey-blue (Dim/Comments)
    "border": "#434C5E",      # Lighter Grey-blue (Borders)
    "accent1": "#88C0D0",     # Cyan - for info, commands, success
    "accent2": "#EBCB8B",     # Yellow - for warnings
    "error": "#BF616A",       # Red - for errors, keep red for strong error indication
}

# Map palette to style constants
STYLE_SUCCESS = f"bold {PALETTE['accent1']}" # Cyan for success
STYLE_ERROR = f"bold {PALETTE['error']}"     # Red for error (strong indication)
STYLE_WARNING = f"bold {PALETTE['accent2']}"   # Yellow for warning
STYLE_INFO = f"bold {PALETTE['accent1']}"    # Cyan for info
STYLE_COMMAND = f"bold {PALETTE['accent1']}" # Cyan for commands
STYLE_BORDER = PALETTE['border']             # Grey-blue for border
STYLE_TITLE = f"bold {PALETTE['accent1']}"   # Cyan for title (or could use accent2/yellow for contrast if needed)
STYLE_DIM = f"{PALETTE['dim']}"
STYLE_EMPHASIS = "bold"

# Input prompt style using prompt_toolkit styling
PROMPT_STYLE = PromptStyle.from_dict({
    # Use 'username@hostname:path$ ' style prompt (or similar)
    'prompt_symbol': f"bold {PALETTE['accent1']}", # Prompt symbol color (e.g., '$', '>')
    'path': f"fg:{PALETTE['accent1']} bold",        # Path color
    'model': f"fg:{PALETTE['accent1']}",          # Model name color
    # Default text will use terminal's foreground, which works with the palette
    # Add other elements if needed for the prompt structure
})

# Spinner configuration (keep as is unless visual change desired)
SPINNER_STYLE = "dots"
# More descriptive analyzing texts
SPINNER_ANALYZING_TEXTS = ["Thinking...", "Processing...", "Analyzing...", "Working on it..."]

# Logo (keep as is, colors will depend on terminal theme)
# Consider making the "Terminal Assistant" part use a style, e.g., f"[{STYLE_INFO}]Terminal Assistant[/{STYLE_INFO}]" if rendered via Rich
LOGO = """
  ██████╗ ███████╗███╗   ███╗██╗███╗   ██╗██╗
 ██╔════╝ ██╔════╝████╗ ████║██║████╗  ██║██║
 ██║  ███╗█████╗  ██╔████╔██║██║██╔██╗ ██║██║
 ██║   ██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║
 ╚██████╔╝███████╗██║ ╚═╝ ██║██║██║ ╚████║██║
  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝
            Terminal Assistant
"""

# Example of how to use palette directly if needed:
# some_text = f"[{PALETTE['accent2']}]This is yellow text[/{PALETTE['accent2']}]" 