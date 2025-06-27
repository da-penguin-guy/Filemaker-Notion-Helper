import requests
from dotenv import load_dotenv
import os

load_dotenv()

notionToken = os.getenv("NOTION_API_KEY")
if notionToken is None:
    raise ValueError("Notion API key not found. Please get the .env file provided")



headers = {
    "Authorization": f"Bearer {notionToken}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def CreateNotionPage(database_id, properties):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notionToken}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to create page:", response.text)
        return None
    
def ReadNotionDatabase(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to read database:", response.text)
        return None
    
def ReadPageProperties(page_id):
    page_url = f"https://api.notion.com/v1/pages/{page_id}"
    response = requests.get(page_url, headers=headers)
    return response.json()["properties"]