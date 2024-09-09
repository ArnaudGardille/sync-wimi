import os
import io
import argparse
from tqdm import tqdm
from dotenv import load_dotenv
import requests
import json
import uuid
from datetime import datetime
from unstructured.partition.auto import partition

SUPPORTED_EXTENSIONS_DIFY = [".txt", ".md", ".md", ".pdf", ".html", ".htm", ".xlsx", ".xls", ".csv"]
SUPPORTED_EXTENSIONS_UNSTRUCTURED = [".csv", ".eml", ".msg", ".epub", ".xlsx", ".xls", ".html", ".htm", ".md", ".markdown", ".pdf", ".txt", ".pptx", ".docx", ".xml"]

# Define command-line arguments
parser = argparse.ArgumentParser(description="Sync files with Dify knowledge base.")
parser.add_argument('--dify-api-url', type=str, help='Dify API URL')
parser.add_argument('--dify-api-key', type=str, help='Dify API Key')
parser.add_argument('--knowledge-name', type=str, help='Knowledge Base Name')
parser.add_argument('--folders', type=str, help='Comma-separated list of Folder Identifiers or Names', default='root')
parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicate documents')
parser.add_argument('--include-subfolders', action='store_true', help='Include subfolders in processing')
parser.add_argument('--verbose', action='store_true', help='Verbose logging')
parser.add_argument('--workspace', type=str, help='Workspace for all folders or comma-separated list for each folder', default='General')

args = parser.parse_args()
load_dotenv()

# Define retry strategy
retry_strategy = requests.adapters.Retry(
    total=3,
    backoff_factor=1,
)

# Create a session and mount an adapter with the retry strategy
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

class Document:
    def __init__(self, name: str, id: str, date: float, mime_type=None, workspace_id=None):
        self.name = name
        self.id = id
        self.date = float(date)
        self.mime_type = mime_type
        self.workspace_id = workspace_id

    def __str__(self):
        return f'{self.name}, {self.id}, {self.date}'

class DifyKnowledgeClient:
    def __init__(self, DIFY_API_URL=None, DIFY_API_KEY=None, KNOWLEDGE_NAME=None):
        self.DIFY_API_URL = DIFY_API_URL or os.getenv('DIFY_API_URL')
        self.DIFY_API_KEY = DIFY_API_KEY or os.getenv('DIFY_API_KEY')
        self.KNOWLEDGE_NAME = KNOWLEDGE_NAME or os.getenv('KNOWLEDGE_NAME')

        self.HEADERS = {
            'Authorization': f'Bearer {self.DIFY_API_KEY}',
            "Content-Type": "application/json"
        }

        self.KNOWLEDGE_ID = self.get_or_create_knowledge(self.KNOWLEDGE_NAME)

    def get_or_create_knowledge(self, name):
        url = f"{self.DIFY_API_URL}/datasets"
        response = session.get(url, headers=self.HEADERS, params={"limit": 100})

        if response.status_code == 200:
            datasets = response.json().get('data', [])
            for dataset in datasets:
                if dataset['name'] == name:
                    print(f"Found knowledge base: {name}")
                    return dataset['id']

        print(f"Creating new knowledge: {name}")
        data = {"name": name}
        response = session.post(url, headers=self.HEADERS, json=data)

        if response.status_code in [200, 201]:
            return response.json()['id']
        else:
            raise Exception("Failed to create knowledge base:" + str(response.text))

    def get_existing_documents(self):
        url = f"{self.DIFY_API_URL}/datasets/{self.KNOWLEDGE_ID}/documents"

        has_more = True
        documents = set()
        page = 1
        while has_more:
            response = session.get(url, headers=self.HEADERS, params={"limit": 100, "page": page})
            if response.status_code == 200:
                has_more = response.json().get('has_more', False)
                page += 1
                documents.update({Document(name=doc['name'], id=doc['id'], date=doc['created_at']) for doc in response.json().get('data', [])})
            else:
                raise Exception(f"Failed to fetch existing documents: {response.text}")
        return documents

    def upload_document(self, document_name, document_content):
        url = f"{self.DIFY_API_URL}/datasets/{self.KNOWLEDGE_ID}/document/create_by_file"

        data_payload = {
            "indexing_technique": "high_quality",
            "process_rule": {
                "mode": "automatic",
                "rules": {
                    "pre_processing_rules": [
                        {"id": "remove_extra_spaces", "enabled": True},
                        {"id": "remove_urls_emails", "enabled": True}
                    ],
                    "segmentation": {
                        "separator": "\n",
                        "max_tokens": 1000
                    }
                }
            }
        }

        files = {
            'data': (None, json.dumps(data_payload), 'application/json'),
            'file': (document_name, document_content, 'application/octet-stream')
        }

        response = session.post(url, headers={'Authorization': f'Bearer {self.DIFY_API_KEY}'}, files=files)
        try:
            return response.json()['document']
        except KeyError:
            print("KeyError with", document_name)
            print(response.json())
            raise KeyError

    def upload_text(self, document_name: str, text: str):
        url = f"{self.DIFY_API_URL}/datasets/{self.KNOWLEDGE_ID}/document/create_by_text"

        data_payload = {
            "name": document_name,
            "text": text,
            "indexing_technique": "high_quality",
            "process_rule": {
                "mode": "automatic",
                "rules": {
                    "pre_processing_rules": [
                        {"id": "remove_extra_spaces", "enabled": True},
                        {"id": "remove_urls_emails", "enabled": True}
                    ],
                    "segmentation": {
                        "separator": "\n",
                        "max_tokens": 1000
                    }
                }
            }
        }

        response = session.post(url, headers={'Authorization': f'Bearer {self.DIFY_API_KEY}'}, json=data_payload)
        return response.json()['document']

    def update_document(self, document_name, document_id, document_content):
        url = f"{self.DIFY_API_URL}/datasets/{self.KNOWLEDGE_ID}/documents/{document_id}/update_by_file"

        data_payload = {
            "process_rule": {
                "mode": "automatic",
                "rules": {
                    "pre_processing_rules": [{"id": "remove_extra_spaces", "enabled": True},
                                            {"id": "remove_urls_emails", "enabled": True}],
                    "segmentation": {"separator": "\n", "max_tokens": 1000}
                }
            }
        }

        files = {
            'data': (None, json.dumps(data_payload), 'application/json'),
            'file': (document_name, document_content, 'application/octet-stream')
        }

        response = session.post(url, headers={'Authorization': f'Bearer {self.DIFY_API_KEY}'}, files=files)

        try:
            return response.json()['document']
        except KeyError:
            print("Deleting document and performing again...")
            self.delete_document(document_id)
            self.upload_document(document_name, document_content)

    def update_text(self, document_name, document_id, text):
        url = f"{self.DIFY_API_URL}/datasets/{self.KNOWLEDGE_ID}/documents/{document_id}/update_by_text"

        data_payload = {
            "name": document_name,
            "text": text,
            "process_rule": {
                "mode": "automatic",
                "rules": {
                    "pre_processing_rules": [{"id": "remove_extra_spaces", "enabled": True},
                                            {"id": "remove_urls_emails", "enabled": True}],
                    "segmentation": {"separator": "\n", "max_tokens": 1000}
                }
            }
        }

        response = session.post(url, headers={'Authorization': f'Bearer {self.DIFY_API_KEY}'}, json=data_payload)
        return response.json()['document']

    def delete_document(self, document_id):
        url = f"{self.DIFY_API_URL}/datasets/{self.KNOWLEDGE_ID}/documents/{document_id}"

        response = session.delete(url, headers=self.HEADERS)

        if response.status_code == 200:
            print(f"Document {document_id} deleted successfully.")
        else:
            print(f"Failed to delete document {document_id}. Status code: {response.status_code}")

class WimiFileSource:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.projects = None
        self.BASE_URL = os.getenv('WIMI_API_URL')
        self.DOWNLOAD_URL = os.getenv('WIMI_DOWNLOAD_URL')
        self.account_id = os.getenv('WIMI_ACCOUNT_ID')
        self.user_id = os.getenv('WIMI_USER_ID')
        self.login = os.getenv('WIMI_LOGIN')
        self.password = os.getenv('WIMI_PASSWORD')
        self.app_token = os.getenv('WIMI_API_KEY')
        self.extensions = SUPPORTED_EXTENSIONS_UNSTRUCTURED if os.getenv('UNSTRUCTURED') else SUPPORTED_EXTENSIONS_DIFY

    def authenticate(self):
        payload = {
            "header": {
                "app_token": self.app_token,
                "api_version": "1.2",
                "msg_key": f"auth.user.login.{str(uuid.uuid4())}",
                "identification": {"account_id": self.account_id},
                "target": "auth.user.login",
                "debug": {"indent_output": True},
                "auth": {"login": self.login, "password": self.password}
            },
            "body": {
                "data": {
                    "token": None,
                    "list_projects": True,
                    "projects_auth": True,
                    "projects_stats": True,
                    "projects_tasks_stats": True,
                    "projects_users": True,
                    "manual": True,
                    "csrf_security": True,
                    "fetch_pwd_sha": True
                }
            }
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.BASE_URL, headers=headers, data=json.dumps(payload))
        auth_response = response.json()
        assert auth_response and 'body' in auth_response and 'data' in auth_response['body']
        print("Authentication succeeded!")
        self.token = auth_response['header']['token']
        self.user_id = auth_response['body']['data']['user']['user_id']
        self.projects = auth_response['body']['data']['projects']

    def get_project_id(self, project_name_or_id):
        if project_name_or_id.isnumeric():
            return int(project_name_or_id)
        else:
            for project in self.projects:
                if project['name'] == project_name_or_id:
                    return project['project_id']
        raise ValueError(f"Project {project_name_or_id} not found")

    def list_files(self, project_id, folder_id=None):
        payload = {
            'header': {
                'target': 'document.entry.list',
                'api_version': '1.2',
                'app_token': self.app_token,
                'msg_key': str(uuid.uuid4()),
                'token': self.token,
                'identification': {
                    'account_id': self.account_id,
                    'user_id': self.user_id,
                    "project_id": project_id,
                }
            },
            'body': {'data': {'no_comment_count': True, 'process_thumbnail': True}}
        }

        if folder_id:
            payload["header"]["identification"]["dir_id"] = int(folder_id)

        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.BASE_URL, headers=headers, data=json.dumps(payload))
        files_dicts = response.json()["body"]["data"]["files"]

        files = []
        for d in files_dicts:
            if '.' + d["extension"] in self.extensions:
                files.append(Document(name=remove_multiple_extensions(d["name"]),
                                      id=d["file_id"],
                                      date=convert_to_timestamp(d["date"]),
                                      workspace_id=project_id
                                      ))
            else:
                print("Not supported file:", d["name"])

        return files

    def list_folders(self, project_id, folder_id=None):
        payload = {
            'header': {
                'target': 'document.entry.list',
                'api_version': '1.2',
                'app_token': self.app_token,
                'msg_key': str(uuid.uuid4()),
                'token': self.token,
                'identification': {
                    'account_id': self.account_id,
                    'user_id': self.user_id,
                    "project_id": project_id,
                }
            },
            'body': {'data': {'no_comment_count': True, 'process_thumbnail': True}}
        }

        if folder_id:
            payload["header"]["identification"]["dir_id"] = int(folder_id)

        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.BASE_URL, headers=headers, data=json.dumps(payload))

        return [(dir['name'], dir['dir_id']) for dir in response.json()["body"]["data"]["dirs"]]

    def list_files_recursive(self, wimi_project, folder_id) -> list[Document]:
        all_files = []

        # List files in the current folder
        files = self.list_files(wimi_project, folder_id)
        all_files.extend(files)

        # List folders in the current folder
        folders = self.list_folders(wimi_project, folder_id)

        # Recursively list files in each subfolder
        for subfolder_name, subfolder_id in folders:
            all_files.extend(self.list_files_recursive(wimi_project, subfolder_id))

        return all_files

    def download_file(self, document: Document):
        print("downloading", document.name)
        print("workspace_id", document.workspace_id)
        payload = {
            "header": {
                "target": "document.file.Download",
                "api_version": "1.2",
                "app_token": self.app_token,
                "msg_key": str(uuid.uuid4()),
                "token": self.token,
                "identification": {
                    "account_id": self.account_id,
                    "user_id": self.user_id,
                    "project_id": document.workspace_id,
                    "file_id": document.id,
                }
            },
            "body": {}
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.DOWNLOAD_URL, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Failed to download file. Status code: {response.status_code}")

def convert_to_timestamp(date_str):
    formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.timestamp()
        except ValueError:
            continue
    raise ValueError(f"Date string '{date_str}' does not match any expected format.")

def remove_multiple_extensions(filename):
    parts = filename.split('.')
    if len(parts) > 2:
        while parts[-1] == parts[-2]:
            parts = parts[:-1]
        return '.'.join(parts)
    return filename

def retrieve_files_from_folder(file_source, wimi_project, folder_identifier_or_name, include_subfolders=True, verbose=True):
    if folder_identifier_or_name == 'root':
        folder_identifier = None
    else:
        folders = file_source.list_folders(wimi_project)
        try:
            folder_identifier = [folder_id for (name, folder_id) in folders if name == folder_identifier_or_name][0]
        except IndexError:
            print(f"Folder {folder_identifier_or_name} not found")
            raise IndexError

    if include_subfolders:
        available_documents = file_source.list_files_recursive(wimi_project, folder_identifier)
    else:
        available_documents = file_source.list_files(wimi_project, folder_identifier)

    if verbose:
        print("Available documents")
        for doc in available_documents:
            print(doc)

    return available_documents

def synchronize_with_dify(all_documents, knowledge_client, file_source, remove_duplicates=True, verbose=True):
    existing_documents = knowledge_client.get_existing_documents()

    if verbose:
        print("Existing documents")
        for doc in existing_documents:
            print(doc)

    for file in tqdm(all_documents):
        document_name = file.name
        if verbose:
            print(f"\nProcessing file: {file.name} (ID: {file.id})")

        if document_name in [d.name for d in existing_documents]:
            document_with_name = [d for d in existing_documents if d.name == document_name]
            existing_document = max(document_with_name, key=lambda x: x.date)

            if remove_duplicates and len(document_with_name) > 1:
                sorted_documents = sorted(document_with_name, key=lambda x: x.date, reverse=True)[1:]
                for doc in sorted_documents:
                    knowledge_client.delete_document(doc.id)

            if existing_document.date <= file.date:
                extension = '.' + os.path.splitext(file.name)[1]
                if extension in SUPPORTED_EXTENSIONS_UNSTRUCTURED:
                    content_stream = io.BytesIO(file_source.download_file(file))
                    knowledge_client.update_document(document_name, existing_document.id, content_stream)
                print(f"Updated document: {document_name}")
            else:
                if verbose:
                    print(f"No need to update document: {document_name}")

        else:
            try:
                content_stream = io.BytesIO(file_source.download_file(file))
                extension = os.path.splitext(file.name)[1]
                if extension in SUPPORTED_EXTENSIONS_UNSTRUCTURED:
                    rep = knowledge_client.upload_document(document_name, content_stream)
                else:
                    if verbose:
                        print(f"Unsupported file type: {extension}")

            except Exception as e:
                print(f"Error uploading document: {document_name}")
                print("Trying again...")
                rep = knowledge_client.upload_document(document_name, content_stream)
                print("Success!")

            if verbose:
                print(f"Uploaded new document: {document_name}")
                print(rep)

    for doc in existing_documents:
        if doc.name not in [file.name for file in all_documents]:
            knowledge_client.delete_document(doc.id)
            if verbose:
                print(f"Deleted document no longer in drive: {doc.name}")

if __name__ == "__main__":
    wimi_source_provider = WimiFileSource()

    # Authenticate to retrieve projects
    wimi_source_provider.authenticate()

    folder_identifiers_or_names = [name.strip() for name in args.folders.split(',')]
    workspaces_input = [args.workspace] * len(folder_identifiers_or_names) if len(args.workspace.split(',')) == 1 else [name.strip() for name in args.workspace.split(',')]

    all_documents = []

    for workspace_input, folder_identifier_or_name in zip(workspaces_input, folder_identifiers_or_names):
        print(workspace_input, folder_identifier_or_name)
        wimi_project = wimi_source_provider.get_project_id(workspace_input)

        # Process files for the given workspace and folder
        documents = retrieve_files_from_folder(wimi_source_provider, wimi_project, folder_identifier_or_name, args.include_subfolders, args.verbose)

        all_documents.extend(documents)

    knowledge_client = DifyKnowledgeClient(DIFY_API_URL=args.dify_api_url, DIFY_API_KEY=args.dify_api_key, KNOWLEDGE_NAME=args.knowledge_name)

    synchronize_with_dify(all_documents, knowledge_client, wimi_source_provider, args.remove_duplicates, args.verbose)