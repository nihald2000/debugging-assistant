import gradio as gr
try:
    gr.mcp
except AttributeError:
    class MockMCP:
        def tool(self, func):
            return func
    gr.mcp = MockMCP()

from pathlib import Path
from typing import List, Optional, Dict
import os
import fnmatch
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SimpleNodeParser
from utils.logger import log

# Configuration
ALLOWED_DIRECTORIES = [Path(os.getcwd()).resolve()]
MAX_FILE_SIZE_MB = 10

def validate_path(file_path: str) -> Path:
    """
    Validate that the path is within allowed directories and exists.
    """
    try:
        path = Path(file_path).resolve()
        is_allowed = False
        for allowed_dir in ALLOWED_DIRECTORIES:
            if path.is_relative_to(allowed_dir):
                is_allowed = True
                break
        
        if not is_allowed:
            raise PermissionError(f"Access denied: {file_path} is not in allowed directories.")
        
        return path
    except Exception as e:
        log.error(f"Path validation failed for {file_path}: {e}")
        raise

def check_file_size(path: Path):
    """
    Check if file size is within limits.
    """
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.2f}MB (Max: {MAX_FILE_SIZE_MB}MB)")

# LlamaIndex Cache
_index_cache = None

def get_index():
    """
    Lazy load LlamaIndex.
    """
    global _index_cache
    if _index_cache is None:
        log.info("Building LlamaIndex...")
        # For simplicity, we index the current working directory but respect .gitignore if possible
        # This is a basic implementation. In production, you'd want persistent storage.
        documents = SimpleDirectoryReader(
            str(ALLOWED_DIRECTORIES[0]), 
            recursive=True, 
            exclude_hidden=True
        ).load_data()
        _index_cache = VectorStoreIndex.from_documents(documents)
        log.info("LlamaIndex built successfully.")
    return _index_cache

@gr.mcp.tool
def read_file(file_path: str) -> str:
    """
    Read contents of a file from the codebase.
    
    Args:
        file_path: Absolute or relative path to the file.
    """
    try:
        path = validate_path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        check_file_size(path)
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        log.info(f"Read file: {path}")
        return content
    except Exception as e:
        log.error(f"Error reading file {file_path}: {e}")
        return f"Error: {str(e)}"

@gr.mcp.tool
def list_files(directory: str = ".", pattern: str = "*") -> List[str]:
    """
    List files matching a pattern in a directory.
    
    Args:
        directory: Directory to search in.
        pattern: Glob pattern to match files (e.g., "*.py").
    """
    try:
        dir_path = validate_path(directory)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")
        
        files = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                if fnmatch.fnmatch(filename, pattern):
                    full_path = Path(root) / filename
                    # Return relative path for cleaner output
                    files.append(str(full_path.relative_to(dir_path)))
        
        log.info(f"Listed {len(files)} files in {directory} matching {pattern}")
        return files
    except Exception as e:
        log.error(f"Error listing files in {directory}: {e}")
        return [f"Error: {str(e)}"]

@gr.mcp.tool
def get_file_context(file_path: str, line_number: int, context_lines: int = 5) -> str:
    """
    Get lines surrounding a specific line number.
    
    Args:
        file_path: Path to the file.
        line_number: Target line number (1-based).
        context_lines: Number of lines before and after to include.
    """
    try:
        path = validate_path(file_path)
        check_file_size(path)
        
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        if line_number < 1 or line_number > total_lines:
            raise ValueError(f"Line number {line_number} out of range (1-{total_lines})")
        
        start = max(0, line_number - 1 - context_lines)
        end = min(total_lines, line_number + context_lines)
        
        context = []
        for i in range(start, end):
            prefix = ">" if i == (line_number - 1) else " "
            context.append(f"{i+1:4d} {prefix} {lines[i].rstrip()}")
            
        return "\n".join(context)
    except Exception as e:
        log.error(f"Error getting context for {file_path}: {e}")
        return f"Error: {str(e)}"

@gr.mcp.tool
def search_in_files(query: str, file_types: List[str] = None) -> List[dict]:
    """
    Semantic search across codebase using LlamaIndex.
    
    Args:
        query: Natural language search query.
        file_types: Optional list of file extensions to filter (not yet implemented in this basic version).
    """
    try:
        index = get_index()
        retriever = index.as_retriever(similarity_top_k=5)
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            results.append({
                "file_path": node.metadata.get("file_path", "unknown"),
                "score": node.score,
                "content": node.get_text()
            })
        
        log.info(f"Search for '{query}' returned {len(results)} results")
        return results
    except Exception as e:
        log.error(f"Error searching files: {e}")
        return [{"error": str(e)}]

if __name__ == "__main__":
    # Create a simple interface to demonstrate the MCP server
    with gr.Blocks() as demo:
        gr.Markdown("# Filesystem MCP Server")
        gr.Markdown("This server provides tools for file access and semantic search.")
    
    demo.launch()
