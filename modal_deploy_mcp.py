import modal
import os
import fnmatch
import requests
from pathlib import Path
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

# Define Modal App
app = modal.App("debuggenie-mcp")

# Define Image with dependencies
image = modal.Image.debian_slim().pip_install(
    "mcp[cli]", 
    "google-genai", 
    "duckduckgo-search", 
    "beautifulsoup4", 
    "requests", 
    "llama-index-core"
)

# Define Persistent Volume for codebase access
volume = modal.Volume.from_name("debuggenie-data", create_if_missing=True)

# Define Secrets for API keys (GITHUB_TOKEN, etc.)
secrets = [modal.Secret.from_name("debuggenie-secrets")]

# -----------------------------------------------------------------------------
# 1. Filesystem MCP Server
# -----------------------------------------------------------------------------
@app.function(image=image, volumes={"/data": volume}, secrets=secrets)
@modal.asgi_app()
def filesystem_mcp():
    mcp = FastMCP("filesystem")
    MOUNT_POINT = Path("/data")

    @mcp.tool()
    def list_files(directory: str = ".", pattern: str = "*") -> List[str]:
        """List files in the mounted directory."""
        try:
            target_dir = (MOUNT_POINT / directory).resolve()
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

    return mcp

# -----------------------------------------------------------------------------
# 2. GitHub MCP Server
# -----------------------------------------------------------------------------
@app.function(image=image, secrets=secrets)
@modal.asgi_app()
def github_mcp():
    mcp = FastMCP("github")
    
    def get_headers():
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    @mcp.tool()
    def search_issues(query: str, repo: str) -> List[dict]:
        """Search GitHub issues."""
        url = "https://api.github.com/search/issues"
        params = {"q": f"repo:{repo} is:issue {query}", "per_page": 5}
        try:
            resp = requests.get(url, headers=get_headers(), params=params)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [{"title": i["title"], "url": i["html_url"], "state": i["state"]} for i in items]
        except Exception as e:
            return [{"error": str(e)}]

    @mcp.tool()
    def search_code(query: str, language: str = "python") -> List[dict]:
        """Search code on GitHub."""
        url = "https://api.github.com/search/code"
        params = {"q": f"{query} language:{language}", "per_page": 5}
        try:
            resp = requests.get(url, headers=get_headers(), params=params)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [{"name": i["name"], "repo": i["repository"]["full_name"], "url": i["html_url"]} for i in items]
        except Exception as e:
            return [{"error": str(e)}]

    return mcp

# -----------------------------------------------------------------------------
# 3. Web Search MCP Server
# -----------------------------------------------------------------------------
@app.function(image=image, secrets=secrets)
@modal.asgi_app()
def websearch_mcp():
    mcp = FastMCP("websearch")

    @mcp.tool()
    def search_web(query: str) -> List[dict]:
        """Search the web using DuckDuckGo."""
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append(r)
            return results
        except Exception as e:
            return [{"error": str(e)}]

    @mcp.tool()
    def get_page_content(url: str) -> str:
        """Get text content from a URL."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup(["script", "style"]):
                s.decompose()
            return soup.get_text()[:5000]
        except Exception as e:
            return f"Error: {str(e)}"

    return mcp
