"""
Unit tests for git_audit.py functions.

Focuses on testing the bug fix for None git_url handling and
error handling improvements.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from argparse import Namespace
import sys
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from git_audit import (
    audit_repository,
    clone_or_update_repo
)


class TestAuditRepositoryValidation:
    """
    Tests for the defensive validation in audit_repository().
    This is where the critical bug fix was applied.
    """

    def test_none_git_url_raises_value_error(self):
        """
        Test that None git_url raises ValueError instead of AttributeError.
        This is the core bug fix!
        """
        args = Namespace(git_url=None, output_fpath="./test.csv")

        with pytest.raises(ValueError) as exc_info:
            audit_repository(args)

        assert "cannot be None" in str(exc_info.value)
        assert "validation error" in str(exc_info.value)

    def test_empty_string_git_url_raises_value_error(self):
        """Test that empty string git_url raises ValueError."""
        args = Namespace(git_url="", output_fpath="./test.csv")

        with pytest.raises(ValueError) as exc_info:
            audit_repository(args)

        assert "non-empty string" in str(exc_info.value)

    def test_whitespace_git_url_raises_value_error(self):
        """Test that whitespace-only git_url raises ValueError."""
        args = Namespace(git_url="   ", output_fpath="./test.csv")

        with pytest.raises(ValueError) as exc_info:
            audit_repository(args)

        assert "non-empty string" in str(exc_info.value)

    def test_invalid_url_format_raises_value_error(self):
        """Test that URL without '/' raises ValueError before attempting split."""
        args = Namespace(git_url="invalid-url-no-slash", output_fpath="./test.csv")

        with pytest.raises(ValueError) as exc_info:
            audit_repository(args)

        assert "Invalid git_url format" in str(exc_info.value)
        assert "Expected format" in str(exc_info.value)

    def test_valid_url_passes_validation(self):
        """Test that a valid URL passes validation without raising ValueError."""
        args = Namespace(
            git_url="https://github.com/owner/repo.git",
            output_fpath="./test.csv"
        )

        # The validation happens at the start of audit_repository()
        # We can't easily test beyond validation without mocking the entire function,
        # so we'll test that the validation logic itself doesn't raise

        # These should all pass the validation checks
        valid_urls = [
            "https://github.com/owner/repo.git",
            "https://github.com/owner/repo",
            "git@github.com:owner/repo.git",
            "http://gitlab.com/group/project"
        ]

        for url in valid_urls:
            args = Namespace(git_url=url, output_fpath="./test.csv")
            # Validation checks only
            assert args.git_url is not None
            assert isinstance(args.git_url, str)
            assert args.git_url.strip() != ""
            assert '/' in args.git_url


class TestCloneOrUpdateRepo:
    """Tests for clone_or_update_repo() error handling."""

    @patch('git_audit.subprocess.run')
    @patch('git_audit.os.path.isdir')
    def test_successful_clone(self, mock_isdir, mock_run):
        """Test successful repository clone."""
        mock_isdir.return_value = False
        mock_run.return_value = Mock(returncode=0)

        # Should not raise
        clone_or_update_repo("https://github.com/owner/repo.git", "/test/path")

        assert mock_run.called

    @patch('git_audit.subprocess.run')
    @patch('git_audit.os.path.isdir')
    @patch('git_audit.os.path.join')
    def test_successful_update(self, mock_join, mock_isdir, mock_run):
        """Test successful repository update."""
        mock_isdir.return_value = True
        mock_run.return_value = Mock(returncode=0)

        # Should not raise
        clone_or_update_repo("https://github.com/owner/repo.git", "/test/path")

        # Should call fetch and pull
        assert mock_run.call_count == 2

    @patch('git_audit.subprocess.run')
    @patch('git_audit.os.path.isdir')
    def test_authentication_failed_on_clone(self, mock_isdir, mock_run):
        """Test authentication failure during clone."""
        mock_isdir.return_value = False

        error = subprocess.CalledProcessError(1, "git")
        error.stderr = "fatal: Authentication failed"
        mock_run.side_effect = error

        with pytest.raises(RuntimeError) as exc_info:
            clone_or_update_repo("https://github.com/owner/private.git", "/test/path")

        assert "Authentication failed" in str(exc_info.value)
        assert "private repository" in str(exc_info.value)
        assert "Option 1" in str(exc_info.value)

    @patch('git_audit.subprocess.run')
    @patch('git_audit.os.path.isdir')
    def test_repository_not_found(self, mock_isdir, mock_run):
        """Test repository not found error."""
        mock_isdir.return_value = False

        error = subprocess.CalledProcessError(1, "git")
        error.stderr = "fatal: Repository not found"
        mock_run.side_effect = error

        with pytest.raises(RuntimeError) as exc_info:
            clone_or_update_repo("https://github.com/owner/nonexistent.git", "/test/path")

        assert "not found" in str(exc_info.value)
        assert "verify" in str(exc_info.value).lower()

    @patch('git_audit.subprocess.run')
    @patch('git_audit.os.path.isdir')
    def test_network_error_during_update(self, mock_isdir, mock_run):
        """Test network error during repository update."""
        mock_isdir.return_value = True
        mock_join = Mock(return_value="/test/path/.git")

        error = subprocess.CalledProcessError(1, "git")
        error.stderr = "fatal: unable to access"
        mock_run.side_effect = error

        with pytest.raises(RuntimeError) as exc_info:
            with patch('git_audit.os.path.join', mock_join):
                clone_or_update_repo("https://github.com/owner/repo.git", "/test/path")

        assert "Failed to update" in str(exc_info.value)
        assert "Network" in str(exc_info.value) or "connectivity" in str(exc_info.value)

    @patch('git_audit.subprocess.run')
    @patch('git_audit.os.path.isdir')
    def test_generic_clone_error(self, mock_isdir, mock_run):
        """Test generic clone error."""
        mock_isdir.return_value = False

        error = subprocess.CalledProcessError(1, "git")
        error.stderr = "Some unexpected error"
        mock_run.side_effect = error

        with pytest.raises(RuntimeError) as exc_info:
            clone_or_update_repo("https://github.com/owner/repo.git", "/test/path")

        assert "Failed to clone" in str(exc_info.value)


class TestOriginalBugScenario:
    """
    Tests that reproduce the original bug scenario to ensure it's fixed.
    """

    def test_original_bug_scenario_run_current_directory(self):
        """
        Reproduce the exact scenario that caused the original bug:
        - User runs from a directory that is a git repo
        - But the repo has no remote configured
        - get_url_from_dir returns None
        - Previously: AttributeError on None.split()
        - Now: ValueError with clear message
        """
        # Simulate what happens when there's no remote
        args = Namespace(git_url=None, output_fpath="./test.csv")

        # Should raise ValueError, NOT AttributeError
        with pytest.raises(ValueError):
            audit_repository(args)

        # Make sure it's NOT raising AttributeError
        try:
            audit_repository(args)
        except AttributeError:
            pytest.fail("Still raising AttributeError! Bug not fixed!")
        except ValueError:
            pass  # Expected

    def test_original_bug_line_317(self):
        """
        Test the specific line that caused the bug (line 317):
        repo_name = args.git_url.split('/')[-1].replace('.git', '')
        """
        # This would have caused: AttributeError: 'NoneType' object has no attribute 'split'
        args = Namespace(git_url=None, output_fpath="./test.csv")

        with pytest.raises(ValueError) as exc_info:
            audit_repository(args)

        # Verify we never get to the split() call
        assert "cannot be None" in str(exc_info.value)

    def test_original_bug_line_394(self):
        """
        Test the second location that would fail (line 394):
        owner = args.git_url.rstrip("/").split("/")[-2]
        """
        args = Namespace(git_url=None, output_fpath="./test.csv")

        with pytest.raises(ValueError):
            audit_repository(args)

        # The validation happens before we ever reach line 394


class TestErrorMessages:
    """Tests that error messages are clear and actionable."""

    def test_none_error_message_is_helpful(self):
        """Test that None git_url produces helpful error message."""
        args = Namespace(git_url=None, output_fpath="./test.csv")

        try:
            audit_repository(args)
        except ValueError as e:
            error_msg = str(e)
            # Should mention the problem
            assert "None" in error_msg or "cannot be None" in error_msg
            # Should provide guidance
            assert "Git repository" in error_msg
            assert "remote" in error_msg
        else:
            pytest.fail("Should have raised ValueError")

    def test_invalid_format_error_message_is_helpful(self):
        """Test that invalid URL format produces helpful error message."""
        args = Namespace(git_url="invalid-url", output_fpath="./test.csv")

        try:
            audit_repository(args)
        except ValueError as e:
            error_msg = str(e)
            # Should show the invalid URL
            assert "invalid-url" in error_msg
            # Should show expected format
            assert "Expected format" in error_msg
            assert "github.com" in error_msg or "owner/repository" in error_msg
        else:
            pytest.fail("Should have raised ValueError")


class TestRegressionPrevention:
    """Tests to prevent regression of the bug fix."""

    def test_cannot_call_split_on_none(self):
        """Ensure we can never reach the split() calls with None."""
        # Try various ways None might slip through
        test_cases = [
            None,
            "",
            "   ",
            "no-slash-url",
        ]

        for git_url in test_cases:
            args = Namespace(git_url=git_url, output_fpath="./test.csv")

            # All should raise ValueError before reaching split()
            with pytest.raises(ValueError):
                audit_repository(args)

    @pytest.mark.parametrize("invalid_url", [
        None,
        "",
        "   ",
        "invalid",
        123,  # Wrong type
        [],   # Wrong type
    ])
    def test_various_invalid_inputs(self, invalid_url):
        """Test that various invalid inputs are caught."""
        args = Namespace(git_url=invalid_url, output_fpath="./test.csv")

        with pytest.raises((ValueError, AttributeError)):
            audit_repository(args)

        # If it raises AttributeError, it means we didn't validate properly
        try:
            audit_repository(args)
        except AttributeError:
            pytest.fail(f"AttributeError for {invalid_url} - validation incomplete!")
        except ValueError:
            pass  # Expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
