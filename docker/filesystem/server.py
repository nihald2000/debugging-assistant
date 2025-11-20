
from mcp.server.fastmcp import FastMCP
import os
import fnmatch
from pathlib import Path
from typing import List

mcp = FastMCP("filesystem")

# In Docker, we mount the project to /data
MOUNT_POINT = Path("/data")

@mcp.tool()
def list_files(directory: str = ".", pattern: str = "*") -> List[str]:
    """List files in the mounted directory."""
    try:
        # Resolve path relative to mount point
        target_dir = (MOUNT_POINT / directory).resolve()
        
        # Security check: ensure we stay within /data
        if not str(target_dir).startswith(str(MOUNT_POINT.resolve())):
            return [f"Error: Access denied. Path must be within {MOUNT_POINT}"]
            
        if not target_dir.is_dir():
            return [f"Error: Not a directory: {directory}"]
            
        files = []
        for root, _, filenames in os.walk(target_dir):
            for filename in filenames:
                if fnmatch.fnmatch(filename, pattern):
                    full_path = Path(root) / filename
                    rel_path = full_path.relative_to(MOUNT_POINT)
                    files.append(str(rel_path))
        return files
    except Exception as e:
        return [f"Error: {str(e)}"]

@mcp.tool()
def read_file(file_path: str) -> str:
    """Read a file from the mounted directory."""
    try:
        target_path = (MOUNT_POINT / file_path).resolve()
        
        if not str(target_path).startswith(str(MOUNT_POINT.resolve())):
            return f"Error: Access denied."
            
        if not target_path.exists():
            return f"Error: File not found."
            
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
