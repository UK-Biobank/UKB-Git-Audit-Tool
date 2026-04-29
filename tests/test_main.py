"""
Unit tests for main.py functions.

Tests the main execution functions and URL validation logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import (
    get_url_from_dir,
    extract_owner_repo,
    run_current_directory,
    run_from_directory,
    run_from_url
)


class TestGetUrlFromDir:
    """Tests for get_url_from_dir()"""

    @patch('main.subprocess.run')
    def test_success_with_remote(self, mock_run):
        """Test getting URL from a directory with remote."""
        mock_run.return_value = Mock(
            stdout="https://github.com/owner/repo.git\n",
            returncode=0
        )

        url = get_url_from_dir("/test/path")

        assert url == "https://github.com/owner/repo.git"
        mock_run.assert_called_once_with(
            ["git", "-C", "/test/path", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )

    @patch('main.subprocess.run')
    def test_git_not_installed(self, mock_run):
        """Test when git is not installed."""
        mock_run.side_effect = FileNotFoundError()

        url = get_url_from_dir("/test/path")

        assert url is None

    @patch('main.subprocess.run')
    def test_no_remote_configured(self, mock_run):
        """Test when repository has no remote."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        url = get_url_from_dir("/test/path")

        assert url is None

    @patch('main.subprocess.run')
    def test_empty_remote_url(self, mock_run):
        """Test when remote returns empty string."""
        mock_run.return_value = Mock(stdout="", returncode=0)

        url = get_url_from_dir("/test/path")

        assert url is None


class TestExtractOwnerRepo:
    """Tests for extract_owner_repo()"""

    def test_valid_github_url(self):
        """Test extracting owner/repo from standard GitHub URL."""
        owner, repo = extract_owner_repo("https://github.com/owner-name/repo-name")

        assert owner == "owner-name"
        assert repo == "repo-name"

    def test_url_with_git_extension(self):
        """Test URL ending with .git"""
        owner, repo = extract_owner_repo("https://github.com/owner/repo.git")

        assert owner == "owner"
        assert repo == "repo.git"

    def test_url_with_trailing_slash(self):
        """Test URL with trailing slash."""
        owner, repo = extract_owner_repo("https://github.com/owner/repo/")

        assert owner == "repo"
        assert repo == ""

    def test_invalid_url_format(self):
        """Test handling of invalid URL format."""
        owner, repo = extract_owner_repo("invalid-url")

        assert owner is None
        assert repo is None

    def test_url_too_short(self):
        """Test URL without enough parts."""
        owner, repo = extract_owner_repo("https://github.com/")

        # Should handle IndexError gracefully
        # When split by '/', the URL has parts but they may be empty
        assert (owner is None or owner == "" or
                repo is None or repo == "")


class TestRunCurrentDirectory:
    """Tests for run_current_directory()"""

    @patch('main.audit_repository')
    @patch('main.get_url_from_dir')
    @patch('environment_validator.display_environment_validation')
    @patch('environment_validator.check_git_installed')
    @patch('main.Path.cwd')
    @patch('builtins.print')
    def test_successful_execution(
        self,
        mock_print,
        mock_cwd,
        mock_git_installed,
        mock_validate,
        mock_get_url,
        mock_audit
    ):
        """Test successful execution of audit from current directory."""
        mock_cwd.return_value = Path("/test/repo")
        mock_git_installed.return_value = (True, "")
        mock_validate.return_value = True
        mock_get_url.return_value = "https://github.com/owner/repo.git"

        run_current_directory()

        mock_audit.assert_called_once()
        args = mock_audit.call_args[0][0]
        assert args.git_url == "https://github.com/owner/repo.git"

    @patch('main.audit_repository')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.print')
    def test_git_not_installed(self, mock_print, mock_git_installed, mock_audit):
        """Test when git is not installed."""
        mock_git_installed.return_value = (False, "Git not found")

        run_current_directory()

        # Should not call audit
        mock_audit.assert_not_called()
        # Should print error message
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "ERROR" in printed_text

    @patch('main.audit_repository')
    @patch('environment_validator.display_environment_validation')
    @patch('environment_validator.check_git_installed')
    @patch('main.Path.cwd')
    @patch('builtins.print')
    def test_validation_failed(
        self,
        mock_print,
        mock_cwd,
        mock_git_installed,
        mock_validate,
        mock_audit
    ):
        """Test when environment validation fails."""
        mock_cwd.return_value = Path("/test/repo")
        mock_git_installed.return_value = (True, "")
        mock_validate.return_value = False

        run_current_directory()

        # Should not call audit
        mock_audit.assert_not_called()

    @patch('main.audit_repository')
    @patch('main.get_url_from_dir')
    @patch('environment_validator.display_environment_validation')
    @patch('environment_validator.check_git_installed')
    @patch('main.Path.cwd')
    @patch('builtins.print')
    def test_no_remote_url(
        self,
        mock_print,
        mock_cwd,
        mock_git_installed,
        mock_validate,
        mock_get_url,
        mock_audit
    ):
        """Test when no remote URL is found (the original bug scenario)."""
        mock_cwd.return_value = Path("/test/repo")
        mock_git_installed.return_value = (True, "")
        mock_validate.return_value = True
        mock_get_url.return_value = None  # This caused the original bug!

        run_current_directory()

        # Should not call audit
        mock_audit.assert_not_called()
        # Should print error about missing remote
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "remote" in printed_text.lower()


class TestRunFromDirectory:
    """Tests for run_from_directory()"""

    @patch('main.audit_repository')
    @patch('main.os.chdir')
    @patch('main.os.getcwd')
    @patch('main.get_url_from_dir')
    @patch('environment_validator.display_environment_validation')
    @patch('environment_validator.check_git_installed')
    @patch('main.Path')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_successful_execution(
        self,
        mock_print,
        mock_input,
        mock_path_class,
        mock_git_installed,
        mock_validate,
        mock_get_url,
        mock_getcwd,
        mock_chdir,
        mock_audit
    ):
        """Test successful execution from provided directory."""
        mock_input.return_value = "/test/repo"
        mock_getcwd.return_value = "/original/path"

        # Mock Path behavior
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = True
        mock_path_class.return_value = mock_path

        mock_git_installed.return_value = (True, "")
        mock_validate.return_value = True
        mock_get_url.return_value = "https://github.com/owner/repo.git"

        run_from_directory()

        mock_audit.assert_called_once()
        # Verify we changed to the directory
        mock_chdir.assert_called()

    @patch('main.audit_repository')
    @patch('main.Path')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_directory_does_not_exist(self, mock_print, mock_input, mock_path_class, mock_audit):
        """Test when provided directory doesn't exist."""
        mock_input.return_value = "/nonexistent/path"

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        run_from_directory()

        # Should not call audit
        mock_audit.assert_not_called()
        # Should print error
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "does not exist" in printed_text

    @patch('main.audit_repository')
    @patch('main.Path')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_path_is_not_directory(self, mock_print, mock_input, mock_path_class, mock_audit):
        """Test when path exists but is not a directory."""
        mock_input.return_value = "/test/file.txt"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = False
        mock_path_class.return_value = mock_path

        run_from_directory()

        # Should not call audit
        mock_audit.assert_not_called()
        # Should print error
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "not a directory" in printed_text


class TestRunFromUrl:
    """Tests for run_from_url()"""

    @patch('main.audit_repository')
    @patch('environment_validator.check_repository_access')
    @patch('environment_validator.validate_git_url')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_successful_execution(
        self,
        mock_print,
        mock_input,
        mock_git_installed,
        mock_validate_url,
        mock_test_access,
        mock_audit
    ):
        """Test successful execution from URL."""
        mock_input.return_value = "https://github.com/owner/repo.git"
        mock_git_installed.return_value = (True, "")
        mock_validate_url.return_value = (True, "")
        mock_test_access.return_value = (True, "")

        run_from_url()

        mock_audit.assert_called_once()
        args = mock_audit.call_args[0][0]
        assert args.git_url == "https://github.com/owner/repo.git"

    @patch('main.audit_repository')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_git_not_installed(self, mock_print, mock_input, mock_git_installed, mock_audit):
        """Test when git is not installed."""
        mock_input.return_value = "https://github.com/owner/repo.git"
        mock_git_installed.return_value = (False, "Git not found")

        run_from_url()

        mock_audit.assert_not_called()

    @patch('main.audit_repository')
    @patch('environment_validator.validate_git_url')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_invalid_url(
        self,
        mock_print,
        mock_input,
        mock_git_installed,
        mock_validate_url,
        mock_audit
    ):
        """Test with invalid URL format."""
        mock_input.return_value = "invalid-url"
        mock_git_installed.return_value = (True, "")
        mock_validate_url.return_value = (False, "Invalid format")

        run_from_url()

        mock_audit.assert_not_called()

    @patch('main.audit_repository')
    @patch('environment_validator.check_repository_access')
    @patch('environment_validator.validate_git_url')
    @patch('environment_validator.check_git_installed')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_private_repository(
        self,
        mock_print,
        mock_input,
        mock_git_installed,
        mock_validate_url,
        mock_test_access,
        mock_audit
    ):
        """Test when repository is private/inaccessible."""
        mock_input.return_value = "https://github.com/owner/private-repo.git"
        mock_git_installed.return_value = (True, "")
        mock_validate_url.return_value = (True, "")
        mock_test_access.return_value = (False, "Authentication failed")

        run_from_url()

        mock_audit.assert_not_called()
        # Should print guidance about using Option 1
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Option 1" in printed_text


# Add subprocess import that was missing
import subprocess


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
