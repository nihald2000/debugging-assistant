import pytest
from pathlib import Path
import os
from unittest.mock import patch
import shutil
import tempfile
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variable before importing to control workspace
TEST_WORKSPACE = os.path.join(tempfile.gettempdir(), "debuggenie_security_test_ws")
with patch.dict(os.environ, {"DEBUGGENIE_WORKSPACE": TEST_WORKSPACE}):
    from mcp_servers.filesystem_mcp import (
        validate_path_secure, 
        read_file, 
        list_files, 
        SecurityError, 
        WORKSPACE_ROOT,
        rate_limiter,
        BLACKLISTED_PATTERNS
    )

@pytest.mark.unit
class TestSecurityValidation:
    
    def setup_method(self):
        # Create test workspace
        self.test_ws = WORKSPACE_ROOT
        if self.test_ws.exists():
            shutil.rmtree(self.test_ws)
        self.test_ws.mkdir(parents=True)
        rate_limiter.requests.clear()

    def teardown_method(self):
        if self.test_ws.exists():
            shutil.rmtree(self.test_ws)
    
    def test_path_traversal_variations(self):
        """Test various path traversal attack patterns."""
        attack_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "./../.../../etc/shadow",
            "foo/../../etc/passwd",
            "./../../etc/passwd",
        ]
        
        for pattern in attack_patterns:
            with pytest.raises(SecurityError):
                validate_path_secure(pattern)
    
    def test_blacklist_patterns(self):
        """Test all blacklisted patterns are blocked."""
        # Create files matching blacklist
        test_files = [
            ".env",
            ".env.local",
            "secrets/api_key.txt",
            "id_rsa",
            ".ssh/id_rsa",
            "private.pem",
        ]
        
        for file_path in test_files:
            file_full = self.test_ws / file_path
            file_full.parent.mkdir(parents=True, exist_ok=True)
            file_full.write_text("secret")
            
            with pytest.raises(SecurityError, match="blacklisted"):
                validate_path_secure(file_path)
    
    def test_symlink_escape_blocked(self):
        """Test symlinks pointing outside workspace are blocked."""
        # Create symlink to outside directory
        # Use a temporary file outside workspace
        with tempfile.NamedTemporaryFile(delete=False) as outside_file:
            outside_path = Path(outside_file.name)
            outside_path.write_text("secret")
        
        try:
            symlink = self.test_ws / "link.txt"
            try:
                symlink.symlink_to(outside_path)
            except OSError:
                pytest.skip("Symlinks not supported on this OS/user")
            
            with pytest.raises(SecurityError, match="escapes workspace"):
                validate_path_secure("link.txt")
        finally:
            if outside_path.exists():
                os.unlink(outside_path)
    
    def test_file_size_limit(self):
        """Test large files are rejected."""
        # Create 11MB file (exceeds 10MB limit)
        large_file = self.test_ws / "large.bin"
        # Create sparse file to save disk space/time if possible, but python write is explicit
        # Writing 11MB is fast enough
        with open(large_file, "wb") as f:
            f.seek(11 * 1024 * 1024 - 1)
            f.write(b"\0")
        
        with pytest.raises(SecurityError, match="too large"):
            validate_path_secure("large.bin")

    def test_rate_limiting(self):
        """Test rate limiting."""
        client_id = "test_client"
        # Consume all tokens
        for _ in range(100):
            rate_limiter.check_rate_limit(client_id)
            
        # Next request should fail
        assert rate_limiter.check_rate_limit(client_id) is False
        
        # Tool should return error
        result = read_file("safe.txt", client_id=client_id)
        assert "Rate limit exceeded" in result

