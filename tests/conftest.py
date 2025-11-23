import pytest
import os
import shutil
import tempfile
from unittest.mock import Mock
from pathlib import Path
from tests.fixtures.mock_responses import CLAUDE_ANALYSIS_SUCCESS

@pytest.fixture
def mock_api_config():
    """Mock API configuration."""
    config = Mock()
    config.openai_api_key = "sk-test-openai"
    config.anthropic_api_key = "sk-test-anthropic"
    config.gemini_api_key = "sk-test-gemini"
    config.github_token = "ghp-test"
    return config

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for file operations."""
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir).resolve()
    yield workspace
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_error():
    """Sample error text for testing."""
    return """
    Traceback (most recent call last):
      File "app.py", line 42, in <module>
        data = json.loads(request_body)
      File "/usr/lib/python3.9/json/__init__.py", line 346, in loads
        return _default_decoder.decode(s)
      File "/usr/lib/python3.9/json/decoder.py", line 337, in decode
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
      File "/usr/lib/python3.9/json/decoder.py", line 355, in raw_decode
        raise JSONDecodeError("Expecting value", s, idx)
    json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
    """

@pytest.fixture
def mock_claude_response():
    """Mock response from Claude agent."""
    return CLAUDE_ANALYSIS_SUCCESS
