import os, sys, re
import subprocess
from pathlib import Path
from argparse import Namespace
import pandas as pd

from git_audit import audit_repository


def execute():
    
    options = {
        "1": (f"Run in current working directory: {Path.cwd()}", run_current_directory),
        "2": ("Enter full directory path", run_from_directory),
        "3": ("Enter repository URL", run_from_url),
        "4": ("Enter CSV file path (URLs)", run_from_csv),
        "5": ("Exit", sys.exit)
    }

    while True:
        print("\nChoose an option:")
        for key, (desc, _) in options.items():
            print(f"{key}. {desc}")

        choice = input("Enter your choice: ").strip()

        if choice in options:
            _, action = options[choice]
            action()
            
        else:
            print("Invalid choice. Please try again.")


def get_url_from_dir(directory: str):
    """
    Gets the remote URL from a git directory.

    Args:
        directory: Path to git repository

    Returns:
        str or None: Remote URL if found, None otherwise
    """
    try:
        result = subprocess.run(
            ["git", "-C", directory, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        return url if url else None
    except FileNotFoundError:
        # Git is not installed
        return None
    except subprocess.CalledProcessError:
        # Not a git repo or no remote configured
        return None


def run_current_directory():
    from environment_validator import (
        check_git_installed,
        display_environment_validation
    )

    # Step 1: Check git is installed
    git_installed, error_msg = check_git_installed()
    if not git_installed:
        print(f"\n[ERROR] {error_msg}")
        print("Please install Git and try again.")
        print("Download from: https://git-scm.com/downloads")
        return

    # Step 2: Display environment validation
    print("\n" + "="*60)
    if not display_environment_validation(str(Path.cwd())):
        print("\n[ERROR] Environment validation failed.")
        print("Please fix the issues above and try again.")
        return

    # Step 3: Get git URL
    git_url = get_url_from_dir(str(Path.cwd()))
    if git_url is None:
        print("\n[ERROR] Could not retrieve Git remote URL.")
        print("This directory may not be a Git repository or doesn't have a remote configured.")
        print("\nPossible solutions:")
        print("  1. Make sure you're in a Git repository directory")
        print("  2. Check that a remote is configured: git remote -v")
        print("  3. Add a remote: git remote add origin <url>")
        return

    print(f"\n[OK] Remote URL found: {git_url}")
    print("\n" + "="*60)
    print("STARTING AUDIT")
    print("="*60 + "\n")

    args = Namespace(git_url=git_url, output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
    # Pass current directory to avoid re-cloning (we're already in the repo)
    audit_repository(args, working_directory=str(Path.cwd()))


def run_from_directory():
    from environment_validator import (
        check_git_installed,
        display_environment_validation
    )

    path = input("Enter full directory path: ").strip()

    # Step 1: Validate path exists
    if not Path(path).exists():
        print(f"\n[ERROR] Directory does not exist: {path}")
        return

    if not Path(path).is_dir():
        print(f"\n[ERROR] Path is not a directory: {path}")
        return

    # Step 2: Check git is installed
    git_installed, error_msg = check_git_installed()
    if not git_installed:
        print(f"\n[ERROR] {error_msg}")
        print("Please install Git and try again.")
        print("Download from: https://git-scm.com/downloads")
        return

    # Step 3: Display environment validation
    print("\n" + "="*60)
    if not display_environment_validation(path):
        print("\n[ERROR] Environment validation failed.")
        print("Please fix the issues above and try again.")
        return

    # Step 4: Get git URL
    git_url = get_url_from_dir(path)
    if git_url is None:
        print("\n[ERROR] Could not retrieve Git remote URL.")
        print("The specified directory may not be a Git repository or doesn't have a remote configured.")
        print("\nPossible solutions:")
        print("  1. Make sure the directory is a Git repository")
        print("  2. Check that a remote is configured: git remote -v")
        print("  3. Add a remote: git remote add origin <url>")
        return

    print(f"\n[OK] Remote URL found: {git_url}")
    print("\n" + "="*60)
    print("STARTING AUDIT")
    print("="*60 + "\n")

    # Save current working directory
    original_cwd = os.getcwd()

    try:
        # Change to the target directory for the audit
        os.chdir(path)
        args = Namespace(git_url=git_url, output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
        # Pass the directory to avoid re-cloning (we're already in the repo)
        audit_repository(args, working_directory=path)
    finally:
        # Always restore original working directory
        os.chdir(original_cwd)
        print(f"\nReturned to original directory: {original_cwd}")


def run_from_url():
    from environment_validator import (
        check_git_installed,
        validate_git_url,
        check_repository_access
    )

    url = input("Enter repository URL: ").strip()

    # Step 1: Check git is installed
    git_installed, error_msg = check_git_installed()
    if not git_installed:
        print(f"\n[ERROR] {error_msg}")
        print("Please install Git and try again.")
        print("Download from: https://git-scm.com/downloads")
        return

    # Step 2: Validate URL format
    is_valid, error_msg = validate_git_url(url)
    if not is_valid:
        print(f"\n[ERROR] {error_msg}")
        return

    # Step 3: Test repository access
    print("\nTesting repository access...")
    is_accessible, error_msg = check_repository_access(url)
    if not is_accessible:
        print(f"\n[ERROR] {error_msg}")
        print("\n[NOTE] For private repositories, use Option 1 (current directory)")
        print("         after cloning the repository locally with your credentials.")
        return

    print("[OK] Repository is accessible")
    print("\n" + "="*60)
    print("STARTING AUDIT")
    print("="*60 + "\n")

    args = Namespace(git_url=url, output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
    audit_repository(args)


def run_from_csv():
    from environment_validator import (
        check_git_installed,
        validate_git_url,
        check_repository_access
    )

    csv_path = input("Enter CSV file path: ").strip()

    # Step 1: Check git is installed
    git_installed, error_msg = check_git_installed()
    if not git_installed:
        print(f"\n[ERROR] {error_msg}")
        print("Please install Git and try again.")
        print("Download from: https://git-scm.com/downloads")
        return

    # Step 2: Read CSV
    try:
        df = pd.read_csv(csv_path, header=None)
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        return

    if df.empty or df.shape[1] < 1:
        print("[ERROR] CSV is empty or doesn't contain any columns.")
        return

    source_dir = Path.cwd()
    urls = df.iloc[:, 0].dropna()

    print(f"\nFound {len(urls)} URLs to process")
    successful = 0
    failed = 0

    for idx, url in enumerate(urls, 1):
        url = str(url).strip()
        if not url:
            continue

        print(f"\n{'='*60}")
        print(f"Processing {idx}/{len(urls)}: {url}")
        print('='*60)

        # Validate URL
        is_valid, error_msg = validate_git_url(url)
        if not is_valid:
            print(f"[SKIP] Invalid URL: {error_msg}")
            failed += 1
            continue

        # Test access
        print("Testing repository access...")
        is_accessible, error_msg = check_repository_access(url)
        if not is_accessible:
            print(f"[SKIP] Inaccessible repository: {error_msg}")
            failed += 1
            continue

        print("[OK] Repository is accessible")

        # Extract owner/repo
        owner, repo = extract_owner_repo(url)
        if not owner or not repo:
            print(f"[SKIP] Could not parse owner/repo from URL: {url}")
            failed += 1
            continue

        target_dir = source_dir / owner
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"Switching to directory: {target_dir}")
        os.chdir(target_dir)

        try:
            args = Namespace(git_url=url, output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
            audit_repository(args)
            successful += 1
        except Exception as e:
            print(f"[ERROR] Audit failed: {e}")
            failed += 1
        finally:
            os.chdir(source_dir)

    print(f"\n{'='*60}")
    print(f"Batch processing complete: {successful} successful, {failed} failed")
    print('='*60)


def extract_owner_repo(url):
    """Extract owner and repo name from GitHub URL."""
    try:
        return url.split('/')[-2], url.split('/')[-1]
    except IndexError as e:
        print(f"Failed to extract owner/repo from URL: {url}")
        return None, None


if __name__ == '__main__':
    execute()