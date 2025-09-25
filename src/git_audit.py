import os
import subprocess
import argparse
import mimetypes
import numpy as np
import pandas as pd
import regex as re
import json
from tqdm import tqdm
from collections import Counter
from pathlib import Path
import shutil
from datetime import datetime, timezone


from utilities import (regex_pattern, register_common_ukb_filetypes, 
                      contextualise_git_status, update_dictionary,
                      build_collaborator_table, fetch_forked_repos)
from access_management import get_github_token

register_common_ukb_filetypes()
gh_token = get_github_token()


# --- Core Data Collection and Parsing Functions ---
def capture_git_files() -> str:
    """
    Runs git commands to get a list of all objects (files) and their sizes
    from the entire repository history.
    """
    all_ref_files = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        stdout=subprocess.PIPE,
        text=True,
    )
    
    big_file_dig = subprocess.run(
        ["git", "cat-file", "--batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)'"],
        input=all_ref_files.stdout,
        capture_output=True,
        text=True,
    )
    return big_file_dig


def git_to_pandas(git_stdout, columns) -> pd.DataFrame:
    """
    Parses the output of capture_git_files() into a pandas DataFrame.
    """
    blob_lines = git_stdout.splitlines()
    branch_data = []

    for line in blob_lines:
        if line.startswith("'blob"):
            branch_data.append(line.replace("'", "").split(maxsplit=3))

    df = pd.DataFrame(branch_data, columns=columns)
    df['objectsize'] = pd.to_numeric(df['objectsize'])

    return df


def get_full_log() -> str:
    """
    Runs git log with a custom format to get a complete history of all file changes.
    """
    log_cmd = subprocess.run(
    ["git", "log", "--all", "--name-status",
     "--date=iso-strict",
     "--pretty=format:COMMIT_START|%H|%ad|%d"],
    capture_output=True, text=True, check=True
    )
    return log_cmd.stdout


def parse_full_log_to_dataframe(raw_log_output) -> pd.DataFrame:
    """
    Parses the raw git log output into a structured pandas DataFrame.
    """
    log_data = []
    current_commit = None
    current_date = None
    current_refs = None
    
    lines = raw_log_output.strip().split('\n')
    
    for line in lines:
        if line.startswith('COMMIT_START'):
            parts = line.split('|')
            current_commit = parts[1]
            current_date = parts[2]
            current_refs = parts[3]
            continue
            
        if not re.match(r'^[A-Z]', line):
            continue
            
        parts = line.split('\t')
        status = parts[0]
        
        if status.startswith('R'):
            old_filename = parts[1]
            new_filename = parts[2]
            log_data.append({
                'commit': current_commit,
                'status': status,
                'filename': new_filename,
                'date': current_date,
                'refs': current_refs,
                'old_filename': old_filename
            })
        else:
            filename = parts[1]
            log_data.append({
                'commit': current_commit,
                'status': status,
                'filename': filename,
                'date': current_date,
                'refs': current_refs,
                'old_filename': ''
            })
            
    return pd.DataFrame(log_data)

def get_blob_hashes_for_commits(commits) -> pd.DataFrame:
    """
    For a list of commit hashes, get a DataFrame of all files, their blob hashes,
    and their file paths using 'git ls-tree'.
    """

    all_blob_data = []
    
    for commit in commits.unique():
        try:
            ls_tree_cmd = subprocess.run(
                ['git', 'ls-tree', '-r', '-z', f'{commit}'],
                capture_output=True, text=True, check=True
            )
            
            parts = ls_tree_cmd.stdout.split('\0')
            
            for part in parts[:-1]:
                header, filename = part.split('\t', 1)
                header_parts = header.split()
                
                if len(header_parts) == 3 and header_parts[1] == 'blob':
                    blob_hash = header_parts[2]
                    all_blob_data.append({
                        'commit': commit,
                        'blob_hash': blob_hash,
                        'filename': filename
                    })
        except subprocess.CalledProcessError:
            print(ls_tree_cmd.stderr)
            continue
            
    return pd.DataFrame(all_blob_data)


# --- Analysis of files ---    
def analyze_glob_hashes_for_pattern(df: pd.DataFrame, pattern) -> pd.DataFrame:
    """
    For each unique blob_hash in df, count:
      - eid_occ: total matches of the 7-digit ID pattern in content
      - unique_occ: number of distinct IDs in that blob
      - found_ids: JSON of top IDs with counts (most_common up to 5)
    Returns (tuple) of two dataframes
        blob_hash, eid_occ, unique_occ, found_ids
        eid, count
    """
    rows = []
    unique_blobs = df["blob_hash"].dropna().unique()
    eid_dict = {}

    for blob_hash in tqdm(unique_blobs, desc="Scanning blobs"):
        eid_occ = np.nan          # unreadable/unknown until decode succeeds
        unique_count = 0          # neutral default
        top_ids = ""

        try:
            out = subprocess.run(
                ["git", "show", str(blob_hash)],
                capture_output=True,
                check=True,
            )
            text = out.stdout.decode("utf-8")   # let UnicodeDecodeError be raised
            ids = re.findall(pattern, text)
            eid_occ = len(ids)
            unique_count = len(set(ids))
            if eid_occ:
                c = Counter(ids)
                top_ids = json.dumps(dict(c.most_common(5)))
                eid_dict = update_dictionary(eid_dict, c)           # update dictionary of all found IDs

        except (subprocess.CalledProcessError,UnicodeDecodeError):
            # leave defaults (eid_occ=0, unique_count=0, top_ids="")
            # non-UTF8 / binary content or git show error — keep defaults
            pass

        rows.append(
            {
                "blob_hash": blob_hash,
                "eid_occ": eid_occ,  # 0 => read OK/no IDs; NaN => unreadable/failed decode/deleted
                "unique_occ": unique_count,
                "found_ids": top_ids,
            }
        )

    return pd.DataFrame(rows), pd.DataFrame(eid_dict.items(), columns=["eid", "count"])

def analyse_file_names(df, pattern) -> pd.DataFrame:
    """
    Iterate through all filenames, searching for eids within the filename
    Adds a file_ext column using mimetypes.guess_type
    Add size_MB rounded to 3 decimal places
    """
    df['filename_occ'] = df['filename'].apply(lambda filename: 1 if bool(re.search(pattern, filename)) else 0)
    df['file_ext'] = df['filename'].apply(lambda filename: mimetypes.guess_type(filename)[0] or 'unknown')

    df['size_bytes'] = pd.to_numeric(df['size_bytes'], errors='coerce')
    df['size_MB'] = df['size_bytes'] / 1024**2 * 1000 // 1 / 1000

    return df


# --- Update Repo ---
def clone_or_update_repo(git_url, local_path):
    if os.path.isdir(os.path.join(local_path, ".git")):
        print(f"Repository already exists. Updating {local_path}...")
        subprocess.run(["git", "fetch", "--all", "--prune"], cwd=local_path, check=True)
        subprocess.run(["git", "pull"], cwd=local_path, check=True)
    else:
        if os.path.exists(local_path):
            shutil.rmtree(local_path, ignore_errors=True)
        print(f"Cloning {git_url} to {local_path}...")
        subprocess.run(["git", "clone", git_url, local_path], check=True)


# --- Main Audit Function ---
def audit_repository(args):
    """
    Main executable function for the repository audit.
    Produces a single dataframe of all files, current & historical
        with file sizes and number of potential ID occurences in the file contents and file name
    """
    original_path = os.getcwd()
    
    repo_name = args.git_url.split('/')[-1].replace('.git', '')
    repo_path = os.path.join(original_path, repo_name)

    
    try:
        clone_or_update_repo(args.git_url, repo_path)
        os.chdir(repo_path)
        print(f"Auditing repository at {repo_path}...")
        
        # Step 1: collect git history and size
        print("Fetching commit history...")
        full_log_output = get_full_log()
        full_log_df = parse_full_log_to_dataframe(full_log_output)
        
        print("Fetching file sizes...")
        blob_dig = capture_git_files()
        blob_pd = git_to_pandas(blob_dig.stdout, ["objecttype", "objectname", "objectsize", "filename"])
        blob_sizes_df = blob_pd.rename(columns={'objectname': 'blob_hash', 'objectsize': 'size_bytes'})

        # after building full_log_df
        if not isinstance(full_log_df, pd.DataFrame) or 'commit' not in full_log_df.columns or full_log_df.empty:
            # Emit placeholder CSV when repo has no commits
            #out = Path("/app") / f"REPOSITORY_AUDIT_REPORT_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
            out = Path("/app") / f"REPOSITORY_AUDIT_REPORT_{repo_name}.csv"
            pd.DataFrame([{"note": "No commits or data to audit"}]).to_csv(out, index=False)
            print("No commits found; wrote placeholder CSV.")
            return

        
        print("Fetching file blob hashes...")
        blob_hashes_df = get_blob_hashes_for_commits(full_log_df['commit'])
        
        # Step 2 - merge
        print("Merging data into master DataFrame...")
        merged_df = pd.merge(full_log_df, blob_hashes_df, on=['commit', 'filename'], how='left')
        final_df = pd.merge(merged_df, blob_sizes_df[['blob_hash', 'size_bytes']], on='blob_hash', how='left')
        
        # Step 3 - analyse
        print("Performing analysis...")

        id_pattern = regex_pattern()

        # 1. Check for IDs in file content across the entire history
        print("Inspecting blob hashes")
        glob_hash_hits, total_eids_df = analyze_glob_hashes_for_pattern(final_df, id_pattern)
        glob_hash_hits = glob_hash_hits.copy()

        final_df = pd.merge(
            final_df,
            glob_hash_hits,
            on='blob_hash',
            how='left'
        )

        # 2. Checks for IDs in the file names across the entire history, add file extensions
        final_df = analyse_file_names(final_df, id_pattern)
        # Format date to dd/mm/yyyy for spreadsheet-friendly sorting
        final_df["date"] = pd.to_datetime(final_df["date"], errors="coerce", utc=True).dt.tz_convert(None).dt.strftime("%d/%m/%Y")

        # 3. Format the dataframe for eases of analysis
        final_df['total_occ'] = final_df['eid_occ'] + final_df['filename_occ']                      # combine content occurrences with filename occurrences
        final_df['status'] = final_df['status'].apply(lambda s: contextualise_git_status(s))
        final_df['repo_name'] = repo_name
        #git_name = Path(rf"{args.git_url}").stem
        git_name = repo_name

        if not final_df.empty:
            # Robust total occurrences
            final_df['total_occ'] = (
                pd.to_numeric(final_df['eid_occ'], errors='coerce').fillna(0).astype(int)
                + pd.to_numeric(final_df['filename_occ'], errors='coerce').fillna(0).astype(int)
            )

            # Build links & owner fields FIRST
            owner = args.git_url.rstrip("/").split("/")[-2]
            repo  = repo_name

            final_df["repo_link"] = f"https://github.com/{owner}/{repo}"
            final_df["raw_link"]  = ("https://raw.githubusercontent.com/{}/{}/".format(owner, repo)
                                    + final_df["commit"].astype(str) + "/" + final_df["filename"].astype(str).str.lstrip("/"))
            final_df["file_link"] = ("https://github.com/{}/{}/blob/".format(owner, repo)
                                    + final_df["commit"].astype(str) + "/" + final_df["filename"].astype(str).str.lstrip("/"))
            final_df["repo_owner"]     = owner
            final_df["repo_full_name"] = owner + "/" + repo
            final_df["Decision"] = ""
            final_df["Justification"] = ""

            ordered_cols = [
                "repo_name", "repo_owner", "repo_full_name",
                "commit", "date", "status", "filename", "file_ext", "blob_hash",
                "size_bytes", "size_MB", "eid_occ", "filename_occ", "total_occ",
                "unique_occ", "found_ids", "repo_link", "raw_link", "file_link",
                "refs", "old_filename", "Decision", "Justification"
            ]

            final_df = final_df[ordered_cols]
            final_df.sort_values(by='total_occ', ascending=False, inplace=True)

            ## Build collaborator emails table
            build_collaborator_table(owner, repo_name,
                                     token=gh_token)

            ## Build json file of forked repos
            fetch_forked_repos(owner, repo_name,
                                     token=gh_token)

            # --- repo-level EID frequency table ---
            output_csv_path = args.output_fpath.replace('.csv', f'_{git_name}.csv')

            # Write the per-repo audit CSV last
            final_df.to_csv(output_csv_path, na_rep="nan", index=False)

            total_eids_df = total_eids_df.sort_values(by='count', ascending=False)
            total_eids_df.to_csv(f"eid_frequency_{repo_name}.csv", index=False)
            print(f"Written EID frequency report to eid_frequency_{repo_name}.csv")


        else:
            print("No findings to report.")
            pd.DataFrame([{"Message": "No findings to report."}]).to_csv(args.output_fpath.replace('.csv', f'_{git_name}.csv'), index=False)

    except subprocess.CalledProcessError as e:
        print(f"A Git command failed. Please check the repository URL and your Git installation. Error: {e}")
    finally:
        os.chdir(original_path)
        print("Audit complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A script to audit a public repository's full history for sensitive data and large files.")
    parser.add_argument("git_url", type=str, help="The URL of the Git repository to clone and audit.")
    parser.add_argument("--output_fpath", type=str, default="./REPOSITORY_AUDIT_REPORT.csv", help="The path and file name to save the output to.")

    args = parser.parse_args()
    audit_repository(args)
