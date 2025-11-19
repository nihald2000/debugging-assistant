import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_servers.web_search_mcp import search_stack_overflow, search_web, get_page_content, extract_code_snippets

class TestWebSearchMCP(unittest.TestCase):
    
    @patch('requests.get')
    def test_search_stack_overflow(self, mock_get):
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Test Error",
                    "link": "http://stackoverflow.com/q/1",
                    "is_answered": True,
                    "score": 100,
                    "body": "This is the body"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        results = search_stack_overflow("python error")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Error")
        self.assertTrue(results[0]['has_accepted_answer'])

    @patch('mcp_servers.web_search_mcp.DDGS')
    def test_search_web(self, mock_ddgs):
        # Mock DDGS context manager
        mock_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {"title": "Result 1", "href": "http://example.com", "body": "Snippet 1"}
        ]
        
        results = search_web("query")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Result 1")

    @patch('requests.get')
    def test_get_page_content(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Hello World</p></body></html>"
        mock_get.return_value = mock_response
        
        content = get_page_content("http://example.com")
        self.assertIn("Hello World", content)

    @patch('requests.get')
    def test_extract_code_snippets(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><pre>print('hello')</pre></body></html>"
        mock_get.return_value = mock_response
        
        snippets = extract_code_snippets("http://example.com")
        self.assertEqual(len(snippets), 1)
        self.assertIn("print('hello')", snippets[0])

if __name__ == "__main__":
    unittest.main()
