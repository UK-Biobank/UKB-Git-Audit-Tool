# UKB-Git-Audit-Tool
Tool for auditing Git repos for potential data breaches concerning UK Biobank data. Scans commit history and flags files with sensitive content. Easy to use—just drop the executable into your repo and run.

## Features

- **Automated Scanning:** Scans your Git repository for files containing sensitive UK Biobank data.
- **Comprehensive Audit:** Checks entire commit history, inlcuding deleted files.
- **Customizable Rules:** Easily extend or modify patterns for sensitive data detection.
- **Clear Reporting:** Generates detailed reports highlighting potential data breaches.
- **Cross-Platform:** Works on Windows as an executable, or can be run as a Python script.

## Getting Started (with the .exe for Windows)

0. **Install** Git on your computer if not done already 
1. **Download** the latest release from the [releases page](https://github.com/UK-Biobank/UKB-Git-Audit-Tool/releases).
2. **Place** the executable in the root directory of your Git repository.
3. **Run** the ukb-git-audit-tool.exe tool

## Alternative Installation and Usage (Python-based)

If you are unable to run the executable file, you can use the Python source code directly.

### Prerequisites
- Python version >=3.10 and <3.15
- Git must be installed
- Poetry or pip for dependency management

### Installation with pip
1. Clone the repository to your local machine.
2. Navigate to the project directory.
3. Run `pip install -r requirements.txt` to install dependencies.
4. Execute the tool using `python src/main.py`.

### Installation with Poetry
1. Clone the repository to your local machine.
2. Navigate to the project directory.
3. Run `poetry install` to set up the environment.
4. Use `poetry run python src/main.py` to execute the tool.

### Script Options
Running the script or executable opens a terminal with the following options:
1. Run in the current directory (recommended for private repositories).
2. Enter a directory path to audit a cloned public repository.
3. Enter a repository URL to clone and audit (public only).
4. Submit a CSV file path for batch auditing multiple URLs.
5. Exit the program.

### Notes on Private Repositories
- Option 1 is recommended for auditing private repositories, as it uses the Git credentials already configured in your local environment.
- Options 2 and 3 attempt to clone the repository using the provided URL. For private repositories, this requires explicit authentication and may fail if credentials are not properly configured.
- If you wish to audit a private repository from another directory, ensure your Git credentials are accessible and provide the repository URL when prompted.
- The tool will clone the repository and perform the audit, but may duplicate the repository inside your current directory (a known issue to be resolved in future versions).

### Output Files
| File Name     | Format    | Description |
| --- | --- | --- |
| Audit report          | CSV   | Lists all files in the repository with audit and file metrics     |
| EID frequency table   | CSV   | Tracks potential EIDs and their frequency.                        |
| Forks                 | JSON  | Lists forks of the repository.                                    |
| Contributors table    | CSV   | Lists owner and contributors and their public email addresses.    |


## Contributing
Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or improvements.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer
See [DISCLAIMER](DISCLAIMER.md) for details.
