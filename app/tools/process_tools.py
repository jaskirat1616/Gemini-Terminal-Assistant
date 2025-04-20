import psutil
from typing import List, Dict, Any

def list_processes() -> List[Dict[str, Any]]:
    """List running processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        processes.append(proc.info)
    return processes 