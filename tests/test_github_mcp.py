import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_servers.github_mcp import search_issues, get_pr_discussions, GitHubClient

class TestGitHubMCP(unittest.TestCase):
    
    @patch('mcp_servers.github_mcp.client._execute_graphql')
    def test_search_issues(self, mock_graphql):
        # Mock response
        mock_graphql.return_value = {
            "data": {
                "search": {
                    "edges": [
                        {
                            "node": {
                                "title": "Test Issue",
                                "url": "http://github.com/test/issue/1",
                                "bodyText": "This is a test issue body.",
                                "state": "OPEN",
                                "labels": {"nodes": [{"name": "bug"}]},
                                "comments": {"totalCount": 2}
                            }
                        }
                    ]
                }
            }
        }
        
        results = search_issues("test", "owner/repo")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Issue")
        self.assertEqual(results[0]['labels'], ["bug"])

    @patch('mcp_servers.github_mcp.client._execute_graphql')
    def test_get_pr_discussions(self, mock_graphql):
        mock_graphql.return_value = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "comments": {
                            "nodes": [
                                {
                                    "author": {"login": "user1"},
                                    "body": "LGTM",
                                    "createdAt": "2023-01-01T00:00:00Z"
                                }
                            ]
                        },
                        "reviews": {
                            "nodes": []
                        }
                    }
                }
            }
        }
        
        results = get_pr_discussions("https://github.com/owner/repo/pull/123")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['body'], "LGTM")

if __name__ == "__main__":
    unittest.main()
