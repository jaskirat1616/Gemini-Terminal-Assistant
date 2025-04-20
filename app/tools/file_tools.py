import os
from pathlib import Path
from typing import Dict, Any, List, Union
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

# Ensure Struct is imported if needed here, although the manager will handle the final conversion
# from google.protobuf.struct_pb2 import Struct

def list_files(directory: str = ".") -> Dict[str, Union[List[str], str]]:
    """List files in a directory and return the result as a dictionary."""
    try:
        main_dir = f"/Users/jaskiratsingh/{directory}"
        path = Path(main_dir)
        if not path.exists():
            return {"error": f"Directory '{main_dir}' does not exist."}
        if not path.is_dir():
            return {"error": f"'{main_dir}' is not a directory."}
        if not os.access(main_dir, os.R_OK):
            return {"error": f"Permission denied: Cannot read directory '{main_dir}'."}

        # Return a dictionary with a fixed key 'file_list' containing the names
        file_names = [entry.name for entry in path.iterdir()]
        return {"file_list": file_names}
    except Exception as e:
        return {"error": str(e)}

def read_file_content(file_path: str) -> Dict[str, Any]:
    """Read the content of a file."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}

def generate_and_execute_code(prompt: str) -> Any:
    """Generate code based on a prompt, save it to a temporary file, and execute it."""
    try:
        # Call the model to generate code based on the prompt
        # Assuming `model` is an instance of your model class
        generated_code = model.generate_code(prompt)
        
        # Create a temporary file to store the generated code
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(generated_code)
            temp_file_path = temp_file.name
        
        # Execute the generated code
        import subprocess
        result = subprocess.run(['python', temp_file_path], capture_output=True, text=True)
        
        # Clean up the temporary file
        import os
        os.remove(temp_file_path)
        
        # Format the output using Rich
        output_panel = Panel(
            Syntax(generated_code, "python", theme="monokai", line_numbers=True),
            title="Generated Code",
            border_style="blue"
        )
        
        execution_panel = Panel(
            Text(f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}"),
            title="Execution Result",
            border_style="green" if result.returncode == 0 else "red"
        )
        
        return Panel(
            output_panel,
            execution_panel,
            title="Code Generation and Execution",
            border_style="yellow"
        )
    except Exception as e:
        return Panel(
            Text(f"Error: {str(e)}", style="red"),
            title="Error",
            border_style="red"
        )
