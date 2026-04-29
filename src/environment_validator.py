"""
Environment validation module for Git Audit Tool.

This module provides validation functions to check:
- Git installation
- Git repository status
- Repository access and credentials
- URL format validation
"""

import os
import subprocess
from pathlib import Path


def check_git_installed() -> tuple[bool, str]:
    """
    Checks if git is installed and accessible.

    Returns:
        tuple[bool, str]: (is_installed, error_message)
            - is_installed: True if git is available, False otherwise
            - error_message: Empty string if successful, error description if not
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        return True, ""
    except FileNotFoundError:
        return False, "Git is not installed or not found in PATH"
    except subprocess.CalledProcessError:
        return False, "Git command failed to execute"


def validate_git_repository(directory: str) -> tuple[bool, str]:
    """
    Validates that the directory is a git repository.

    Args:
        directory: Path to directory to check

    Returns:
        tuple[bool, str]: (is_valid, error_message)
            - is_valid: True if directory is a git repo, False otherwise
            - error_message: Empty string if successful, error description if not
    """
    # Check if .git directory exists
    git_dir = Path(directory) / ".git"
    if not git_dir.exists():
        return False, f"Directory is not a Git repository (no .git folder found)"

    # Verify with git command
    try:
        result = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip().lower() == "true":
            return True, ""
        else:
            return False, "Directory is not inside a Git working tree"
    except subprocess.CalledProcessError:
        return False, "Git repository validation failed"


def get_repository_info(directory: str) -> dict:
    """
    Gets information about the git repository for validation display.

    Args:
        directory: Path to repository directory

    Returns:
        dict: Repository information with keys:
            - current_dir: Absolute path to directory
            - is_git_repo: True/False
            - has_remote: True/False
            - remote_url: URL of origin remote or empty string
            - branch_name: Current branch name or empty string
    """
    info = {
        "current_dir": str(Path(directory).resolve()),
        "is_git_repo": False,
        "has_remote": False,
        "remote_url": "",
        "branch_name": ""
    }

    # Check if git repository
    is_repo, _ = validate_git_repository(directory)
    info["is_git_repo"] = is_repo

    if not is_repo:
        return info

    # Get branch name
    try:
        result = subprocess.run(
            ["git", "-C", directory, "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True
        )
        info["branch_name"] = result.stdout.strip()
    except subprocess.CalledProcessError:
        info["branch_name"] = ""

    # Get remote URL
    try:
        result = subprocess.run(
            ["git", "-C", directory, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        if remote_url:
            info["has_remote"] = True
            info["remote_url"] = remote_url
    except subprocess.CalledProcessError:
        info["has_remote"] = False
        info["remote_url"] = ""

    return info


def validate_git_url(git_url: str | None) -> tuple[bool, str]:
    """
    Validates that git_url is not None and has proper format.

    Args:
        git_url: Git repository URL to validate

    Returns:
        tuple[bool, str]: (is_valid, error_message)
            - is_valid: True if URL is valid, False otherwise
            - error_message: Empty string if successful, error description if not
    """
    if git_url is None:
        return False, "No git URL provided (URL is None)"

    if not isinstance(git_url, str):
        return False, f"Git URL must be a string, got {type(git_url).__name__}"

    if not git_url.strip():
        return False, "Empty git URL provided"

    # Check if URL has proper format (contains '/' for splitting owner/repo)
    if '/' not in git_url:
        return False, f"Invalid URL format: {git_url}\nExpected format: https://github.com/owner/repository"

    return True, ""


def check_repository_access(git_url: str) -> tuple[bool, str]:
    """
    Tests if repository is accessible (not private/credential issue).

    Args:
        git_url: Git repository URL to test

    Returns:
        tuple[bool, str]: (is_accessible, error_message)
            - is_accessible: True if repo is accessible, False otherwise
            - error_message: Empty string if successful, detailed error with guidance if not
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", git_url],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        return True, ""
    except subprocess.TimeoutExpired:
        return False, (
            "Connection timeout while accessing repository.\n"
            "Please check your network connection."
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.lower() if e.stderr else ""

        # Detect authentication/private repository issues
        if "authentication failed" in stderr or "could not read" in stderr:
            return False, (
                "Authentication failed. This is likely a private repository.\n"
                "For private repositories:\n"
                "  1. Clone the repository manually with your credentials\n"
                "  2. Use Option 1 (Run in current directory) from within the cloned repo"
            )
        elif "repository not found" in stderr or "404" in stderr:
            return False, (
                "Repository not found.\n"
                "Please verify:\n"
                "  - The URL is correct\n"
                "  - The repository exists\n"
                "  - You have access to the repository"
            )
        elif "permission denied" in stderr or "403" in stderr:
            return False, (
                "Permission denied. This repository may be private or you lack access.\n"
                "For private repositories:\n"
                "  1. Clone the repository manually with your credentials\n"
                "  2. Use Option 1 (Run in current directory) from within the cloned repo"
            )
        else:
            return False, (
                f"Failed to access repository.\n"
                f"Error: {e.stderr if e.stderr else 'Unknown error'}\n"
                "Please check the URL and your network connection."
            )
    except FileNotFoundError:
        return False, "Git is not installed or not found in PATH"


def display_environment_validation(directory: str = ".") -> bool:
    """
    Displays environment validation results to user before audit.

    Args:
        directory: Path to directory to validate (default: current directory)

    Returns:
        bool: True if all checks pass, False otherwise
    """
    print("\nENVIRONMENT VALIDATION")
    print("=" * 60)

    all_checks_passed = True

    # Check 1: Git installed
    git_installed, error_msg = check_git_installed()
    if git_installed:
        print("[OK] Git installed: YES")
    else:
        print(f"[ERROR] Git installed: NO - {error_msg}")
        all_checks_passed = False

    # If git not installed, can't do other checks
    if not git_installed:
        print("=" * 60)
        return False

    # Get repository info
    info = get_repository_info(directory)

    # Check 2: Current directory
    print(f"  Current directory: {info['current_dir']}")

    # Check 3: Is git repository
    if info['is_git_repo']:
        print("[OK] Is git repository: YES")
    else:
        print("[ERROR] Is git repository: NO")
        all_checks_passed = False

    # Check 4: Remote URL
    if info['has_remote']:
        print(f"[OK] Remote URL: {info['remote_url']}")
    else:
        print("[ERROR] Remote URL: Not configured")
        if info['is_git_repo']:
            all_checks_passed = False

    # Check 5: Current branch
    if info['branch_name']:
        print(f"  Current branch: {info['branch_name']}")
    else:
        if info['is_git_repo']:
            print("  Current branch: Unable to determine")

    print("=" * 60)

    return all_checks_passed
