import os
import json
from pathlib import Path

# Configuration
DOCKER_DIR = Path("docker")
CONFIG_FILE = "claude_desktop_config.json"
COMPOSE_FILE = "docker-compose.yml"

def create_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Created {path}")

# 1. Filesystem Server
filesystem_server = """
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
    \"\"\"List files in the mounted directory.\"\"\"
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
    \"\"\"Read a file from the mounted directory.\"\"\"
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
"""

filesystem_dockerfile = """
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .

# Create mount point
RUN mkdir /data
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "server.py"]
"""

# 2. GitHub Server
github_server = """
from mcp.server.fastmcp import FastMCP
import os
import requests
from typing import List, Dict, Any

mcp = FastMCP("github")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is required")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

@mcp.tool()
def search_issues(query: str, repo: str) -> List[dict]:
    \"\"\"Search GitHub issues.\"\"\"
    url = "https://api.github.com/search/issues"
    params = {"q": f"repo:{repo} is:issue {query}", "per_page": 5}
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [{"title": i["title"], "url": i["html_url"], "state": i["state"]} for i in items]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def search_code(query: str, language: str = "python") -> List[dict]:
    \"\"\"Search code on GitHub.\"\"\"
    url = "https://api.github.com/search/code"
    params = {"q": f"{query} language:{language}", "per_page": 5}
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [{"name": i["name"], "repo": i["repository"]["full_name"], "url": i["html_url"]} for i in items]
    except Exception as e:
        return [{"error": str(e)}]

if __name__ == "__main__":
    mcp.run()
"""

github_dockerfile = """
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "server.py"]
"""

# 3. Web Search Server
websearch_server = """
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
from typing import List

mcp = FastMCP("websearch")

@mcp.tool()
def search_web(query: str) -> List[dict]:
    \"\"\"Search the web using DuckDuckGo.\"\"\"
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
    \"\"\"Get text content from a URL.\"\"\"
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

if __name__ == "__main__":
    mcp.run()
"""

websearch_dockerfile = """
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "server.py"]
"""

# Generate Files
def main():
    # Filesystem
    create_file(DOCKER_DIR / "filesystem/server.py", filesystem_server)
    create_file(DOCKER_DIR / "filesystem/Dockerfile", filesystem_dockerfile)
    create_file(DOCKER_DIR / "filesystem/requirements.txt", "mcp[cli]\n")

    # GitHub
    create_file(DOCKER_DIR / "github/server.py", github_server)
    create_file(DOCKER_DIR / "github/Dockerfile", github_dockerfile)
    create_file(DOCKER_DIR / "github/requirements.txt", "mcp[cli]\nrequests\n")

    # Web Search
    create_file(DOCKER_DIR / "websearch/server.py", websearch_server)
    create_file(DOCKER_DIR / "websearch/Dockerfile", websearch_dockerfile)
    create_file(DOCKER_DIR / "websearch/requirements.txt", "mcp[cli]\nduckduckgo-search\nbeautifulsoup4\nrequests\n")

    # Docker Compose
    compose_content = """
services:
  filesystem:
    build: ./docker/filesystem
    image: mcp/filesystem
    volumes:
      - .:/data
  
  github:
    build: ./docker/github
    image: mcp/github
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
  
  websearch:
    build: ./docker/websearch
    image: mcp/websearch
"""
    create_file(Path(COMPOSE_FILE), compose_content)

    # Claude Desktop Config
    config_content = {
        "mcpServers": {
            "filesystem": {
                "command": "docker",
                "args": [
                    "run", "-i", "--rm",
                    "-v", "${HOME}/Documents/MyProject:/data",
                    "mcp/filesystem"
                ]
            },
            "github": {
                "command": "docker",
                "args": [
                    "run", "-i", "--rm",
                    "-e", "GITHUB_TOKEN",
                    "mcp/github"
                ]
            },
            "websearch": {
                "command": "docker",
                "args": [
                    "run", "-i", "--rm",
                    "mcp/websearch"
                ]
            }
        }
    }
    create_file(Path(CONFIG_FILE), json.dumps(config_content, indent=2))

    print("\n[OK] Deployment files generated!")
    print("1. Run 'docker-compose build' to create images")
    print("2. Copy content of claude_desktop_config.json to your Claude config")
    print("3. Ensure GITHUB_TOKEN is set in your environment")

if __name__ == "__main__":
    main()
