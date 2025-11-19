import gradio as gr
try:
    gr.mcp
except AttributeError:
    class MockMCP:
        def tool(self, func):
            return func
    gr.mcp = MockMCP()

import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from duckduckgo_search import DDGS
from cachetools import TTLCache, cached
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.logger import log
import re

# Cache: 100 items, 1 hour TTL
cache = TTLCache(maxsize=100, ttl=3600)

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    has_accepted_answer: bool = False # for SO
    votes: int = 0 # for SO
    relevance_score: float = 0.0
    code_snippets: List[str] = Field(default_factory=list)

@cached(cache)
@gr.mcp.tool
def search_stack_overflow(error_query: str) -> List[dict]:
    """
    Search Stack Overflow for similar errors using the Stack Exchange API.
    
    Args:
        error_query: The error message or query string.
    """
    log.info(f"Searching Stack Overflow for: {error_query}")
    
    api_url = "https://api.stackexchange.com/2.3/search/advanced"
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": error_query,
        "site": "stackoverflow",
        "filter": "withbody", # Get body to extract snippets if needed, though snippet is usually enough for list
        "pagesize": 5
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("items", []):
            # Basic relevance scoring based on votes and accepted answer
            score = 0.5
            if item.get("is_answered"):
                score += 0.2
            if item.get("score", 0) > 10:
                score += 0.2
            if item.get("accepted_answer_id"):
                score += 0.1
                
            result = SearchResult(
                title=item.get("title"),
                url=item.get("link"),
                snippet=item.get("body", "")[:200] + "...", # Use body as snippet (truncated)
                has_accepted_answer=item.get("is_answered", False),
                votes=item.get("score", 0),
                relevance_score=min(score, 1.0),
                code_snippets=[] # We could extract from body if we wanted
            )
            results.append(result.model_dump())
            
        return results
    except Exception as e:
        log.error(f"Error searching Stack Overflow: {e}")
        return [{"error": str(e)}]

@cached(cache)
@gr.mcp.tool
def search_web(query: str) -> List[dict]:
    """
    General web search using DuckDuckGo.
    
    Args:
        query: Search query.
    """
    log.info(f"Searching web for: {query}")
    
    try:
        results = []
        with DDGS() as ddgs:
            ddgs_results = list(ddgs.text(query, max_results=5))
            
            for r in ddgs_results:
                result = SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    relevance_score=0.8 # Default score for web results
                )
                results.append(result.model_dump())
                
        return results
    except Exception as e:
        log.error(f"Error searching web: {e}")
        return [{"error": str(e)}]

@gr.mcp.tool
def get_page_content(url: str) -> str:
    """
    Fetch and clean page content from a URL.
    
    Args:
        url: URL to fetch.
    """
    log.info(f"Fetching content from: {url}")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:5000] # Limit content length
    except Exception as e:
        log.error(f"Error fetching page content: {e}")
        return f"Error: {str(e)}"

@gr.mcp.tool
def extract_code_snippets(url: str) -> List[str]:
    """
    Extract code blocks from a webpage.
    
    Args:
        url: URL to extract code from.
    """
    log.info(f"Extracting code from: {url}")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        snippets = []
        
        # Look for <pre><code> blocks (common)
        for code_block in soup.find_all('pre'):
            code = code_block.get_text()
            if code and len(code.strip()) > 10: # Filter tiny snippets
                snippets.append(code.strip())
                
        # Look for <code> blocks not in pre (inline code, maybe less useful but sometimes blocks)
        # Often <code> inside <div class="code"> or similar
        for code_block in soup.find_all('code'):
            if code_block.parent.name != 'pre':
                code = code_block.get_text()
                if len(code.split('\n')) > 1: # Only multiline code
                    snippets.append(code.strip())
                    
        return snippets[:10] # Limit number of snippets
    except Exception as e:
        log.error(f"Error extracting code: {e}")
        return [f"Error: {str(e)}"]

if __name__ == "__main__":
    # Create a simple interface to demonstrate the MCP server
    with gr.Blocks() as demo:
        gr.Markdown("# Web Search MCP Server")
        gr.Markdown("Tools for web searching and content extraction.")
    
    demo.launch()
