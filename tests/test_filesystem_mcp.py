import unittest
import os
import sys
from pathlib import Path
import tempfile
import shutil
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock environment variable before importing to control workspace
TEST_WORKSPACE = os.path.join(tempfile.gettempdir(), "debuggenie_legacy_test_ws")
with patch.dict(os.environ, {"DEBUGGENIE_WORKSPACE": TEST_WORKSPACE}):
    from mcp_servers.filesystem_mcp import (
        read_file, 
        list_files, 
        get_file_context, 
        validate_path_secure, 
        WORKSPACE_ROOT,
        rate_limiter
    )

class TestFilesystemMCP(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = WORKSPACE_ROOT
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)
        
        # Create some test files
        with open(self.test_dir / "test.txt", "w") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7")
        
        subdir = self.test_dir / "subdir"
        subdir.mkdir()
        with open(subdir / "sub.py", "w") as f:
            f.write("print('hello')")
            
        rate_limiter.requests.clear()

    def tearDown(self):
        # Cleanup
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_read_file(self):
        # Read relative to workspace
        content = read_file("test.txt")
        self.assertIn("Line 1", content)
        
    def test_read_file_security(self):
        # Try to read outside allowed dir
        result = read_file("../outside.txt")
        self.assertIn("Error", result)

    def test_list_files(self):
        files = list_files(".")
        self.assertIn("test.txt", files)
        # Note: list_files returns relative paths now
        # On windows path separator is backslash, but our tool normalizes or returns as is?
        # The tool returns str(full_path.relative_to(dir_path)) which uses OS separator.
        # Let's check for just the filename to be safe or normalize in test
        self.assertTrue(any("test.txt" in f for f in files))
        self.assertTrue(any("sub.py" in f for f in files))

    def test_get_file_context(self):
        context = get_file_context("test.txt", 4, context_lines=1)
        # Should show lines 3, 4, 5
        self.assertIn("Line 3", context)
        self.assertIn("> Line 4", context)
        self.assertIn("Line 5", context)
        self.assertNotIn("Line 1", context)

if __name__ == "__main__":
    unittest.main()
