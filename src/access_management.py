import os, sys


def get_github_token():
    """
    Retrieves the GitHub PAT from a bundled file or an environment variable.
    """
    pat = ""
    # Check for the token file, bundled by PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        try:
            # The token file will be in the temporary PyInstaller directory
            token_path = os.path.join(sys._MEIPASS, 'GAT_PAT')
            if os.path.exists(token_path):
                with open(token_path, 'r') as f:
                    pat = f.read().strip()
        except Exception:
            print("Error reading the token file.")
    
    # If not found in the file, fall back to environment variable
    if not pat:
        pat = os.getenv("GAT_PAT", "")
    return pat