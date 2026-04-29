"""
Unit tests for environment_validator module.

These tests use mocking to avoid depending on actual git installation,
filesystem state, or network access.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import subprocess
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from environment_validator import (
    check_git_installed,
    validate_git_repository,
    get_repository_info,
    validate_git_url,
    check_repository_access,
    display_environment_validation
)


class TestCheckGitInstalled:
    """Tests for check_git_installed()"""

    @patch('environment_validator.subprocess.run')
    def test_git_installed_success(self, mock_run):
        """Test when git is installed and working."""
        mock_run.return_value = Mock(
            stdout="git version 2.40.0",
            returncode=0
        )

        installed, msg = check_git_installed()

        assert installed is True
        assert msg == ""
        mock_run.assert_called_once_with(
            ["git", "--version"],
            capture_output=True,
            text=True,
            check=True
        )

    @patch('environment_validator.subprocess.run')
    def test_git_not_in_path(self, mock_run):
        """Test when git is not in PATH."""
        mock_run.side_effect = FileNotFoundError()

        installed, msg = check_git_installed()

        assert installed is False
        assert "not installed" in msg or "not found" in msg

    @patch('environment_validator.subprocess.run')
    def test_git_command_fails(self, mock_run):
        """Test when git command fails to execute."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        installed, msg = check_git_installed()

        assert installed is False
        assert "failed" in msg.lower()


class TestValidateGitRepository:
    """Tests for validate_git_repository()"""

    @patch('environment_validator.subprocess.run')
    @patch('environment_validator.Path')
    def test_valid_git_repository(self, mock_path, mock_run):
        """Test validation of a valid git repository."""
        # Mock .git directory exists
        mock_git_dir = MagicMock()
        mock_git_dir.exists.return_value = True
        mock_path.return_value.__truediv__.return_value = mock_git_dir

        # Mock git command success
        mock_run.return_value = Mock(
            stdout="true\n",
            returncode=0
        )

        is_valid, msg = validate_git_repository("/fake/path")

        assert is_valid is True
        assert msg == ""

    @patch('environment_validator.subprocess.run')
    @patch('environment_validator.Path')
    def test_no_git_directory(self, mock_path, mock_run):
        """Test when .git directory doesn't exist."""
        # Mock .git directory does not exist
        mock_git_dir = MagicMock()
        mock_git_dir.exists.return_value = False
        mock_path.return_value.__truediv__.return_value = mock_git_dir

        is_valid, msg = validate_git_repository("/fake/path")

        assert is_valid is False
        assert "not a Git repository" in msg
        # Should not call git command if .git dir doesn't exist
        mock_run.assert_not_called()

    @patch('environment_validator.subprocess.run')
    @patch('environment_validator.Path')
    def test_git_command_fails(self, mock_path, mock_run):
        """Test when git command fails."""
        # Mock .git directory exists
        mock_git_dir = MagicMock()
        mock_git_dir.exists.return_value = True
        mock_path.return_value.__truediv__.return_value = mock_git_dir

        # Mock git command fails
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        is_valid, msg = validate_git_repository("/fake/path")

        assert is_valid is False
        assert "validation failed" in msg.lower()


class TestGetRepositoryInfo:
    """Tests for get_repository_info()"""

    @patch('environment_validator.validate_git_repository')
    @patch('environment_validator.subprocess.run')
    @patch('environment_validator.Path')
    def test_complete_repository_info(self, mock_path, mock_run, mock_validate):
        """Test getting complete info from a valid repository."""
        # Mock path resolution
        mock_path.return_value.resolve.return_value = "/absolute/path"

        # Mock valid git repository
        mock_validate.return_value = (True, "")

        # Mock git commands
        def run_side_effect(cmd, **kwargs):
            if "branch" in cmd:
                return Mock(stdout="main\n")
            elif "remote" in cmd:
                return Mock(stdout="https://github.com/owner/repo.git\n")
            return Mock(stdout="")

        mock_run.side_effect = run_side_effect

        info = get_repository_info("/fake/path")

        assert info["current_dir"] == "/absolute/path"
        assert info["is_git_repo"] is True
        assert info["has_remote"] is True
        assert info["remote_url"] == "https://github.com/owner/repo.git"
        assert info["branch_name"] == "main"

    @patch('environment_validator.validate_git_repository')
    @patch('environment_validator.Path')
    def test_not_a_git_repository(self, mock_path, mock_validate):
        """Test getting info from a non-git directory."""
        mock_path.return_value.resolve.return_value = "/absolute/path"
        mock_validate.return_value = (False, "Not a git repo")

        info = get_repository_info("/fake/path")

        assert info["is_git_repo"] is False
        assert info["has_remote"] is False
        assert info["remote_url"] == ""
        assert info["branch_name"] == ""

    @patch('environment_validator.validate_git_repository')
    @patch('environment_validator.subprocess.run')
    @patch('environment_validator.Path')
    def test_no_remote_configured(self, mock_path, mock_run, mock_validate):
        """Test repository with no remote."""
        mock_path.return_value.resolve.return_value = "/absolute/path"
        mock_validate.return_value = (True, "")

        def run_side_effect(cmd, **kwargs):
            if "branch" in cmd:
                return Mock(stdout="main\n")
            elif "remote" in cmd:
                raise subprocess.CalledProcessError(1, "git")

        mock_run.side_effect = run_side_effect

        info = get_repository_info("/fake/path")

        assert info["is_git_repo"] is True
        assert info["has_remote"] is False
        assert info["remote_url"] == ""


class TestValidateGitUrl:
    """Tests for validate_git_url()"""

    def test_valid_url(self):
        """Test validation of a valid URL."""
        is_valid, msg = validate_git_url("https://github.com/owner/repo")

        assert is_valid is True
        assert msg == ""

    def test_none_url(self):
        """Test validation of None."""
        is_valid, msg = validate_git_url(None)

        assert is_valid is False
        assert "None" in msg

    def test_empty_string(self):
        """Test validation of empty string."""
        is_valid, msg = validate_git_url("")

        assert is_valid is False
        assert "Empty" in msg

    def test_whitespace_only(self):
        """Test validation of whitespace-only string."""
        is_valid, msg = validate_git_url("   ")

        assert is_valid is False
        assert "Empty" in msg

    def test_invalid_type(self):
        """Test validation of non-string type."""
        is_valid, msg = validate_git_url(123)

        assert is_valid is False
        assert "must be a string" in msg

    def test_no_slash(self):
        """Test URL without slash (can't split owner/repo)."""
        is_valid, msg = validate_git_url("invalid-url-no-slash")

        assert is_valid is False
        assert "Invalid URL format" in msg

    @pytest.mark.parametrize("url", [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo.git",
        "git@github.com:owner/repo.git",
        "http://gitlab.com/group/subgroup/project",
    ])
    def test_various_valid_formats(self, url):
        """Test various valid URL formats."""
        is_valid, msg = validate_git_url(url)

        assert is_valid is True
        assert msg == ""


class TestTestRepositoryAccess:
    """Tests for check_repository_access()"""

    @patch('environment_validator.subprocess.run')
    def test_accessible_repository(self, mock_run):
        """Test accessing a public, accessible repository."""
        mock_run.return_value = Mock(
            stdout="ref: refs/heads/main\n",
            returncode=0
        )

        is_accessible, msg = check_repository_access("https://github.com/owner/repo")

        assert is_accessible is True
        assert msg == ""
        mock_run.assert_called_once()

    @patch('environment_validator.subprocess.run')
    def test_authentication_failed(self, mock_run):
        """Test private repository requiring authentication."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128,
            "git",
            stderr="fatal: Authentication failed"
        )

        is_accessible, msg = check_repository_access("https://github.com/owner/private-repo")

        assert is_accessible is False
        assert "Authentication failed" in msg
        assert "private repository" in msg.lower()
        assert "Option 1" in msg

    @patch('environment_validator.subprocess.run')
    def test_repository_not_found(self, mock_run):
        """Test non-existent repository."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128,
            "git",
            stderr="fatal: repository not found"
        )

        is_accessible, msg = check_repository_access("https://github.com/owner/nonexistent")

        assert is_accessible is False
        assert "not found" in msg.lower()

    @patch('environment_validator.subprocess.run')
    def test_permission_denied(self, mock_run):
        """Test permission denied (403)."""
        mock_run.side_effect = subprocess.CalledProcessError(
            128,
            "git",
            stderr="fatal: HTTP request failed with 403"
        )

        is_accessible, msg = check_repository_access("https://github.com/owner/forbidden")

        assert is_accessible is False
        assert "Permission denied" in msg

    @patch('environment_validator.subprocess.run')
    def test_timeout(self, mock_run):
        """Test connection timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        is_accessible, msg = check_repository_access("https://github.com/owner/repo")

        assert is_accessible is False
        assert "timeout" in msg.lower()

    @patch('environment_validator.subprocess.run')
    def test_git_not_installed(self, mock_run):
        """Test when git is not installed."""
        mock_run.side_effect = FileNotFoundError()

        is_accessible, msg = check_repository_access("https://github.com/owner/repo")

        assert is_accessible is False
        assert "not installed" in msg or "not found" in msg


class TestDisplayEnvironmentValidation:
    """Tests for display_environment_validation()"""

    @patch('environment_validator.get_repository_info')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.print')
    def test_all_checks_pass(self, mock_print, mock_git_installed, mock_repo_info):
        """Test when all validation checks pass."""
        mock_git_installed.return_value = (True, "")
        mock_repo_info.return_value = {
            "current_dir": "/test/path",
            "is_git_repo": True,
            "has_remote": True,
            "remote_url": "https://github.com/owner/repo.git",
            "branch_name": "main"
        }

        result = display_environment_validation("/test/path")

        assert result is True
        # Verify it printed success messages
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "✓" in printed_text or "YES" in printed_text

    @patch('environment_validator.check_git_installed')
    @patch('builtins.print')
    def test_git_not_installed(self, mock_print, mock_git_installed):
        """Test when git is not installed."""
        mock_git_installed.return_value = (False, "Git not found")

        result = display_environment_validation("/test/path")

        assert result is False

    @patch('environment_validator.get_repository_info')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.print')
    def test_not_a_git_repo(self, mock_print, mock_git_installed, mock_repo_info):
        """Test when directory is not a git repository."""
        mock_git_installed.return_value = (True, "")
        mock_repo_info.return_value = {
            "current_dir": "/test/path",
            "is_git_repo": False,
            "has_remote": False,
            "remote_url": "",
            "branch_name": ""
        }

        result = display_environment_validation("/test/path")

        assert result is False

    @patch('environment_validator.get_repository_info')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.print')
    def test_no_remote_configured(self, mock_print, mock_git_installed, mock_repo_info):
        """Test when git repo has no remote."""
        mock_git_installed.return_value = (True, "")
        mock_repo_info.return_value = {
            "current_dir": "/test/path",
            "is_git_repo": True,
            "has_remote": False,
            "remote_url": "",
            "branch_name": "main"
        }

        result = display_environment_validation("/test/path")

        assert result is False


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @patch('environment_validator.subprocess.run')
    def test_empty_git_output(self, mock_run):
        """Test handling of empty git command output."""
        mock_run.return_value = Mock(stdout="", returncode=0)

        # Should still succeed but with empty values
        installed, msg = check_git_installed()
        assert installed is True

    @patch('environment_validator.subprocess.run')
    def test_stderr_without_error_attribute(self, mock_run):
        """Test CalledProcessError without stderr attribute."""
        error = subprocess.CalledProcessError(1, "git")
        # Explicitly don't set stderr attribute
        mock_run.side_effect = error

        is_accessible, msg = check_repository_access("https://github.com/owner/repo")

        assert is_accessible is False
        # Should handle gracefully even without stderr

    def test_validate_url_with_special_characters(self):
        """Test URLs with special characters."""
        urls = [
            "https://github.com/owner/repo-with-dashes",
            "https://github.com/owner/repo_with_underscores",
            "https://github.com/owner/repo.with.dots",
        ]

        for url in urls:
            is_valid, msg = validate_git_url(url)
            assert is_valid is True, f"Should accept {url}"


# Integration-style tests (can be skipped in CI without git)
class TestIntegrationWithRealGit:
    """
    Integration tests that use real git commands.
    These can be skipped if git is not available.
    """

    @pytest.mark.skipif(not Path(".git").exists(), reason="Not in a git repository")
    def test_real_git_check(self):
        """Test with actual git installation."""
        installed, msg = check_git_installed()
        assert installed is True

    @pytest.mark.skipif(not Path(".git").exists(), reason="Not in a git repository")
    def test_real_repo_validation(self):
        """Test validation of actual repository."""
        is_valid, msg = validate_git_repository(".")
        assert is_valid is True

    @pytest.mark.skipif(not Path(".git").exists(), reason="Not in a git repository")
    def test_real_repo_info(self):
        """Test getting info from actual repository."""
        info = get_repository_info(".")
        assert info["is_git_repo"] is True
        assert isinstance(info["current_dir"], str)


if __name__ == "__main__":
    # Allow running tests directly with: python test_environment_validator.py
    pytest.main([__file__, "-v"])
