import requests
import json
import re
from datetime import datetime

ASANA_ACCESS_TOKEN = "2/1207986152477905/1211255467312096:7bff2c6868b77ee35049b98f5349e280"
BASE_URL = "https://app.asana.com/api/1.0"

headers = {
    "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}"
}

def fetch_asana_projects():
    try:
        response = requests.get(f"{BASE_URL}/projects", headers=headers)
        response.raise_for_status()
        return response.json().get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching projects: {e}")
        return []

def fetch_project_sections(project_gid: str):
    try:
        url = f"{BASE_URL}/projects/{project_gid}/sections"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        return res.json().get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching sections: {e}")
        return []

def fetch_section_tasks(section_gid: str):
    try:
        url = f"{BASE_URL}/sections/{section_gid}/tasks"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        return res.json().get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching tasks: {e}")
        return []

def parse_identity_from_description(description: str):
    """Extract Brand Type and Currency Type from description text."""
    brand_match = re.search(r"Brand\s*Type:\s*(\w+)", description or "", re.IGNORECASE)
    currency_match = re.search(r"Currency\s*Type:\s*(\w+)", description or "", re.IGNORECASE)

    return {
        "brand": brand_match.group(1) if brand_match else None,
        "currency": currency_match.group(1) if currency_match else None
    }

def fetch_task_comments(task_gid: str):
    """Fetch comments (stories) for a task."""
    try:
        url = f"{BASE_URL}/tasks/{task_gid}/stories"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        stories = res.json().get("data", [])

        comments = []
        for story in stories:
            if story.get("type") == "comment":
                comments.append({
                    "gid": story.get("gid"),
                    "created_at": story.get("created_at"),
                    "created_by": story.get("created_by", {}).get("name"),
                    "text": story.get("text")
                })

        return comments
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching comments for task {task_gid}: {e}")
        return []

def fetch_task_attachments(task_gid: str):
    """Fetch attachments for a task."""
    try:
        url = f"{BASE_URL}/tasks/{task_gid}/attachments"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        attachments = res.json().get("data", [])

        return [
            {
                "gid": att.get("gid"),
                "name": att.get("name"),
                "download_url": att.get("download_url"),
                "created_at": att.get("created_at"),
                "created_by": att.get("created_by", {}).get("name")
            }
            for att in attachments
        ]
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching attachments for task {task_gid}: {e}")
        return []

def fetch_task_details(task_gid: str):
    """Fetch full task details: title, description, identity, comments, attachments."""
    try:
        url = f"{BASE_URL}/tasks/{task_gid}"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json().get("data", {})
        description = data.get("notes", "")

        identity = parse_identity_from_description(description)
        comments = fetch_task_comments(task_gid)
        attachments = fetch_task_attachments(task_gid)

        return {
            "gid": data.get("gid"),
            "title": data.get("name"),
            "description": description,
            "identity": identity,
            "comments": comments,
            "attachments": attachments
        }
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching task {task_gid}: {e}")
        return {
            "gid": task_gid,
            "title": None,
            "description": None,
            "identity": {},
            "comments": [],
            "attachments": []
        }

def fetch_project_structure(project_gid: str):
    project_data = []
    sections = fetch_project_sections(project_gid)

    for section in sections:
        tasks = fetch_section_tasks(section["gid"])
        enriched_tasks = []
        for task in tasks:
            details = fetch_task_details(task["gid"])
            enriched_tasks.append(details)

        project_data.append({
            "section_name": section["name"],
            "section_gid": section["gid"],
            "task_count": len(enriched_tasks),
            "tasks": enriched_tasks
        })
    
    return project_data

if __name__ == "__main__":
    projects = fetch_asana_projects()
    target_project_gid = "1207974428313657"  # Example: "New Campaign"
    project_structure = fetch_project_structure(target_project_gid)

    print(json.dumps(project_structure, indent=2, ensure_ascii=False))
