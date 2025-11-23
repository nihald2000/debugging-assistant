import gradio as gr
try:
    gr.mcp
except AttributeError:
    class MockMCP:
        def tool(self, func):
            return func
    gr.mcp = MockMCP()

from pathlib import Path
from typing import List, Optional, Dict, Set
import os
import fnmatch
import time
from collections import defaultdict
from datetime import datetime, timedelta
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SimpleNodeParser
from utils.logger import log

# --- Security Configuration ---

# Default to a dedicated workspace directory
DEFAULT_WORKSPACE = Path("./workspace").resolve()

# Get from environment or use default
WORKSPACE_ROOT = Path(
    os.getenv("DEBUGGENIE_WORKSPACE", str(DEFAULT_WORKSPACE))
).resolve()

# Ensure workspace exists
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

# Global blacklist - NEVER allow access to these
BLACKLISTED_PATTERNS = {
    ".env", ".env.*", "*.pem", "*.key", 
    ".git/*", ".ssh/*", "id_rsa*",
    "secrets/*", "credentials/*",
    ".aws/*", ".config/*",
    "__pycache__/*", "*.pyc"
}

# File size limits
MAX_FILE_SIZE_MB = 10
MAX_FILES_PER_REQUEST = 100

class SecurityError(Exception):
    """Raised for security violations."""
    pass

# --- Security Utilities ---

def log_file_access(
    operation: str,
    file_path: str,
    client_id: str,
    allowed: bool,
    reason: str = ""
):
    """Log all file access attempts for security auditing."""
    log.info(
        f"SECURITY_AUDIT | {operation} | {file_path} | "
        f"client={client_id} | allowed={allowed} | {reason}"
    )

def validate_path_secure(file_path: str) -> Path:
    """
    Validate path with multiple security checks.
    
    Raises:
        SecurityError: If path validation fails
    """
    # Step 1: Convert to Path and resolve (follows symlinks)
    try:
        requested_path = Path(file_path)
        
        # Block absolute paths from user to prevent confusion/bypass attempts
        # Users should provide paths relative to the workspace root
        if requested_path.is_absolute():
             # If it's absolute, check if it's inside workspace
             # If so, make it relative for further checks, or just use it if safe
             # But generally, we prefer relative inputs.
             # For now, let's treat absolute paths as suspicious if they don't start with workspace
             if not str(requested_path.resolve()).startswith(str(WORKSPACE_ROOT)):
                 raise SecurityError("Absolute paths outside workspace not allowed")
        
        # Resolve relative to workspace
        if requested_path.is_absolute():
             full_path = requested_path.resolve()
        else:
             full_path = (WORKSPACE_ROOT / requested_path).resolve()
        
    except (ValueError, OSError) as e:
        raise SecurityError(f"Invalid path: {e}")
    
    # Step 2: Verify resolved path is within workspace
    try:
        # is_relative_to is available in Python 3.9+
        if not full_path.is_relative_to(WORKSPACE_ROOT):
             raise SecurityError(f"Path escapes workspace: {file_path}")
    except AttributeError:
        # Fallback for older python if needed (though 3.13 is used here)
        if not str(full_path).startswith(str(WORKSPACE_ROOT)):
            raise SecurityError(f"Path escapes workspace: {file_path}")
    
    # Step 3: Check against blacklist
    try:
        relative_path = full_path.relative_to(WORKSPACE_ROOT)
        str_rel_path = str(relative_path).replace(os.sep, "/") # Normalize for fnmatch
        
        for pattern in BLACKLISTED_PATTERNS:
            if fnmatch.fnmatch(str_rel_path, pattern) or fnmatch.fnmatch(str(relative_path.name), pattern):
                raise SecurityError(f"Access denied: {pattern} is blacklisted")
    except ValueError:
        # Should not happen if Step 2 passed
        raise SecurityError("Path validation error during blacklist check")
    
    # Step 4: Verify file exists and is actually a file (for read operations)
    # We allow non-existent paths for some checks if needed, but here we assume read
    if not full_path.exists():
        raise SecurityError(f"File not found: {file_path}")
    
    if not full_path.is_file():
        raise SecurityError(f"Not a file: {file_path}")
    
    # Step 5: Check file size
    try:
        size_mb = full_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise SecurityError(
                f"File too large: {size_mb:.2f}MB (max {MAX_FILE_SIZE_MB}MB)"
            )
    except OSError as e:
         raise SecurityError(f"Could not stat file: {e}")
    
    return full_path

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = defaultdict(list)  # ip -> [timestamps]
    
    def check_rate_limit(self, client_id: str = "default") -> bool:
        """
        Check if request should be allowed.
        Returns True if allowed, False if rate limited.
        """
        now = datetime.now()
        
        # Clean old entries
        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if now - ts < self.window
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(now)
        return True

rate_limiter = RateLimiter()

# --- LlamaIndex Cache ---
_index_cache = None

def get_index():
    """
    Lazy load LlamaIndex.
    """
    global _index_cache
    if _index_cache is None:
        log.info("Building LlamaIndex...")
        # Index only the workspace
        documents = SimpleDirectoryReader(
            str(WORKSPACE_ROOT), 
            recursive=True, 
            exclude_hidden=True
        ).load_data()
        _index_cache = VectorStoreIndex.from_documents(documents)
        log.info("LlamaIndex built successfully.")
    return _index_cache

# --- MCP Tools ---

@gr.mcp.tool
def read_file(file_path: str, client_id: str = "default") -> str:
    """
    Read contents of a file from the codebase.
    
    Args:
        file_path: Relative path to the file within the workspace.
        client_id: Client identifier for rate limiting.
    """
    # Rate limit check
    if not rate_limiter.check_rate_limit(client_id):
        log_file_access("read_file", file_path, client_id, False, "Rate limit exceeded")
        return "Error: Rate limit exceeded. Try again later."
    
    try:
        # Secure validation
        safe_path = validate_path_secure(file_path)
        
        # Read file
        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        
        log_file_access("read_file", file_path, client_id, True)
        return content
        
    except SecurityError as e:
        log_file_access("read_file", file_path, client_id, False, str(e))
        log.warning(f"Security violation: {e}")
        return f"Error: {e}"
    except Exception as e:
        log_file_access("read_file", file_path, client_id, False, f"Unexpected: {e}")
        log.error(f"Unexpected error reading {file_path}: {e}")
        return f"Error: Failed to read file"

@gr.mcp.tool
def list_files(directory: str = ".", pattern: str = "*", client_id: str = "default") -> List[str]:
    """
    List files matching a pattern in a directory.
    
    Args:
        directory: Directory to search in (relative to workspace).
        pattern: Glob pattern to match files.
        client_id: Client identifier for rate limiting.
    """
    if not rate_limiter.check_rate_limit(client_id):
        log_file_access("list_files", directory, client_id, False, "Rate limit exceeded")
        return ["Error: Rate limit exceeded"]

    try:
        # Validate directory
        try:
            requested_path = Path(directory)
            if requested_path.is_absolute():
                 full_path = requested_path.resolve()
            else:
                 full_path = (WORKSPACE_ROOT / requested_path).resolve()
            
            if not full_path.is_relative_to(WORKSPACE_ROOT):
                 raise SecurityError(f"Path escapes workspace: {directory}")
            
            if not full_path.exists() or not full_path.is_dir():
                 raise SecurityError(f"Invalid directory: {directory}")
                 
        except Exception as e:
            raise SecurityError(f"Invalid path: {e}")

        files = []
        count = 0
        for root, _, filenames in os.walk(full_path):
            for filename in filenames:
                if count >= MAX_FILES_PER_REQUEST:
                    break
                    
                if fnmatch.fnmatch(filename, pattern):
                    # Check blacklist for each file
                    rel_file_path = Path(root) / filename
                    try:
                         # Re-use validate logic or simple check? 
                         # Simple check for speed in list
                         rel_from_ws = rel_file_path.relative_to(WORKSPACE_ROOT)
                         str_rel = str(rel_from_ws).replace(os.sep, "/")
                         
                         is_blacklisted = False
                         for bl_pattern in BLACKLISTED_PATTERNS:
                             if fnmatch.fnmatch(str_rel, bl_pattern) or fnmatch.fnmatch(filename, bl_pattern):
                                 is_blacklisted = True
                                 break
                         
                         if not is_blacklisted:
                             files.append(str(rel_from_ws))
                             count += 1
                    except Exception:
                        continue
            if count >= MAX_FILES_PER_REQUEST:
                break
        
        log_file_access("list_files", directory, client_id, True, f"Found {len(files)} files")
        return files
    except SecurityError as e:
        log_file_access("list_files", directory, client_id, False, str(e))
        return [f"Error: {str(e)}"]
    except Exception as e:
        log_file_access("list_files", directory, client_id, False, f"Unexpected: {e}")
        return [f"Error: {str(e)}"]

@gr.mcp.tool
def get_file_context(file_path: str, line_number: int, context_lines: int = 5, client_id: str = "default") -> str:
    """
    Get lines surrounding a specific line number.
    """
    if not rate_limiter.check_rate_limit(client_id):
        return "Error: Rate limit exceeded"

    try:
        path = validate_path_secure(file_path)
        
        with open(path, "r", encoding="utf-8", errors="replace") as f:
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
            
        log_file_access("get_file_context", file_path, client_id, True)
        return "\n".join(context)
    except SecurityError as e:
        log_file_access("get_file_context", file_path, client_id, False, str(e))
        return f"Error: {str(e)}"
    except Exception as e:
        log_file_access("get_file_context", file_path, client_id, False, f"Unexpected: {e}")
        return f"Error: {str(e)}"

@gr.mcp.tool
def search_in_files(query: str, file_types: List[str] = None, client_id: str = "default") -> List[dict]:
    """
    Semantic search across codebase using LlamaIndex.
    """
    if not rate_limiter.check_rate_limit(client_id):
        return [{"error": "Rate limit exceeded"}]

    try:
        index = get_index()
        retriever = index.as_retriever(similarity_top_k=5)
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            # Verify the file path in metadata is still valid/secure
            try:
                # node.metadata['file_path'] is usually absolute
                fpath = node.metadata.get("file_path")
                if fpath:
                     validate_path_secure(fpath)
                     
                results.append({
                    "file_path": fpath,
                    "score": node.score,
                    "content": node.get_text()
                })
            except SecurityError:
                continue # Skip insecure results
        
        log_file_access("search_in_files", query, client_id, True, f"Returned {len(results)} results")
        return results
    except Exception as e:
        log_file_access("search_in_files", query, client_id, False, f"Unexpected: {e}")
        return [{"error": str(e)}]

if __name__ == "__main__":
    # Create a simple interface to demonstrate the MCP server
    with gr.Blocks() as demo:
        gr.Markdown("# Filesystem MCP Server (Secure)")
        gr.Markdown(f"Serving files from: `{WORKSPACE_ROOT}`")
    
    demo.launch()
