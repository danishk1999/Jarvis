import json
import requests
import threading
from datetime import datetime, timedelta
from pathlib import Path

STORE_DIR = Path("memory_store")

# ── Notification callback — injected at startup by main.py or telegram_bot.py ──
_notification_callback = None

def set_notification_callback(fn):
    global _notification_callback
    _notification_callback = fn

# Keep old name as alias so telegram_bot.py still works
set_telegram_sender = set_notification_callback


# ── Notes ──────────────────────────────────────────────────────────────────
NOTES_FILE = STORE_DIR / "notes.json"

def _load_notes():
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text())
    return []

def _save_notes(notes):
    STORE_DIR.mkdir(exist_ok=True)
    NOTES_FILE.write_text(json.dumps(notes, indent=2))

def save_note(content: str, tags: list = None) -> str:
    notes = _load_notes()
    note = {
        "id": len(notes) + 1,
        "content": content,
        "tags": tags or [],
        "created": datetime.now().isoformat(),
    }
    notes.append(note)
    _save_notes(notes)
    return f"Note #{note['id']} saved."

def get_notes(tag: str = None, limit: int = 10) -> str:
    notes = _load_notes()
    if tag:
        notes = [n for n in notes if tag.lower() in [t.lower() for t in n.get("tags", [])]]
    notes = notes[-limit:]
    if not notes:
        return "No notes found."
    lines = []
    for n in notes:
        tags = f" [{', '.join(n['tags'])}]" if n.get("tags") else ""
        date = n["created"][:10]
        lines.append(f"[{n['id']}] ({date}){tags} {n['content']}")
    return "\n".join(lines)

def delete_note(note_id: int) -> str:
    notes = _load_notes()
    filtered = [n for n in notes if n["id"] != note_id]
    if len(filtered) == len(notes):
        return f"Note #{note_id} not found."
    _save_notes(filtered)
    return f"Note #{note_id} deleted."


# ── Todos ──────────────────────────────────────────────────────────────────
TODOS_FILE = STORE_DIR / "todos.json"

def _load_todos():
    if TODOS_FILE.exists():
        return json.loads(TODOS_FILE.read_text())
    return []

def _save_todos(todos):
    STORE_DIR.mkdir(exist_ok=True)
    TODOS_FILE.write_text(json.dumps(todos, indent=2))

def add_todo(task: str, priority: str = "normal") -> str:
    todos = _load_todos()
    todo = {
        "id": len(todos) + 1,
        "task": task,
        "priority": priority,
        "done": False,
        "created": datetime.now().isoformat(),
    }
    todos.append(todo)
    _save_todos(todos)
    return f"Task #{todo['id']} added: {task}"

def complete_todo(todo_id: int) -> str:
    todos = _load_todos()
    for t in todos:
        if t["id"] == todo_id:
            t["done"] = True
            _save_todos(todos)
            return f"Task #{todo_id} marked as done."
    return f"Task #{todo_id} not found."

def list_todos(show_done: bool = False) -> str:
    todos = _load_todos()
    if not show_done:
        todos = [t for t in todos if not t["done"]]
    if not todos:
        return "No pending tasks." if not show_done else "No tasks found."
    lines = []
    for t in todos:
        status = "✓" if t["done"] else "○"
        priority = f" [{t['priority']}]" if t["priority"] != "normal" else ""
        lines.append(f"{status} [{t['id']}]{priority} {t['task']}")
    return "\n".join(lines)

def delete_todo(todo_id: int) -> str:
    todos = _load_todos()
    filtered = [t for t in todos if t["id"] != todo_id]
    if len(filtered) == len(todos):
        return f"Task #{todo_id} not found."
    _save_todos(filtered)
    return f"Task #{todo_id} deleted."


# ── Weather ────────────────────────────────────────────────────────────────
def get_weather(location: str = "Calgary") -> str:
    try:
        r = requests.get(f"https://wttr.in/{location}?format=j1", timeout=10)
        if r.status_code != 200:
            return f"Couldn't fetch weather for {location}."
        data = r.json()
        c = data["current_condition"][0]
        today = data["weather"][0]
        return (
            f"Weather in {location}: {c['weatherDesc'][0]['value']}\n"
            f"Temperature: {c['temp_C']}°C (feels like {c['FeelsLikeC']}°C)\n"
            f"Today: {today['mintempC']}°C – {today['maxtempC']}°C\n"
            f"Humidity: {c['humidity']}% | Wind: {c['windspeedKmph']} km/h"
        )
    except Exception as e:
        return f"Weather lookup failed: {e}"


# ── Web search ─────────────────────────────────────────────────────────────
def web_search(query: str, max_results: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=min(max_results, 10)):
                results.append(f"• {r['title']}\n  {r['href']}\n  {r['body'][:200]}")
        return "\n\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


# ── Reminders ─────────────────────────────────────────────────────────────
def set_reminder(message: str, minutes: int) -> str:
    def fire():
        text = f"⏰ Reminder: {message}"
        if _notification_callback:
            _notification_callback(text)
        else:
            print(text)

    t = threading.Timer(minutes * 60, fire)
    t.daemon = True
    t.start()

    run_at = (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M")
    return f"Reminder set for {run_at} ({minutes} min from now): '{message}'"


# ── Job search (thin wrapper around existing module) ───────────────────────
def search_jobs(keywords: str = "IT Support", location: str = "Calgary") -> str:
    try:
        from job_search import search_adzuna
        results = search_adzuna(keywords, location)
        if not results:
            return f"No jobs found for '{keywords}' in {location}."
        lines = []
        for job in results[:5]:
            title = job.get("title", "Unknown")
            company = job.get("company", {}).get("display_name", "Unknown")
            url = job.get("redirect_url", "")
            lines.append(f"• {title} @ {company}\n  {url}")
        return f"Jobs for '{keywords}' in {location}:\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"Job search failed: {e}"


# ── Morning briefing ───────────────────────────────────────────────────────
def get_briefing(location: str = "Calgary") -> str:
    parts = [f"Good morning! Here's your briefing for {datetime.now().strftime('%A, %B %d')}.\n"]

    weather = get_weather(location)
    parts.append(f"WEATHER\n{weather}")

    todos = list_todos(show_done=False)
    parts.append(f"PENDING TASKS\n{todos}")

    try:
        from job_search import fetch_all_jobs
        jobs = fetch_all_jobs()
        parts.append(f"NEW JOBS\n{len(jobs)} new job(s) found. Use /jobs for the full list.")
    except Exception:
        pass

    return "\n\n".join(parts)


# ── Tool definitions for the Claude API ───────────────────────────────────
TOOL_DEFINITIONS = [
    {
        "name": "save_note",
        "description": "Save a note or piece of information for later retrieval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The note content"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags to categorize the note",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "get_notes",
        "description": "Retrieve saved notes, optionally filtered by tag.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Filter notes by this tag"},
                "limit": {"type": "integer", "description": "Max notes to return (default 10)"},
            },
        },
    },
    {
        "name": "delete_note",
        "description": "Delete a note by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_id": {"type": "integer", "description": "The note ID to delete"}
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "add_todo",
        "description": "Add a task to the to-do list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The task description"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "description": "Task priority (default: normal)",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "complete_todo",
        "description": "Mark a to-do task as completed by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "integer", "description": "The task ID to mark done"}
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "list_todos",
        "description": "List to-do tasks. By default shows only pending tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "show_done": {
                    "type": "boolean",
                    "description": "Include completed tasks (default false)",
                }
            },
        },
    },
    {
        "name": "delete_todo",
        "description": "Delete a to-do task by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "integer", "description": "The task ID to delete"}
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather and today's forecast for a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location (default: Calgary)",
                }
            },
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for news, information, or any query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 10)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Set a reminder that fires as a Telegram notification after N minutes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The reminder message"},
                "minutes": {
                    "type": "integer",
                    "description": "Minutes from now to send the reminder",
                },
            },
            "required": ["message", "minutes"],
        },
    },
    {
        "name": "search_jobs",
        "description": "Search for IT jobs in Calgary, Edmonton, or remote Canada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Job title or keywords (default: IT Support)",
                },
                "location": {
                    "type": "string",
                    "description": "Location to search (default: Calgary)",
                },
            },
        },
    },
    {
        "name": "get_briefing",
        "description": "Generate a morning briefing with weather, pending tasks, and new job count.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City for weather (default: Calgary)",
                }
            },
        },
    },
]


def execute_tool(name: str, params: dict) -> str:
    dispatch = {
        "save_note": lambda p: save_note(p["content"], p.get("tags")),
        "get_notes": lambda p: get_notes(p.get("tag"), p.get("limit", 10)),
        "delete_note": lambda p: delete_note(p["note_id"]),
        "add_todo": lambda p: add_todo(p["task"], p.get("priority", "normal")),
        "complete_todo": lambda p: complete_todo(p["todo_id"]),
        "list_todos": lambda p: list_todos(p.get("show_done", False)),
        "delete_todo": lambda p: delete_todo(p["todo_id"]),
        "get_weather": lambda p: get_weather(p.get("location", "Calgary")),
        "web_search": lambda p: web_search(p["query"], p.get("max_results", 5)),
        "set_reminder": lambda p: set_reminder(p["message"], p["minutes"]),
        "search_jobs": lambda p: search_jobs(p.get("keywords", "IT Support"), p.get("location", "Calgary")),
        "get_briefing": lambda p: get_briefing(p.get("location", "Calgary")),
    }
    fn = dispatch.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    try:
        return fn(params)
    except Exception as e:
        return f"Tool '{name}' error: {e}"
