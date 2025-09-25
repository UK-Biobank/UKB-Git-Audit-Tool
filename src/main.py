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
    try:
        result = subprocess.run(
            ["git", "-C", directory, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def run_current_directory():
    args = Namespace(git_url=get_url_from_dir(str(Path.cwd())),
                        output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
    audit_repository(args)


def run_from_directory():
    path = input("Enter full directory path: ").strip()
    if Path(path).is_dir():
        args = Namespace(git_url=get_url_from_dir(path),
                            output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
        audit_repository(args)
    else:
        print("Invalid directory path.")


def run_from_url():
    url = input("Enter repository URL: ").strip()
    args = Namespace(git_url=url,
                        output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
    audit_repository(args)


def run_from_csv():
    csv_path = input("Enter CSV file path: ").strip()
    try:
        df = pd.read_csv(csv_path, header=None)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    if df.empty or df.shape[1] < 1:
        print("CSV is empty or doesn't contain any columns.")
        return
    
    source_dir = Path.cwd()


    for url in df.iloc[:, 0].dropna():
        url = str(url).strip()
        if not url:
            continue

        owner, repo = extract_owner_repo(url)
        if not owner or not repo:
            print(f"Could not parse owner/repo from URL: {url}")
            continue
        target_dir = source_dir / owner
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nRunning audit for: {url}")
        print(f"Switching to directory: {target_dir}")

        os.chdir(target_dir)

        args = Namespace(git_url=url,
                        output_fpath='./REPOSITORY_AUDIT_REPORT.csv')
        audit_repository(args)


def extract_owner_repo(url):
    """Extract owner and repo name from GitHub URL."""
    try:
        return url.split('/')[-2], url.split('/')[-1]
    except IndexError as e:
        print(f"Failed to extract owner/repo from URL: {url}")
        return None, None


if __name__ == '__main__':
    execute()