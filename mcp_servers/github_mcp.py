import gradio as gr
try:
    gr.mcp
except AttributeError:
    class MockMCP:
        def tool(self, func):
            return func
    gr.mcp = MockMCP()

import requests
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from cachetools import TTLCache, cached
from utils.logger import log
import time

# Load environment variables
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_KEY")
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_URL = "https://api.github.com/search/code"

# Cache: 100 items, 1 hour TTL
cache = TTLCache(maxsize=100, ttl=3600)

class GitHubIssue(BaseModel):
    title: str
    url: str
    body: str
    labels: List[str]
    state: str
    comments_count: int
    relevance_score: float = 0.0

class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _execute_graphql(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query with retry logic."""
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment variables.")

        response = requests.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            log.error(f"GraphQL Errors: {data['errors']}")
            raise Exception(f"GitHub GraphQL Error: {data['errors'][0]['message']}")
            
        return data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _execute_rest_search(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a REST API search with retry logic."""
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment variables.")

        response = requests.get(
            endpoint,
            params=params,
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code == 403 and "rate limit" in response.text.lower():
            reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait_time = reset_time - time.time() + 1
            log.warning(f"Rate limit hit. Waiting {wait_time:.2f}s")
            time.sleep(wait_time)
            return self._execute_rest_search(endpoint, params) # Retry once after wait

        response.raise_for_status()
        return response.json()

# Initialize client
client = GitHubClient(token=GITHUB_TOKEN)

@cached(cache)
@gr.mcp.tool
def search_issues(query: str, repo: str) -> List[dict]:
    """
    Search GitHub issues in a specific repository using GraphQL.
    
    Args:
        query: Search terms.
        repo: Repository name (e.g., "owner/repo").
    """
    log.info(f"Searching issues in {repo} for: {query}")
    
    graphql_query = """
    query($search_query: String!) {
      search(query: $search_query, type: ISSUE, first: 10) {
        edges {
          node {
            ... on Issue {
              title
              url
              bodyText
              state
              labels(first: 5) {
                nodes {
                  name
                }
              }
              comments {
                totalCount
              }
            }
          }
        }
      }
    }
    """
    
    # Construct search query for GitHub
    full_query = f"repo:{repo} is:issue {query}"
    
    try:
        data = client._execute_graphql(graphql_query, {"search_query": full_query})
        issues = []
        
        for edge in data.get("data", {}).get("search", {}).get("edges", []):
            node = edge.get("node", {})
            if not node:
                continue
                
            issue = GitHubIssue(
                title=node.get("title", ""),
                url=node.get("url", ""),
                body=node.get("bodyText", "")[:500] + "...", # Truncate body
                labels=[l["name"] for l in node.get("labels", {}).get("nodes", [])],
                state=node.get("state", ""),
                comments_count=node.get("comments", {}).get("totalCount", 0),
                relevance_score=1.0 # Placeholder, could be improved with local ranking
            )
            issues.append(issue.model_dump())
            
        return issues
    except Exception as e:
        log.error(f"Error searching issues: {e}")
        return [{"error": str(e)}]

@cached(cache)
@gr.mcp.tool
def search_code(query: str, language: str = "python") -> List[dict]:
    """
    Search code across GitHub using REST API (GraphQL does not support code search).
    
    Args:
        query: Code snippet or terms to search for.
        language: Programming language filter.
    """
    log.info(f"Searching code for: {query} in {language}")
    
    try:
        # GitHub Code Search REST API
        # Note: Requires specific query syntax
        q = f"{query} language:{language}"
        
        data = client._execute_rest_search(GITHUB_REST_URL, {"q": q, "per_page": 5})
        
        results = []
        for item in data.get("items", []):
            results.append({
                "name": item.get("name"),
                "path": item.get("path"),
                "repo": item.get("repository", {}).get("full_name"),
                "url": item.get("html_url"),
                "score": item.get("score")
            })
            
        return results
    except Exception as e:
        log.error(f"Error searching code: {e}")
        return [{"error": str(e)}]

@cached(cache)
@gr.mcp.tool
def get_pr_discussions(pr_url: str) -> List[dict]:
    """
    Get discussions (comments) from a Pull Request.
    
    Args:
        pr_url: Full URL of the Pull Request.
    """
    log.info(f"Getting discussions for PR: {pr_url}")
    
    try:
        # Extract owner, repo, number from URL
        # Format: https://github.com/owner/repo/pull/123
        parts = pr_url.rstrip("/").split("/")
        if "pull" not in parts:
             raise ValueError("Invalid PR URL")
             
        number_idx = parts.index("pull") + 1
        number = int(parts[number_idx])
        repo = parts[number_idx - 2]
        owner = parts[number_idx - 3]
        
        graphql_query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $number) {
              comments(first: 20) {
                nodes {
                  author {
                    login
                  }
                  body
                  createdAt
                }
              }
              reviews(first: 10) {
                nodes {
                  author {
                    login
                  }
                  body
                  state
                }
              }
            }
          }
        }
        """
        
        data = client._execute_graphql(graphql_query, {"owner": owner, "repo": repo, "number": number})
        pr_data = data.get("data", {}).get("repository", {}).get("pullRequest", {})
        
        discussions = []
        
        # Add comments
        for comment in pr_data.get("comments", {}).get("nodes", []):
            discussions.append({
                "type": "comment",
                "author": comment.get("author", {}).get("login", "unknown"),
                "body": comment.get("body", ""),
                "created_at": comment.get("createdAt")
            })
            
        # Add reviews
        for review in pr_data.get("reviews", {}).get("nodes", []):
            if review.get("body"): # Only include reviews with text
                discussions.append({
                    "type": "review",
                    "author": review.get("author", {}).get("login", "unknown"),
                    "body": review.get("body", ""),
                    "state": review.get("state")
                })
                
        return discussions
    except Exception as e:
        log.error(f"Error getting PR discussions: {e}")
        return [{"error": str(e)}]

@cached(cache)
@gr.mcp.tool
def find_similar_bugs(error_message: str) -> List[dict]:
    """
    Find issues with similar error messages.
    
    Args:
        error_message: The error message or stack trace snippet.
    """
    # Extract key terms from error message to form a query
    # This is a heuristic: take the first line or exception type
    query_terms = error_message.split("\n")[0][:100]
    
    # We don't have a specific repo context here, so we might search globally or require a repo
    # For this implementation, let's assume we want to search in popular relevant repos or just return a message
    # that repo is required. However, the prompt implies a general tool.
    # Let's default to a broad search or ask for repo. 
    # To make it useful, let's assume the user might provide "repo:owner/name" in the error message or we just search globally (which is noisy).
    # Better approach: The tool signature should probably include repo, but the prompt signature is just error_message.
    # I will search globally but limit to closed issues (solved bugs) and high relevance.
    
    log.info(f"Finding similar bugs for: {query_terms}")
    
    graphql_query = """
    query($search_query: String!) {
      search(query: $search_query, type: ISSUE, first: 5) {
        edges {
          node {
            ... on Issue {
              title
              url
              state
              repository {
                nameWithOwner
              }
            }
          }
        }
      }
    }
    """
    
    full_query = f"{query_terms} is:issue is:closed"
    
    try:
        data = client._execute_graphql(graphql_query, {"search_query": full_query})
        
        bugs = []
        for edge in data.get("data", {}).get("search", {}).get("edges", []):
            node = edge.get("node", {})
            if not node:
                continue
            
            bugs.append({
                "title": node.get("title"),
                "url": node.get("url"),
                "repo": node.get("repository", {}).get("nameWithOwner"),
                "state": node.get("state")
            })
            
        return bugs
    except Exception as e:
        log.error(f"Error finding similar bugs: {e}")
        return [{"error": str(e)}]

if __name__ == "__main__":
    # Create a simple interface to demonstrate the MCP server
    with gr.Blocks() as demo:
        gr.Markdown("# GitHub MCP Server")
        gr.Markdown("Tools for searching GitHub issues, code, and PRs.")
    
    demo.launch()
