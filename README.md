# Dify Knowledge Base Sync Script

This script allows you to synchronize files from various folders within a Wimi workspace to the Dify knowledge base. It supports removing duplicates, including subfolders in processing, and verbose logging for detailed output.

The provided script synchronizes various file types between Wimi and Dify. By default, Dify accepts files with the following extensions: `.txt`, `.md`, `.pdf`, `.html`, `.htm`, `.xlsx`, `.xls`, and `.csv`. If Dify is configured to use Unstructured, additional file types are supported, including `.csv`, `.eml`, `.msg`, `.epub`, `.xlsx`, `.xls`, `.html`, `.htm`, `.md`, `.markdown`, `.pdf`, `.txt`, `.ppt`, `.pptx`, `.docx`, and `.xml`. Additionally, certain extensions are processed by converting them to text, which includes files with extensions: `.htm`, `.org`, `.odt`, `.text`, `.log`, `.rst`, `.rtf`, `.tsv`, `.json`, and `.doc`.

When a file is removed from Wimi, it is also automatically removed from Dify to ensure consistency. The script is designed to re-parse only the files that have been modified since their last synchronization, optimizing efficiency by avoiding unnecessary processing. The `folders` argument allows users to specify which Wimi folders should be synchronized, accepting a comma-separated list of folder names or identifiers. The `workspace` argument designates the project workspace within Wimi; it can be a single workspace applied to all specified folders or a comma-separated list corresponding to each folder. This setup provides precise control over which files are synchronized and how they are organized within Dify.

## Requirements

- Python 3.x
- Required Python packages: `tqdm`, `python-dotenv`, `requests`

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ArnaudGardille/sync-wimi
   cd sync-wimi
   ```

2. **Install dependencies**:

   With Python 3.10 installed, run :
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the root directory with the following content:
   ```env
   WIMI_API_URL = "https://api.wimi.pro"
   WIMI_DOWNLOAD_URL = "https://api.files.wimi.pro"
   WIMI_ACCOUNT_ID=<your_wimi_account_id>
   WIMI_USER_ID=<your_wimi_user_id>
   WIMI_LOGIN=<your_wimi_login>
   WIMI_PASSWORD=<your_wimi_password>
   WIMI_API_KEY=<your_wimi_api_key>
   DIFY_API_URL='http://my.vigie.ai/v1'
   DIFY_API_KEY=<your_dify_api_key>
   ```

## Usage

### Command-Line Arguments

| Argument              | Type    | Description                                                                                   | Default     |
|-----------------------|---------|-----------------------------------------------------------------------------------------------|-------------|
| `--dify-api-url`      | `str`   | Dify API URL                                                                                  | None        |
| `--dify-api-key`      | `str`   | Dify API Key                                                                                  | None        |
| `--knowledge-name`    | `str`   | Knowledge Base Name                                                                           | None        |
| `--folders`           | `str`   | Comma-separated list of Folder Identifiers or Names                                           | `root`      |
| `--remove-duplicates` | `flag`  | Remove duplicate documents                                                                    | `False`     |
| `--include-subfolders`| `flag`  | Include subfolders in processing                                                              | `False`     |
| `--verbose`           | `flag`  | Verbose logging                                                                               | `False`     |
| `--workspace`         | `str`   | Workspace for all folders or comma-separated list for each folder                             | `General`   |

### Example Usage

1. **Synchronize files from the "General" workspace, including subfolders, and remove duplicates**:
   ```bash
   python sync_script.py --folders "root" --workspace "General" --include-subfolders --remove-duplicates
   ```

2. **Synchronize files from multiple workspaces and folders with verbose logging**:
   ```bash
   python sync_script.py --folders "root,folder1,folder2" --workspace "General,Workspace1,Workspace2" --verbose
   ```

### Detailed Description

1. **Authentication**:
    - The script authenticates with the Wimi API using credentials provided in the `.env` file.
    - It retrieves all available projects (workspaces) during authentication.

2. **Workspace and Folder Processing**:
    - The script allows specifying either a single workspace for all folders or a different workspace for each folder.
    - It processes the folders recursively if the `--include-subfolders` flag is set.

3. **File Synchronization**:
    - The script synchronizes files from the specified folders to the Dify knowledge base.
    - It removes duplicate documents if the `--remove-duplicates` flag is set.

4. **Verbose Logging**:
    - The script provides detailed output if the `--verbose` flag is set, including the list of available documents and updates performed.

## Script Structure

The script consists of the following key components:

1. **Command-Line Argument Parsing**:
   - Defines the arguments required to run the script.

2. **Environment Configuration**:
   - Loads environment variables from the `.env` file.

3. **WimiFileSource Class**:
   - Handles authentication with Wimi.
   - Retrieves projects and sets the appropriate project based on user input.
   - Lists files and folders in the specified project.
   - Downloads files from Wimi.

4. **Helper Functions**:
   - Converts date strings to timestamps.
   - Removes multiple extensions from filenames.

5. **Main Script Logic**:
   - Authenticates with Wimi to retrieve projects.
   - Processes files for each specified workspace and folder.
   - Synchronizes files with the Dify knowledge base.

## Running the Script Periodically on a Linux Machine Using Cron

To run the script periodically on a Linux machine, you can use the cron scheduler. Cron allows you to schedule commands or scripts to run at specified intervals. Here's how you can set up the script to run every 5 minutes:

1. **Open the Crontab File**:
   - Open a terminal and type `crontab -e` to edit the crontab file.

2. **Add a New Cron Job**:
   - Add the following line to the crontab file to run the script every 5 minutes:
     ```bash
     */5 * * * * /usr/bin/python3 /path/to/your/script.py --dify-api-url "https://api.dify.ai" --dify-api-key "your_dify_api_key" --knowledge-name "My Knowledge Base" --folders "root" --workspace "General" --include-subfolders --remove-duplicates
     ```
   - Replace `/usr/bin/python3` with the path to your Python executable if it's different.
   - Replace `/path/to/your/script.py` with the actual path to your script.
   - Adjust the command-line arguments as needed for your specific use case.

3. **Save and Exit**:
   - Save the changes and exit the editor. The cron job will now run the script every 5 minutes.

By following these steps, you can ensure that the script runs periodically and keeps your Dify knowledge base synchronized with the files in your Wimi workspaces.