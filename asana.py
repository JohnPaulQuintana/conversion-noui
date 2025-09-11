import requests
import json
from datetime import datetime

# Configuration
ASANA_ACCESS_TOKEN = "2/1207986152477905/1211255467312096:7bff2c6868b77ee35049b98f5349e280"
TASK_ID = "1211255490062639"
API_URL = f"https://app.asana.com/api/1.0/tasks/{TASK_ID}/stories"

def fetch_asana_projects():
    """
    Fetch all projects from Asana for the authorized user.
    Returns a list of projects with gid, name, and resource_type.
    """
    url = "https://app.asana.com/api/1.0/projects"
    headers = {
        "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        projects = response.json().get("data", [])
        return projects

    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error fetching projects: {e}")
        return []
    
def get_all_stories():
    """Get all stories/comments from Asana task"""
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ASANA_ACCESS_TOKEN}"
    }
    
    params = {
        "opt_fields": "gid,type,resource_subtype,text,is_pinned,created_at,created_by.name",
        "limit": 100  # Maximum per page
    }
    
    try:
        print(f"Fetching stories for task {TASK_ID}...")
        response = requests.get(API_URL, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        stories = data.get("data", [])
        
        print(f"Found {len(stories)} stories")
        print("-" * 80)
        
        # Filter and display only comments (excluding system events)
        comments = [
            story for story in stories 
            if story.get("type") == "comment" 
            and story.get("resource_subtype") == "comment_added"
        ]
        
        print(f"Comments found: {len(comments)}")
        print("-" * 80)
        
        for i, story in enumerate(stories, 1):
            created_at = story.get("created_at", "")
            created_by = story.get("created_by", {}).get("name", "Unknown")
            story_type = story.get("type", "")
            subtype = story.get("resource_subtype", "")
            text = story.get("text", "").strip()
            is_pinned = story.get("is_pinned", False)
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except:
                formatted_time = created_at
            
            print(f"{i}. [{formatted_time}] {created_by} - {story_type}.{subtype}")
            # if text:
            #     print(f"   Text: '{text}'")
            if is_pinned:
                print(f"   📌 PINNED")
            print()
            
        return stories
        
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None

def filter_comments_only(stories):
    """Filter only actual user comments"""
    if not stories:
        return []
    
    return [
        story for story in stories 
        if story.get("type") == "comment" 
        and story.get("resource_subtype") == "comment_added"
        and story.get("text", "").strip() != ""  # Exclude empty comments
    ]

if __name__ == "__main__":
    # Replace with your actual Asana access token
    # ASANA_ACCESS_TOKEN = "0/123456789abcdef..."  # Your token here
    projects = fetch_asana_projects()
    print(json.dumps(projects, indent=2))
    # stories = get_all_stories()
    # print("------------------------------------------------------")
    # print(stories)
    # print("------------------------------------------------------")
    # if stories:
    #     # Get only meaningful comments
    #     comments = filter_comments_only(stories)
    #     print(f"\n📝 MEANINGFUL COMMENTS FOUND: {len(comments)}")
    #     print("=" * 80)
        
    #     for i, comment in enumerate(comments, 1):
    #         created_at = comment.get("created_at", "")
    #         created_by = comment.get("created_by", {}).get("name", "Unknown")
    #         text = comment.get("text", "").strip()
    #         is_pinned = comment.get("is_pinned", False)
            
    #         try:
    #             dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    #             formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    #         except:
    #             formatted_time = created_at
            
    #         pin_status = "📌 " if is_pinned else ""
    #         print(f"{i}. {pin_status}[{formatted_time}] {created_by}:")
    #         print(f"   '{text}'")
    #         print()