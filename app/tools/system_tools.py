import psutil
from typing import Dict, Any
from datetime import datetime
import platform

def get_system_stats() -> dict:
    """Get system statistics like CPU and memory usage."""
    if not psutil:
        raise ImportError("psutil is required for get_system_stats. Please install it.")

    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        cpu_freq = psutil.cpu_freq()

        system_info = {
            "system": f"{platform.system()} {platform.release()}",
            "architecture": f"{platform.machine()} ({platform.processor()})",
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "cpu_cores": f"{psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical",
            "cpu_freq": f"{cpu_freq.current:.0f} MHz (Max: {cpu_freq.max:.0f} MHz)" if cpu_freq else "N/A",
            "cpu_percent": f"{psutil.cpu_percent(interval=0.1)}%",
            "ram_total": f"{mem.total / (1024 ** 3):.2f} GB",
            "ram_available": f"{mem.available / (1024 ** 3):.2f} GB",
            "ram_used": f"{mem.percent}%",
            "disk_total": f"{disk.total / (1024 ** 3):.2f} GB",
            "disk_used": f"{disk.used / (1024 ** 3):.2f} GB ({disk.percent}%)",
            "boot_time": boot_time.strftime('%Y-%m-%d %H:%M:%S')
        }

        return system_info
    except Exception as e:
        raise RuntimeError(f"Error getting system statistics: {e}")

def get_current_datetime() -> Dict[str, Any]:
    """Get the current date and time."""
    now = datetime.now()
    return {
        "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S")
    }

