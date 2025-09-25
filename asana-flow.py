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

def parse_asana_sql_comment(comment_text: str):
    """Parse a structured Asana SQL comment into editable fields, supported values, and template script."""
    sections = re.split(r"\n\s*\n", comment_text.strip())
    data = {"editable_contents": {}, "supported_values": {}, "template_script": ""}

    for block in sections:
        if block.startswith("Editable Contents:"):
            for line in block.splitlines()[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    data["editable_contents"][key.strip()] = value.strip()

        elif block.startswith("List of Supported Values:"):
            for line in block.splitlines()[1:]:
                if ":" in line:
                    key, values = line.split(":", 1)
                    data["supported_values"][key.strip()] = [v.strip() for v in values.split(",")]

        elif block.startswith("Template Scripts:"):
            sql_lines = block.splitlines()[1:]
            data["template_script"] = "\n".join(sql_lines).strip()

    return data if data["template_script"] else None

def classify_input_fields(editable_contents, supported_values):
    """
    Convert editable_contents into structured input definitions:
      - type: 'date', 'select', or 'text'
      - options: only for 'select'
    """
    inputs = []

    for key, value in editable_contents.items():
        field = {"name": key, "default": value}

        # Rule 1: If key contains 'date' → Date Picker
        if "date" in key.lower():
            field["type"] = "date"

        # Rule 2: If supported values exist → Dropdown Select
        elif key in supported_values and supported_values[key]:
            field["type"] = "select"
            field["options"] = supported_values[key]

        # Rule 3: Otherwise → Normal Text Input
        else:
            field["type"] = "text"

        inputs.append(field)

    return inputs

def fetch_latest_sql_comment(task_gid: str):
    """Fetch the latest pinned SQL-style comment; fallback to latest unpinned if none pinned."""
    try:
        url = f"{BASE_URL}/tasks/{task_gid}/stories"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        stories = res.json().get("data", [])

        sql_comments = []
        pinned_comments = []

        for story in stories:
            if story.get("type") == "comment":
                parsed_sql = parse_asana_sql_comment(story.get("text", ""))
                if parsed_sql:
                    record = {
                        "gid": story.get("gid"),
                        "created_at": story.get("created_at"),
                        "created_by": story.get("created_by", {}).get("name"),
                        "parsed_sql": parsed_sql
                    }
                    sql_comments.append(record)
                    if story.get("is_pinned", False):
                        pinned_comments.append(record)

        if pinned_comments:
            # Return most recent pinned
            return max(pinned_comments, key=lambda c: c["created_at"])
        elif sql_comments:
            # Fallback: most recent SQL comment (unpinned)
            return max(sql_comments, key=lambda c: c["created_at"])
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching SQL comments for task {task_gid}: {e}")
        return None

def fetch_task_details(task_gid: str):
    """Fetch full task details but only latest pinned/fallback SQL comment."""
    try:
        url = f"{BASE_URL}/tasks/{task_gid}"
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json().get("data", {})
        description = data.get("notes", "")

        identity = parse_identity_from_description(description)
        latest_sql = fetch_latest_sql_comment(task_gid)

        # Build inputs
        inputs = []
        if latest_sql:
            editable = latest_sql["parsed_sql"]["editable_contents"]
            supported = latest_sql["parsed_sql"]["supported_values"]
            inputs = classify_input_fields(editable, supported)

        return {
            "gid": data.get("gid"),
            "title": data.get("name"),
            "description": description,
            "identity": identity,
            "latest_sql": latest_sql,
            "inputs": inputs  # <-- ready-to-use input schema
        }
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching task {task_gid}: {e}")
        return {
            "gid": task_gid,
            "title": None,
            "description": None,
            "identity": {},
            "latest_sql": None,
            "inputs": []
        }

def fetch_project_structure(project_gid: str):
    project_data = []
    sections = fetch_project_sections(project_gid)

    for section in sections:
        tasks = fetch_section_tasks(section["gid"])
        enriched_tasks = []
        for task in tasks:
            details = fetch_task_details(task["gid"])
            # Only include tasks with at least one SQL comment
            if details["latest_sql"]:
                enriched_tasks.append(details)

        if enriched_tasks:
            project_data.append({
                "section_name": section["name"],
                "section_gid": section["gid"],
                "task_count": len(enriched_tasks),
                "tasks": enriched_tasks
            })
    
    return project_data

if __name__ == "__main__":
    projects = fetch_asana_projects()
    target_project_gid = "1207974428313657"  # Example
    project_structure = fetch_project_structure(target_project_gid)

    print(json.dumps(project_structure, indent=2, ensure_ascii=False))
