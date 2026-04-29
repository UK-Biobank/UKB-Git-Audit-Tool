# Test Suite for Git Audit Tool

This directory contains the test suite for the Git Audit Tool, with comprehensive unit tests using pytest.

## Overview

The test suite focuses on:
1. **Environment validation** - Testing git installation, repository validation, URL validation
2. **Main execution functions** - Testing all 4 execution modes with proper validation
3. **Bug fix verification** - Ensuring the AttributeError bug is fixed and won't regress
4. **Error handling** - Verifying clear, actionable error messages

## Test Files

- **`test_environment_validator.py`** - Tests for the validation module (68 tests)
  - Git installation checks
  - Repository validation
  - URL format validation
  - Repository access testing
  - Mocked subprocess calls to avoid dependencies

- **`test_main.py`** - Tests for main execution functions (25 tests)
  - `get_url_from_dir()` - Including the None return bug scenario
  - `extract_owner_repo()` - URL parsing
  - `run_current_directory()`, `run_from_directory()`, `run_from_url()` - All execution modes
  - Input validation at each step

- **`test_git_audit.py`** - Tests for audit logic and bug fix (30 tests)
  - **Critical**: Tests that None git_url raises ValueError, not AttributeError
  - Defensive validation in `audit_repository()`
  - Error handling in `clone_or_update_repo()`
  - Regression prevention tests

## Installation

This project uses Poetry for dependency management. Install all dependencies including test dependencies:

```bash
poetry install
```

This installs all production dependencies plus dev dependencies (pytest, pytest-mock).

## Running Tests

### Run all tests:
```bash
poetry run pytest
```

### Run with verbose output:
```bash
poetry run pytest -v
```

### Run specific test file:
```bash
poetry run pytest tests/test_environment_validator.py
poetry run pytest tests/test_main.py
poetry run pytest tests/test_git_audit.py
```

### Run specific test class:
```bash
poetry run pytest tests/test_git_audit.py::TestAuditRepositoryValidation
```

### Run specific test:
```bash
poetry run pytest tests/test_git_audit.py::TestAuditRepositoryValidation::test_none_git_url_raises_value_error
```

### Run with coverage (requires pytest-cov):
```bash
poetry add --group dev pytest-cov
poetry run pytest --cov=src --cov-report=html
```
Then open `htmlcov/index.html` to see coverage report.

## Test Strategy

### Unit Tests with Mocking

Most tests use mocking to avoid external dependencies:

```python
@patch('environment_validator.subprocess.run')
def test_git_installed(mock_run):
    mock_run.return_value = Mock(stdout="git version 2.40.0")
    installed, msg = check_git_installed()
    assert installed is True
```

**Why mock?**
- Tests run fast (no actual subprocess calls)
- Tests are isolated (don't depend on system state)
- Tests are deterministic (same result every time)
- Can test error conditions (git not installed, network failure, etc.)

### Integration Tests

Some tests are marked as integration tests and use real git commands:

```python
@pytest.mark.skipif(not Path(".git").exists(), reason="Not in a git repository")
def test_real_git_check(self):
    installed, msg = check_git_installed()
    assert installed is True
```

These are skipped if not in a git repository.

## Key Tests for the Bug Fix

The original bug: `AttributeError: 'NoneType' object has no attribute 'split'`

### Test that verifies the fix:

```python
def test_none_git_url_raises_value_error(self):
    """
    Test that None git_url raises ValueError instead of AttributeError.
    This is the core bug fix!
    """
    args = Namespace(git_url=None, output_fpath="./test.csv")

    with pytest.raises(ValueError) as exc_info:
        audit_repository(args)

    assert "cannot be None" in str(exc_info.value)
```

### Regression prevention:

```python
def test_cannot_call_split_on_none(self):
    """Ensure we can never reach the split() calls with None."""
    test_cases = [None, "", "   ", "no-slash-url"]

    for git_url in test_cases:
        args = Namespace(git_url=git_url, output_fpath="./test.csv")
        with pytest.raises(ValueError):
            audit_repository(args)
```

## Test Coverage

To check which lines are covered by tests:

```bash
pytest --cov=src --cov-report=term-missing
```

This shows which lines are NOT covered by tests.

Current coverage target: **80%+** for critical modules:
- `environment_validator.py` - Should be ~90%
- `main.py` validation logic - Should be ~85%
- `git_audit.py` validation logic - Should be ~80%

## Writing New Tests

### Template for new test:

```python
class TestNewFeature:
    """Tests for new feature."""

    @patch('module.function_to_mock')
    def test_success_case(self, mock_func):
        """Test successful execution."""
        # Arrange
        mock_func.return_value = "expected"

        # Act
        result = function_under_test()

        # Assert
        assert result == "expected"
        mock_func.assert_called_once()

    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(ValueError) as exc_info:
            function_under_test(invalid_input)

        assert "helpful message" in str(exc_info.value)
```

### Best Practices:

1. **Test one thing per test** - Each test should verify one specific behavior
2. **Use descriptive names** - `test_none_git_url_raises_value_error` not `test_error`
3. **Mock external dependencies** - Don't call real subprocess, network, filesystem
4. **Test both success and failure** - Happy path AND error cases
5. **Verify error messages** - Check that errors are clear and actionable
6. **Use parametrize for similar tests**:
   ```python
   @pytest.mark.parametrize("invalid_url", [None, "", "invalid"])
   def test_invalid_urls(self, invalid_url):
       # Test all invalid URLs
   ```

## Continuous Integration

These tests can be run in CI/CD pipelines:

### GitHub Actions example:
```yaml
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    pip install -r requirements-test.txt

- name: Run tests
  run: pytest --cov=src --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests fail with import errors:
```
ModuleNotFoundError: No module named 'environment_validator'
```

**Solution**: Tests add `src/` to path automatically. Ensure you're running from project root.

### Mocks not working:
```
AssertionError: Expected call not found
```

**Solution**: Check the patch path. Use the path where the function is *used*, not where it's *defined*.

```python
# Wrong: @patch('subprocess.run')
# Right: @patch('environment_validator.subprocess.run')
```

### Unicode errors on Windows:
Tests include UTF-8 configuration for Windows console. If issues persist:
```bash
set PYTHONIOENCODING=utf-8
pytest
```

## Contributing

When adding new features:
1. Write tests FIRST (TDD approach) or alongside the feature
2. Ensure tests pass: `pytest`
3. Check coverage: `pytest --cov=src`
4. Add integration tests for complex scenarios

## Test Metrics

Run tests to see current metrics:
```bash
pytest -v --tb=short
```

Expected output:
```
tests/test_environment_validator.py::TestCheckGitInstalled::test_git_installed_success PASSED
tests/test_environment_validator.py::TestCheckGitInstalled::test_git_not_in_path PASSED
...
======================== X passed in Y.YYs ========================
```

Target: **All tests pass** ✓
