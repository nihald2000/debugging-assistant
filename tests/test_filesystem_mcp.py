import unittest
import os
import sys
from pathlib import Path
import tempfile
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_servers.filesystem_mcp import read_file, list_files, get_file_context, validate_path, ALLOWED_DIRECTORIES

class TestFilesystemMCP(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        # Add test dir to allowed directories for validation logic
        self.original_allowed = list(ALLOWED_DIRECTORIES)
        ALLOWED_DIRECTORIES.append(Path(self.test_dir).resolve())
        
        # Create some test files
        with open(os.path.join(self.test_dir, "test.txt"), "w") as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7")
        
        os.makedirs(os.path.join(self.test_dir, "subdir"))
        with open(os.path.join(self.test_dir, "subdir", "sub.py"), "w") as f:
            f.write("print('hello')")

    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.test_dir)
        ALLOWED_DIRECTORIES.clear()
        ALLOWED_DIRECTORIES.extend(self.original_allowed)

    def test_read_file(self):
        content = read_file(os.path.join(self.test_dir, "test.txt"))
        self.assertIn("Line 1", content)
        
    def test_read_file_security(self):
        # Try to read outside allowed dir (assuming /etc/hosts or C:\Windows exists, but safer to just use parent of temp)
        parent = Path(self.test_dir).parent
        result = read_file(str(parent))
        self.assertTrue(result.startswith("Error"))

    def test_list_files(self):
        files = list_files(self.test_dir)
        self.assertIn("test.txt", files)
        self.assertIn(os.path.join("subdir", "sub.py"), files)

    def test_get_file_context(self):
        context = get_file_context(os.path.join(self.test_dir, "test.txt"), 4, context_lines=1)
        # Should show lines 3, 4, 5
        self.assertIn("Line 3", context)
        self.assertIn("> Line 4", context)
        self.assertIn("Line 5", context)
        self.assertNotIn("Line 1", context)

if __name__ == "__main__":
    unittest.main()
