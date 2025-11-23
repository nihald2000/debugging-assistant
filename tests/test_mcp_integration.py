import pytest
from pathlib import Path
from unittest.mock import patch
from mcp_servers.filesystem_mcp import (
    read_file, list_files, validate_path_secure, SecurityError
)

@pytest.mark.integration
class TestFilesystemMCP:
    
    def test_read_file_success(self, temp_workspace):
        """Test reading a valid file."""
        # Create test file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Hello World")
        
        # Mock WORKSPACE_ROOT
        with patch('mcp_servers.filesystem_mcp.WORKSPACE_ROOT', temp_workspace):
            content = read_file("test.txt")
            assert content == "Hello World"
    
    def test_read_file_security_path_traversal(self, temp_workspace):
        """Test path traversal is blocked."""
        with patch('mcp_servers.filesystem_mcp.WORKSPACE_ROOT', temp_workspace):
            with pytest.raises(SecurityError, match="escapes workspace"):
                validate_path_secure("../../etc/passwd")
    
    def test_read_file_security_blacklist(self, temp_workspace):
        """Test blacklisted files are blocked."""
        # Create .env file
        env_file = temp_workspace / ".env"
        env_file.write_text("SECRET_KEY=123")
        
        with patch('mcp_servers.filesystem_mcp.WORKSPACE_ROOT', temp_workspace):
            with pytest.raises(SecurityError, match="blacklisted"):
                validate_path_secure(".env")
    
    def test_list_files_with_pattern(self, temp_workspace):
        """Test file listing with glob pattern."""
        # Create files
        (temp_workspace / "test.py").write_text("print('hello')")
        (temp_workspace / "test.txt").write_text("hello")
        (temp_workspace / "README.md").write_text("# Test")
        
        with patch('mcp_servers.filesystem_mcp.WORKSPACE_ROOT', temp_workspace):
            py_files = list_files(".", "*.py")
            assert "test.py" in py_files
            assert "test.txt" not in py_files
    
    def test_rate_limiting(self, temp_workspace):
        """Test rate limiter blocks excessive requests."""
        from mcp_servers.filesystem_mcp import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # First 5 should succeed
        for i in range(5):
            assert limiter.check_rate_limit("test_client") is True
        
        # 6th should fail
        assert limiter.check_rate_limit("test_client") is False

@pytest.mark.integration
@pytest.mark.slow
class TestGitHubMCP:
    
    @pytest.mark.requires_api
    def test_search_issues_real_api(self):
        """Test GitHub search with real API (requires token)."""
        import os
        if not os.getenv("GITHUB_TOKEN"):
            pytest.skip("GITHUB_TOKEN not set")
        
        from mcp_servers.github_mcp import search_issues
        
        # Search a known repo
        results = search_issues("bug", "torvalds/linux")
        
        assert isinstance(results, list)
        if results and "error" not in results[0]:
            assert "title" in results[0]
            assert "url" in results[0]
    
    def test_search_issues_mocked(self):
        """Test GitHub search with mocked API."""
        with patch('mcp_servers.github_mcp.client._execute_graphql') as mock:
            mock.return_value = {
                "data": {
                    "search": {
                        "edges": [
                            {
                                "node": {
                                    "title": "Test Issue",
                                    "url": "https://github.com/test/repo/issues/1",
                                    "bodyText": "Test body",
                                    "state": "OPEN",
                                    "labels": {"nodes": []},
                                    "comments": {"totalCount": 0}
                                }
                            }
                        ]
                    }
                }
            }
            
            from mcp_servers.github_mcp import search_issues
            results = search_issues("test", "test/repo")
            
            assert len(results) == 1
            assert results[0]["title"] == "Test Issue"
