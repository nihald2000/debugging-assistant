
from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
from typing import List

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

if __name__ == "__main__":
    mcp.run()
