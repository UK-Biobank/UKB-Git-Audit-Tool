# UKB-Git-Audit-Tool
The UKB-Git-Audit-Tool is a utility designed to audit Git repositories for potential exposure of UK Biobank data. It performs a comprehensive scan of the repository’s commit history—including deleted files—to identify and flag content that may contain sensitive information.

The tool supports both executable and Python script modes, making it suitable for a range of environments and workflows.


## Features

- **Automated Scanning:** Scans your Git repository for files containing UK Biobank data.
- **Comprehensive Audit:** Checks full commit history, including deleted files.
- **Clear Reporting:** Generates detailed reports highlighting potential data breaches.
- **Cross-Platform:** Works on Windows as an executable, or can be run as a Python script.
- **Fully Tested:** Comprehensive test suite with 78+ tests ensuring reliability.

## Getting Started (with the .exe for Windows)

0. **Install** Git on your computer if not done already 
1. **Download** the latest release from the [releases page](https://github.com/UK-Biobank/UKB-Git-Audit-Tool/releases).
2. **Place** the executable in the root directory of your Git repository.
3. **Run** the ukb-git-audit-tool.exe tool
4. **Enter** option 1 (Run in the current directory)


## Alternative Installation and Usage (Python-based)

If you are unable to run the executable file, you can use the Python source code directly.

### Prerequisites
- Python version >=3.10 and <3.15
- Git must be installed (the tool will check and notify you if it's not)
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
- **Options 1 & 2 are recommended** for auditing private repositories, as it uses the Git credentials already configured in your local environment.
- Option 3 will attempt to clone the repository using the provided URL.
- If authentication fails, you'll receive clear error messages explaining how to resolve the issue.
- The tool will clone the repository and perform the audit, but may duplicate the repository inside your current directory (a known issue to be resolved in future versions).

### What's New in v1.2
- ✅ **Fixed Critical Bug:** Resolved `AttributeError: 'NoneType' object has no attribute 'split'` when running in repositories without a remote URL
- ✅ **Environment Validation:** Tool now checks Git installation and repository status before starting
- ✅ **Better Error Messages:** Clear, actionable guidance for all error scenarios
- ✅ **Private Repo Detection:** Automatically detects and provides guidance for private repositories
- ✅ **Batch Processing Improvements:** Better validation and progress tracking for CSV batch audits
- ✅ **Comprehensive Testing:** Added 78+ automated tests to ensure reliability

### Output Directory

All audit reports are saved to the `ukb_audit_reports/` folder in your current working directory:

```
your-repo/
├── ukb_audit_reports/
│   ├── REPOSITORY_AUDIT_REPORT_your-repo.csv
│   ├── eid_frequency_your-repo.csv
│   └── AUDIT_SUMMARY_your-repo.html
├── .gitignore  (should include ukb_audit_reports/)
└── ...
```

**IMPORTANT**: The tool will prompt you to add `ukb_audit_reports/` to your `.gitignore` file to prevent accidentally committing sensitive audit data.

### Output Files

| File Name     | Format | Description |
| ------------- | ------ | ----------- |
| REPOSITORY_AUDIT_REPORT_{repo}.csv | CSV  | Detailed list of all files in the repository with audit metrics, match counts, and GitHub links |
| eid_frequency_{repo}.csv | CSV | Frequency table of all detected potential EIDs, sorted by occurrence count |
| AUDIT_SUMMARY_{repo}.html | HTML | Visual summary report with disclaimers, statistics, and prioritized file lists |

### HTML Summary Report

The HTML summary report provides:
- **Visual overview** of findings with clear disclaimers about false positives
- **False positive guidance**: Explanation of genomic coordinates (chr1:5234567) vs real participant IDs
- **High-priority files**: Non-genomic files requiring manual review, with direct GitHub links
- **File type breakdown**: Statistics by file extension to identify genomic data vs phenotype data
- **Top frequent "EIDs"**: Most common matches with warnings for likely coordinates (>1000 occurrences)

The report automatically opens in your default browser after each audit completes.

## Development & Testing

### Running Tests
The project includes a comprehensive test suite with 78+ tests covering all functionality.

```bash
# Install all dependencies including dev/test dependencies
poetry install

# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

### Project Structure
```
UKB-Git-Audit-Tool/
├── src/
│   ├── main.py                    # Main entry point with 4 execution modes
│   ├── git_audit.py               # Core audit logic
│   ├── utilities.py               # Helper functions
│   └── environment_validator.py   # Validation & environment checks (NEW)
├── tests/
│   ├── test_environment_validator.py  # Validation tests (36 tests)
│   ├── test_main.py                   # Main execution tests (15 tests)
│   └── test_git_audit.py              # Audit logic tests (27 tests)
└── requirements.txt               # Production dependencies
```

## Contributing
Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or improvements.

**Before submitting:**
1. Ensure all tests pass: `poetry run pytest`
2. Add tests for new features
3. Update documentation as needed

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer
See [DISCLAIMER](DISCLAIMER.md) for details.
