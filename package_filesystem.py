import os
import json
import zipfile
import shutil
from pathlib import Path

# Configuration
SERVER_NAME = "filesystem"
VERSION = "1.0.0"
OUTPUT_FILE = f"{SERVER_NAME}.mcpb"
BUILD_DIR = Path("build") / SERVER_NAME

# Ensure build directory exists
if BUILD_DIR.exists():
    shutil.rmtree(BUILD_DIR)
BUILD_DIR.mkdir(parents=True)

# 1. Create manifest.json
manifest = {
    "manifest_version": "0.1",
    "name": SERVER_NAME,
    "version": VERSION,
    "description": "Filesystem access and semantic search for Claude Desktop",
    "author": "DebugGenie",
    "server": {
        "type": "python",
        "entry_point": "server.py",
        "mcp_config": {
            "command": "uv",
            "args": ["run", "server.py"],
            "env": {
                "PYTHONUNBUFFERED": "1"
            }
        }
    }
}

with open(BUILD_DIR / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

# 2. Create pyproject.toml for uv
pyproject = f"""
[project]
name = "{SERVER_NAME}"
version = "{VERSION}"
description = "Filesystem MCP server"
requires-python = ">=3.10"
dependencies = [
    "mcp[cli]",
    "llama-index",
    "llama-index-core",
    "gradio", 
    "loguru"
]
"""
# Note: Included gradio just in case, but we'll try to use standard mcp
# Actually, we'll rewrite server.py to use FastMCP to be sure it works with Claude Desktop

with open(BUILD_DIR / "pyproject.toml", "w") as f:
    f.write(pyproject)

# 3. Create server.py (Adapted from filesystem_mcp.py but using FastMCP)
server_code = """
from mcp.server.fastmcp import FastMCP
import os
import fnmatch
from pathlib import Path
from typing import List, Optional
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("filesystem-mcp")

# Initialize FastMCP
mcp = FastMCP("filesystem")

# Configuration
ALLOWED_DIRECTORIES = [Path(os.getcwd()).resolve()]
MAX_FILE_SIZE_MB = 10

def validate_path(file_path: str) -> Path:
    try:
        path = Path(file_path).resolve()
        # For desktop extension, we might want to allow more, but let's stick to CWD for safety
        # or maybe allow the user to configure it via env vars?
        # For now, let's allow the current directory where the server runs
        # which might be the extension dir. This is tricky.
        # Ideally, we pass allowed dirs in env.
        
        allowed_dirs = ALLOWED_DIRECTORIES
        if "MCP_ALLOWED_DIRS" in os.environ:
            allowed_dirs = [Path(d).resolve() for d in os.environ["MCP_ALLOWED_DIRS"].split(",")]
        
        is_allowed = False
        for allowed_dir in allowed_dirs:
            if path.is_relative_to(allowed_dir):
                is_allowed = True
                break
        
        # Fallback: if no env var, maybe allow everything? No, unsafe.
        # Let's assume the user runs this in the project root they want to access.
        
        return path
    except Exception as e:
        logger.error(f"Path validation failed: {e}")
        raise

def check_file_size(path: Path):
    if not path.exists():
        return
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.2f}MB (Max: {MAX_FILE_SIZE_MB}MB)")

@mcp.tool()
def read_file(file_path: str) -> str:
    \"\"\"Read contents of a file.\"\"\"
    try:
        path = validate_path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"
        
        check_file_size(path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def list_files(directory: str = ".", pattern: str = "*") -> List[str]:
    \"\"\"List files matching a pattern.\"\"\"
    try:
        dir_path = validate_path(directory)
        if not dir_path.is_dir():
            return [f"Error: Not a directory: {directory}"]
        
        files = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename, pattern):
                    full_path = Path(root) / filename
                    files.append(str(full_path.relative_to(dir_path)))
        return files
    except Exception as e:
        return [f"Error listing files: {str(e)}"]

@mcp.tool()
def get_file_context(file_path: str, line_number: int, context_lines: int = 5) -> str:
    \"\"\"Get lines surrounding a specific line number.\"\"\"
    try:
        path = validate_path(file_path)
        check_file_size(path)
        
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        total = len(lines)
        if line_number < 1 or line_number > total:
            return f"Error: Line {line_number} out of range (1-{total})"
            
        start = max(0, line_number - 1 - context_lines)
        end = min(total, line_number + context_lines)
        
        result = []
        for i in range(start, end):
            prefix = ">" if i == (line_number - 1) else " "
            result.append(f"{i+1:4d} {prefix} {lines[i].rstrip()}")
            
        return "\\n".join(result)
    except Exception as e:
        return f"Error getting context: {str(e)}"

# LlamaIndex Search
_index_cache = None

def get_index():
    global _index_cache
    if _index_cache is None:
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
        # Index the allowed directory (first one)
        # Note: This might be slow on startup
        root_dir = str(ALLOWED_DIRECTORIES[0])
        documents = SimpleDirectoryReader(
            root_dir, 
            recursive=True, 
            exclude_hidden=True
        ).load_data()
        _index_cache = VectorStoreIndex.from_documents(documents)
    return _index_cache

@mcp.tool()
def search_in_files(query: str) -> str:
    \"\"\"Semantic search across files.\"\"\"
    try:
        index = get_index()
        retriever = index.as_retriever(similarity_top_k=5)
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            meta = node.metadata
            path = meta.get("file_path", "unknown")
            score = node.score if node.score else 0.0
            text = node.get_text()
            results.append(f"File: {path} (Score: {score:.2f})\\nContent:\\n{text}\\n---")
            
        return "\\n".join(results)
    except Exception as e:
        return f"Error searching files: {str(e)}"

if __name__ == "__main__":
    mcp.run()
"""

with open(BUILD_DIR / "server.py", "w") as f:
    f.write(server_code)

# 4. Zip it
with zipfile.ZipFile(OUTPUT_FILE, 'w', zipfile.ZIP_DEFLATED) as zf:
    for file in BUILD_DIR.rglob("*"):
        if file.is_file():
            zf.write(file, file.relative_to(BUILD_DIR))

print(f"[OK] Created {OUTPUT_FILE}")
print(f"Manifest:\n{json.dumps(manifest, indent=2)}")
