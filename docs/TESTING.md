# Testing Guide

## Running Tests

### All tests:
```bash
pytest
```

### By category:
```bash
pytest -m unit          # Fast unit tests
pytest -m integration   # Integration tests
pytest -m slow          # Slow running tests
pytest tests/test_security.py  # Security tests only
```

### With coverage:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Skip tests requiring API keys:
```bash
pytest -m "not requires_api"
```

## Writing Tests

### Naming Convention:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Fixtures:
Use fixtures from `conftest.py`:
```python
def test_with_workspace(temp_workspace):
    # temp_workspace is automatically cleaned up
    file = temp_workspace / "test.txt"
    file.write_text("hello")
```

### Async Tests:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### Mocking:
```python
from unittest.mock import patch, AsyncMock

@patch('module.external_api_call')
def test_with_mock(mock_api):
    mock_api.return_value = "mocked response"
    # test code
```

## Coverage Goals

- **Critical paths**: 90%+
- **Overall**: 70%+
- **Security code**: 95%+

## CI/CD

Tests run automatically on:
- Every push
- Every pull request
- Before merging to main

Failed tests block merges.
