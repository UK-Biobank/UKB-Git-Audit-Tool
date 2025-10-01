import os
import re
import json
import subprocess
import mimetypes
import requests
import pandas as pd


def regex_pattern():
    """
    regex pattern explained
      - any 7 digit number from 1000000-6500000
      - surrounded by anything other than other digits
        - except full stops (floats to 7 decimals)
        - rs/RS - SNP IDs
      - examples:
          - include: 1234567, patient5082392, 3081375_20215_0_0.zip, 3240971.tsv
          - exclude: 123456, 0123456, 01234567, 6500001, 91234567, 1234_567
    """
    return r'(?<!\d)(?<!\.)(?<!rs)(?<!RS)(?<!Rs)(?<!rS)(10[0-9]{5}|[1-5][0-9]{6}|6[0-4][0-9]{5}|6500000)(?!\d)'


def register_common_ukb_filetypes():
    """
    Temporarily add commonly used filetypes we can expect to search for
    """

    # common programming language files
    mimetypes.add_type('text/x-terraform', '.tf')
    mimetypes.add_type('application/x-terraform-lock', '.hcl')
    mimetypes.add_type('text/config-toml', '.toml')
    mimetypes.add_type('text/git', '.gitignore')
    mimetypes.add_type('application/R-data', '.rData')
    mimetypes.add_type('text/x-r-source', '.r')
    mimetypes.add_type('text/x-r-project', '.rproj')
    mimetypes.add_type('text/x-r-source', '.R')
    mimetypes.add_type('text/x-r-project', '.Rproj')
    mimetypes.add_type('application/x-ipynb+json', '.ipynb')

    # images and model data types
    mimetypes.add_type('text/config', '.cfg')
    mimetypes.add_type('appplication/index', '.index')
    mimetypes.add_type('appplication/metadata', '.meta')
    mimetypes.add_type('image/dicom', '.dcm')
    mimetypes.add_type('image/nifti', '.nii')
    mimetypes.add_type('application/visualisation-toolkit', '.vtk')


def update_dictionary(ref_dic, new_dic={}) -> dict:
    """
    Combines two dictionaries and if there are shared keys, combines the integer values
    """

    for key, value in new_dic.items():
        if key in ref_dic:
            ref_dic[key] += value
        else:
            ref_dic[key] = value
    
    return ref_dic


def contextualise_git_status(status: str):
    """
    Replacing the Git statuses (A, M, D, Rxxx, Cxxx) with short descriptions 
    """

    if not isinstance(status, str):
        return 'unknown'
    elif status == 'A':
        return 'added'
    elif status == 'D':
        return 'deleted'
    elif status == 'M':
        return 'modified'
    elif status == 'T':
        return 'type_change'
    elif status == 'U':
        return 'unmerged_conflict'
    elif status.startswith('R'):
        return f"renamed_similarity_{int(status[1:])}%"
    elif status.startswith('B'):
        return f"broken_pairing_similarity_{int(status[1:])}%"
    elif status.startswith('C'):
        return f"copied_similarity_{int(status[1:])}%"
    return 'unknown'


def _get_github_headers(token):
    """Returns the standard headers for GitHub API requests."""
    return {
        'Authorization': f'token {token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'Git-Audit-Tool',
        'Accept': 'application/vnd.github+json'
    }


def build_collaborator_table(owner, repo_name, token):
    """
    Build a table of collaborators and their email addresses.
    Run in conjunction with Git Audit
    Input:
        owner (str) - GitHub owner of repo
        repo_name (str) - Name of repository in GitHub
        token (str) - GitHub Personal Access Token (begins with 'github_pat_')
    Returns:
        None
    Outputs csv file with list of email addresses, user names, 
        frequency count of contributions made to the repo and the User Type
    """
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=format:'%an <%ae>'"],
            capture_output=True,
            check=True,
        )
        log_output = out.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error running git log: {e}")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    entries = [parse_entry(entry) for entry in log_output.split('\n') if entry.strip()]
    df = pd.DataFrame(entries, columns=["Name", "Email"])
    df = df.dropna(subset=["Email"])  # Remove rows with missing emails

    # Count contributions per email
    try:
        counts = df.Email.value_counts().rename('Count').reset_index().rename(columns={'index': 'Email'})
        df = pd.merge(
            df.drop_duplicates(subset=["Email"], keep="first"),
            counts,
            on="Email",
            how="left",
        )
    except Exception as e:
        print(f"Error merging counts: {e}")
        return

    # Get GitHub name and email for the owner
    try:
        owner_email_df = get_github_email(owner, token=token)
    except Exception as e:
        print(f"Error fetching GitHub email: {e}")
        owner_email_df = pd.DataFrame(columns=['Name', 'Email', 'UserType'])

    # Merge with GitHub owner info
    try:
        df = df.merge(owner_email_df, on='Email', how='outer', suffixes=('', '_copy'))
        df['Name'] = df['Name'].fillna(df.get('Name_copy'))
        if 'Name_copy' in df.columns:
            df = df.drop(columns=['Name_copy'])
        df['UserType'] = df['UserType'].fillna('Contributor')
    except Exception as e:
        print(f"Error merging GitHub owner info: {e}")

    # Output to CSV
    try:
        df.sort_values(
            by=['UserType', 'Count'],
            ascending=[False, False]
        ).to_csv(
            f'contributors_{owner}_{repo_name}.csv',
            index=False
        )
        print(f"Output saved to {f'contributors_{owner}_{repo_name}.csv'}")
    except Exception as e:
        print(f"Error writing CSV: {e}")

def parse_entry(entry):
    """
    Parse a single entry from the Git log output.
    """
    try:
        entry = entry.strip("'")
        entry = entry.replace("&amp;lt;", "<").replace("&amp;gt;", ">").strip("'")
        match = re.match(r"(.*)<(.*)>", entry)
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip().lower()
            return name, email
    except Exception as e:
        print(f"Error parsing entry: {e}")
    return None, None


def get_github_email(username, token=None):
    """
    Queries the GitHub API for the user's public profile and returns the email if available, else None.
    """
    url = f"https://api.github.com/users/{username}"
    headers = _get_github_headers(token)

    if not token:
        raise ValueError(
                "A GitHub Personal Access Token (PAT) is required to retrieve the user's email address. "
                "Without a PAT, the email field will not be available from the GitHub API."
            )

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame({
            'Name': [data.get('name')],
            'Email': [data.get('email')],
            'UserType': ['Owner']
        })
    except requests.RequestException as e:
        print(f"GitHub API request failed: {e}")
    except Exception as e:
        print(f"Error processing GitHub API response: {e}")
    return pd.DataFrame(columns=['Name', 'Email', 'UserType'])


def fetch_forked_repos(owner, repo, token=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/forks?per_page=100&sort=stargazers"

    headers = _get_github_headers(token)
    r = requests.get(url,
                     headers=headers,
                     timeout=20)

    try:
        data = r.json()
    except json.JSONDecodeError:
        print("Failed to decode JSON response")
        return

    forks = []
    try:
        for f in data:
            full = f.get("full_name", "")
            html = f.get("html_url", "")
            try:
                email = get_github_email(
                    full.split('/')[0],
                    token=token).iloc[0]['Email']
            except Exception:
                email = ''
            created = f.get("created_at", "")[:10]  # YYYY-MM-DD
            forks.append({
                "name": full,
                "user_email": email,
                "url": html,
                "date_forked": created,
                "changes_made": False
            })
    except Exception as e:
        print(f"Error processing forks data: {e}")

    body = {
        "main_repo": f"{owner}/{repo}",
        "main_repo_url": f"https://github.com/{owner}/{repo}",
        "forks": forks
    }

    output_file = f"forks_{owner}_{repo}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(body, f, indent=2)
