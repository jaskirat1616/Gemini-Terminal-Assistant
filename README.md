# Gemini Terminal Assistant

```ascii

  ██████╗ ███████╗███╗   ███╗██╗███╗   ██╗██╗
 ██╔════╝ ██╔════╝████╗ ████║██║████╗  ██║██║
 ██║  ███╗█████╗  ██╔████╔██║██║██╔██╗ ██║██║
 ██║   ██║██╔══╝  ██║╚██╔╝██║██║██║╚██╗██║██║
 ╚██████╔╝███████╗██║ ╚═╝ ██║██║██║ ╚████║██║
  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝
            Terminal Assistant
```

**A powerful, feature-rich terminal assistant powered by Google's Gemini models.**

Interact with Gemini directly from your command line, leveraging its capabilities for coding help, system tasks, text generation, and more, enhanced with local tool integrations and a user-friendly interface.

[Watch the Demo Video](demo.mov)

## ✨ Key Features

*   **Direct Gemini Interaction:** Chat directly with various Gemini models (Pro, Flash, etc.).
*   **Rich Terminal UI:** Beautifully formatted output using the `rich` library (Markdown, syntax highlighting, tables, panels).
*   **Built-in Commands:** Manage the application, conversation history, configuration, and more using intuitive `/` commands.
*   **Tool Integration:** Access local tools to:
    *   Execute shell commands (`/execute`, `shell` tool)
    *   Perform Git operations (`/git_status`, `/git_diff`, `/git_log`)
    *   Analyze code (`/lint`)
    *   Manage files (list, find large files - implicitly via `find_large` tool)
    *   Network utilities (`/ping`, `/curl`)
    *   System information (`/ps`, potentially `sys_info`)
    *   Code generation and execution (`/generate_code`)
    *   File/URL opening (`open` tool)
*   **Natural Language Command Interpretation:** Understands phrases like "list files in src" or "what's the cpu usage?" and maps them to appropriate tools.
*   **Configuration Management:** Customize model, API key, theme, behavior via `config.json`.
*   **Conversation History:** Save and load chat sessions.
*   **Syntax Highlighting:** Choose from various `pygments` themes for code blocks.
*   **Customizable System Prompt:** Tailor the assistant's behavior and persona.
*   **Model Switching:** Easily switch between available Gemini models (`/models`).
*   **Context Management:** Maintain simple key-value context across messages (`/context`).
*   **Asynchronous Operations:** Responsive UI thanks to `asyncio`.

## 🚀 Requirements

*   Python 3.8+
*   Google Gemini API Key (Get one from [Google AI Studio](https://ai.google.dev/))
*   `pip` package manager

**Core Dependencies:**

*   `google-generativeai`
*   `rich`
*   `prompt-toolkit`
*   `pygments`

*(See `requirements.txt` for a full list)*

## 🛠️ Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd gemini-terminal-assistant # Or your repository name
    ```

2.  **Install Dependencies:**
    *(Assuming you have a `requirements.txt` file)*
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Key:**
    You have two options:
    *   **Environment Variable (Recommended):** Set the `GEMINI_API_KEY` environment variable.
      ```bash
      export GEMINI_API_KEY="YOUR_API_KEY_HERE"
      ```
      (Add this to your `.bashrc`, `.zshrc`, or equivalent for persistence)
    *   **First Run Prompt:** If the API key is not found in the environment, the application will prompt you to enter it on the first run. You can choose whether to save it (in plain text) to the configuration file (`~/.gemini_terminal/config.json`).

## ▶️ Usage

Run the application using:

```bash
python main.py
```

*   You'll be greeted with a welcome message and a prompt `>`.
*   Type your questions or instructions directly and press Enter.
*   Use `/` commands for specific actions (type `/help` to see all commands).
*   Try natural language commands like "show me the files in the current directory" or "run flake8 on main.py".



## ⚙️ Configuration

The configuration is stored in `~/.gemini_terminal/config.json`. You can edit this file directly or use commands like `/models`, `/theme`, and `/system` to modify settings.

**Key Options:**

*   `api_key`: Your Google Gemini API Key (stored in plain text if saved via prompt).
*   `model`: The default Gemini model to use (e.g., "gemini-2.5-pro-exp-03-25").
*   `system_message`: The instruction given to the model about its role and behavior.
*   `temperature`, `top_p`, `top_k`: LLM generation parameters.
*   `theme`: The `pygments` theme for syntax highlighting in code blocks.
*   `allow_execution`: (If implemented fully) Controls whether tools that execute code/commands are allowed.
*   `enable_tools`: Controls whether the LLM can use the defined API tools.

## 📝 Available Commands

Type `/help` in the application to see the most up-to-date list. Common commands include:

| Command         | Arguments             | Description                                      |
| --------------- | --------------------- | ------------------------------------------------ |
| `/help`         |                       | Show the help message                            |
| `/clear`        |                       | Clear the terminal screen                        |
| `/exit`         |                       | Exit the application                             |
| `/models`       | `[name]`              | List models or switch to `[name]`                |
| `/save`         | `[filename]`          | Save conversation (optional filename)            |
| `/load`         | `<filename>`          | Load conversation from file                      |
| `/tools`        |                       | List available tools and their usage             |
| `/config`       |                       | Show current configuration                       |
| `/system`       | `[message]`           | View or set the system message for the LLM       |
| `/theme`        | `[name]`              | List themes or set syntax highlighting theme     |
| `/execute`      | `<command>`           | Execute a shell command directly                 |
| `/summary`      |                       | Ask the LLM to summarize the conversation        |
| `/git_status`   | `[path]`              | Show Git status for a directory (default: `.`)   |
| `/lint`         | `[path]`              | Run code linter (flake8) on path (default: `.`)  |
| `/git_diff`     | `<file1> <file2>`     | Show Git diff between two files                  |
| `/ps`           |                       | List running processes                           |
| `/git_log`      | `[path] [--count=N]`  | Show Git commit log (default: 15 commits)        |
| `/find_large`   | `[path] [--count=N]`  | Find largest files (default: 10 files)           |
| `/ping`         | `<host>`              | Ping a network host                              |
| `/curl`         | `<url>`               | Fetch content from a URL                         |
| `/interpret`    | `<phrase>`            | Interpret a natural language command             |
| `/context`      | `[key=value\|clear]` | View, set, or clear simple key-value context     |
| `/generate_code`| `<prompt>`            | Ask the LLM to generate and optionally execute code |

## 🔧 Available Tools

The assistant can leverage the following tools (invoked via natural language, specific commands, or LLM function calling):

*   **`shell`**: Executes arbitrary shell commands.
*   **`git_status`**: Checks the status of a Git repository.
*   **`git_diff`**: Computes the diff between two files known to Git.
*   **`git_log`**: Retrieves the Git commit history.
*   **`lint`**: Runs a Python linter (e.g., flake8) on files or directories.
*   **`ps`**: Lists currently running processes.
*   **`find_large`**: Finds the largest files in a directory.
*   **`ping`**: Sends ICMP ECHO_REQUEST packets to network hosts.
*   **`curl`**: Transfers data from or to a server using URL syntax.
*   **`sys_info`**: (Implied) Gathers system information (CPU, memory, disk).
*   **`list_files`**: (Implied by system prompt) Lists files in a directory.
*   **`open`**: Opens a file or URL using the system's default application.
*   **`generate_and_execute_code`**: Generates Python code based on a prompt and executes it.
*   *(Potentially others defined in `app/tools/`)*

## 🎨 Customization

*   **Model:** `/models <model_alias>` (e.g., `/models gemini-2.0-flash`)
*   **Theme:** `/theme <theme_name>` (e.g., `/theme dracula`)
*   **System Prompt:** `/system "Your new system prompt here"`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

*(Add specific contribution guidelines if you have them)*

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. *(Create a LICENSE file if you choose MIT or another license)*