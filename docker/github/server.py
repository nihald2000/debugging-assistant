
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
    """Search GitHub issues."""
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
    """Search code on GitHub."""
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
