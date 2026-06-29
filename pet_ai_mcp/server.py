"""
Pet AI MCP Server
Safe, friendly tools for your personal AI companion.
"""

import asyncio
import base64
import datetime
import json
import os
import platform
import subprocess
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ─────────────────────────────────────────────
# Safety config
# ─────────────────────────────────────────────

BLOCKED_PATHS = {
    "/etc", "/sys", "/proc", "/dev", "/boot", "/root",
    "/var/log", "/var/run", "/private/etc", "/private/var",
    "C:\\Windows", "C:\\System32", "C:\\Program Files",
}

SAFE_MUSIC_DIRS = [
    Path.home() / "Music",
    Path.home() / "Downloads",
    Path.home() / "Desktop",
]

OPEN_WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# Memory storage file — sits next to server.py
MEMORY_FILE = Path(__file__).parent / "pet_ai_memory.json"

app = Server("pet-ai")

import time

_RECENT_ACTIONS: dict[tuple, float] = {}

def is_duplicate_action(action: tuple, window: float = 2.0) -> bool:
    now = time.time()

    # Remove expired entries
    expired = [k for k, t in _RECENT_ACTIONS.items() if now - t > window]
    for k in expired:
        del _RECENT_ACTIONS[k]

    if action in _RECENT_ACTIONS:
        return True

    _RECENT_ACTIONS[action] = now
    return False


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def is_safe_path(path_str: str) -> bool:
    try:
        p = Path(path_str).resolve()
    except Exception:
        return False
    for blocked in BLOCKED_PATHS:
        try:
            p.relative_to(Path(blocked).resolve())
            return False
        except ValueError:
            pass
    return True


def load_memory() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_memory(data: dict):
    MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────
# Tool definitions
# ─────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_time",
            description="Return the current local date and time.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_weather",
            description="Fetch current weather for a city. Requires OPENWEATHER_API_KEY env var.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. 'Ho Chi Minh City'"},
                    "units": {"type": "string", "enum": ["metric", "imperial"], "description": "metric=°C, imperial=°F. Default: metric."},
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="open_browser",
            description="Open exactly one browser tab. Open a URL directly, open the homepage for well-known sites (e.g. YouTube, GitHub, Reddit, Gmail), otherwise perform exactly one Google search. Never open more than one destination.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A URL (https://...) or plain search query."},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="play_music",
            description="Play a music file by name from Music, Downloads, or Desktop folder.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Partial or full filename, e.g. 'lofi' or 'bohemian'"},
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="list_folder",
            description="List contents of a folder. System directories are blocked.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or ~ path, e.g. '~/Documents'"},
                    "depth": {"type": "integer", "description": "Levels deep to list (1-3). Default: 1.", "minimum": 1, "maximum": 3},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="set_alarm",
            description="Set an alarm at a specific time. A popup and sound will appear at that time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time": {"type": "string", "description": "Time in HH:MM format (24h), e.g. '07:30'"},
                    "label": {"type": "string", "description": "Label for the alarm, e.g. 'Wake up!'"},
                },
                "required": ["time"],
            },
        ),
        Tool(
            name="set_reminder",
            description="Set a reminder at a specific date and time. A popup will appear.",
            inputSchema={
                "type": "object",
                "properties": {
                    "datetime_str": {"type": "string", "description": "Date and time as 'YYYY-MM-DD HH:MM', e.g. '2026-07-01 09:00'"},
                    "message": {"type": "string", "description": "Reminder message to show"},
                },
                "required": ["datetime_str", "message"],
            },
        ),
        Tool(
            name="schedule_shutdown",
            description="Schedule the PC to shut down at a specific time or after a delay.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["at_time", "after_minutes"], "description": "'at_time' for a specific clock time, 'after_minutes' for a countdown"},
                    "value": {"type": "string", "description": "For at_time: 'HH:MM'. For after_minutes: number of minutes as string, e.g. '30'"},
                    "cancel": {"type": "boolean", "description": "Set true to cancel any scheduled shutdown"},
                },
                "required": ["mode"],
            },
        ),
        Tool(
            name="find_file",
            description="Search for files by name anywhere in user directories. Safe paths only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename or partial name to search for, e.g. 'resume' or 'report.pdf'"},
                    "search_in": {"type": "string", "description": "Root folder to search in. Defaults to home directory (~)."},
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="find_largest_files",
            description="Find the top 5 largest files in a folder to help with cleanup. Does NOT delete anything.",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_in": {"type": "string", "description": "Folder to scan. Defaults to home directory (~)."},
                },
                "required": [],
            },
        ),
        Tool(
            name="create_file",
            description="Create a new file with a given name, extension, and optional content. Always asks for confirmation first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path for the new file, e.g. '~/Documents/notes.txt'"},
                    "content": {"type": "string", "description": "Text content to write into the file. Optional."},
                    "confirmed": {"type": "boolean", "description": "Must be true to actually create the file. If false or missing, just previews the action."},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="memory_set",
            description=(
                "Remember a piece of information as a key-value pair. "
                "IMPORTANT: the key must be short, simple, and human-readable — 1 to 3 words max, "
                "lowercase, no IDs, no suffixes like '_response' or '_123abc'. "
                "The key should describe WHAT is being remembered, not HOW to use it. "
                "Examples of GOOD keys: 'favorite_color', 'wake_time', 'pet_name', 'trigger_123abc'. "
                "Examples of BAD keys: 'trigger_response_123abc', 'user_preference_color_value', 'bnm123_response'. "
                "The value holds the full information, including any instructions or context."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short 1-3 word key, e.g. 'wake_time' or 'trigger_abc'. No long sentences."},
                    "value": {"type": "string", "description": "The information or instruction to remember in full."},
                },
                "required": ["key", "value"],
            },
        ),
        Tool(
            name="memory_get",
            description=(
                "Recall a remembered piece of information. "
                "If you are not sure of the exact key, leave key empty to list ALL memories, "
                "or use memory_search to find by partial keyword. "
                "Always call memory_get with no key first if unsure what keys exist."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Exact key to look up. Leave empty to list all memories."},
                },
                "required": [],
            },
        ),
        Tool(
            name="memory_search",
            description=(
                "Search memories by a partial keyword. Searches both keys and values. "
                "Use this when you are not sure of the exact key name."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Partial word to search for in keys or values, e.g. 'trigger' or 'wake'"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="memory_delete",
            description="Forget a remembered piece of information by key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Exact key to delete"},
                },
                "required": ["key"],
            },
        ),
    ]


# ─────────────────────────────────────────────
# Tool handlers
# ─────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict):

    # ── get_time ─────────────────────────────
    if name == "get_time":
        now = datetime.datetime.now()
        return [TextContent(type="text", text=now.strftime("🕐 %A, %d %B %Y  —  %H:%M:%S"))]

    # ── get_weather ───────────────────────────
    elif name == "get_weather":
        city = arguments["city"]
        units = arguments.get("units", "metric")
        unit_sym = "°C" if units == "metric" else "°F"

        if not OPEN_WEATHER_API_KEY:
            return [TextContent(type="text", text=(
                f"⚠️  No OPENWEATHER_API_KEY set.\n"
                f"Sign up free at https://openweathermap.org/api\n"
                f"Then set OPENWEATHER_API_KEY in Prepare.bat config."
            ))]

        encoded_city = urllib.parse.quote(city)
        url = (f"https://api.openweathermap.org/data/2.5/weather"
               f"?q={encoded_city}&units={units}&appid={OPEN_WEATHER_API_KEY}")
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Weather fetch failed: {e}")]

        desc = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]
        wind_unit = "m/s" if units == "metric" else "mph"
        icon_map = {"clear": "☀️", "cloud": "☁️", "rain": "🌧️", "thunder": "⛈️",
                    "snow": "❄️", "mist": "🌫️", "haze": "🌫️", "drizzle": "🌦️"}
        icon = next((v for k, v in icon_map.items() if k in desc.lower()), "🌡️")
        return [TextContent(type="text", text=(
            f"{icon} {city} — {desc}\n"
            f"🌡️  {temp}{unit_sym} (feels like {feels}{unit_sym})\n"
            f"💧 Humidity: {humidity}%   💨 Wind: {wind} {wind_unit}"
        ))]

    # ── open_browser ──────────────────────────
    elif name == "open_browser":
        query = arguments["query"].strip()
        if is_duplicate_action(("open_browser", query.lower())):
            return [TextContent(type="text", text="Ignored duplicate browser request.")]
        url = query if query.startswith("http") else f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.Popen(["open", url])
            elif system == "Windows":
                os.startfile(url)
            else:
                subprocess.Popen(["xdg-open", url])
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Could not open browser: {e}")]
        return [TextContent(type="text", text=f"🌐 Opened: {url}")]

    # ── play_music ────────────────────────────
    elif name == "play_music":
        filename = arguments["filename"].lower()
        if is_duplicate_action(("play_music", filename)):
            return [TextContent(type="text", text="Ignored duplicate play request.")]
        found = None
        audio_exts = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".opus"}
        for music_dir in SAFE_MUSIC_DIRS:
            if not music_dir.exists():
                continue
            for f in music_dir.rglob("*"):
                if f.suffix.lower() in audio_exts and filename in f.name.lower():
                    found = f
                    break
            if found:
                break
        if not found:
            return [TextContent(type="text", text=f"🎵 No audio file matching '{filename}' found in Music, Downloads, or Desktop.")]
        try:
            if platform.system() == "Darwin":
                subprocess.Popen(["open", str(found)])
            elif platform.system() == "Windows":
                os.startfile(str(found))
            else:
                subprocess.Popen(["xdg-open", str(found)])
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Could not play: {e}")]
        return [TextContent(type="text", text=f"🎵 Now playing: {found.name}\n📂 {found}")]

    # ── list_folder ───────────────────────────
    elif name == "list_folder":
        raw_path = arguments["path"]
        depth = min(max(int(arguments.get("depth", 1)), 1), 3)
        expanded = os.path.expanduser(raw_path)
        if not is_safe_path(expanded):
            return [TextContent(type="text", text=f"🚫 Access denied: '{raw_path}' is a protected system directory.")]
        target = Path(expanded)
        if not target.exists():
            return [TextContent(type="text", text=f"❌ Path does not exist: {expanded}")]
        if not target.is_dir():
            return [TextContent(type="text", text=f"❌ Not a directory: {expanded}")]
        lines = [f"📁 {target}"]
        def walk(path, indent, current_depth):
            if current_depth > depth:
                return
            try:
                entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            except PermissionError:
                lines.append("  " * indent + "🔒 (permission denied)")
                return
            for entry in entries:
                icon = "📄" if entry.is_file() else "📂"
                lines.append("  " * indent + f"{icon} {entry.name}")
                if entry.is_dir():
                    walk(entry, indent + 1, current_depth + 1)
        walk(target, 1, 1)
        return [TextContent(type="text", text="\n".join(lines))]

    # ── set_alarm ─────────────────────────────
    elif name == "set_alarm":
        time_str = arguments["time"]
        label = arguments.get("label", "⏰ Alarm!")
        if is_duplicate_action(("set_alarm", time_str, label)):
            return [TextContent(type="text", text="Ignored duplicate alarm request.")]
        try:
            alarm_time = datetime.datetime.strptime(time_str, "%H:%M").replace(
                year=datetime.datetime.now().year,
                month=datetime.datetime.now().month,
                day=datetime.datetime.now().day,
            )
            if alarm_time < datetime.datetime.now():
                alarm_time += datetime.timedelta(days=1)
        except ValueError:
            return [TextContent(type="text", text="❌ Invalid time format. Use HH:MM, e.g. '07:30'")]

        delay = (alarm_time - datetime.datetime.now()).total_seconds()

        def fire_alarm():
            asyncio.run(_show_popup(f"⏰ ALARM\n{label}"))

        timer = threading.Timer(delay, fire_alarm)
        timer.daemon = True
        timer.start()

        return [TextContent(type="text", text=(
            f"⏰ Alarm set for {alarm_time.strftime('%H:%M')} — {label}\n"
            f"That's in {int(delay // 60)} min {int(delay % 60)} sec."
        ))]

    # ── set_reminder ──────────────────────────
    elif name == "set_reminder":
        dt_str = arguments["datetime_str"]
        message = arguments["message"]
        if is_duplicate_action(("set_reminder", dt_str, message)):
            return [TextContent(type="text", text="Ignored duplicate reminder request.")]
        try:
            remind_at = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return [TextContent(type="text", text="❌ Invalid format. Use 'YYYY-MM-DD HH:MM', e.g. '2026-07-01 09:00'")]

        delay = (remind_at - datetime.datetime.now()).total_seconds()
        if delay < 0:
            return [TextContent(type="text", text="❌ That time is in the past!")]

        def fire_reminder():
            asyncio.run(_show_popup(f"🔔 REMINDER\n{message}"))

        timer = threading.Timer(delay, fire_reminder)
        timer.daemon = True
        timer.start()

        return [TextContent(type="text", text=(
            f"🔔 Reminder set for {remind_at.strftime('%A, %d %B %Y at %H:%M')}\n"
            f"Message: {message}\n"
            f"That's in {int(delay // 3600)}h {int((delay % 3600) // 60)}m."
        ))]

    # ── schedule_shutdown ─────────────────────
    elif name == "schedule_shutdown":
        cancel = arguments.get("cancel", False)
        system = platform.system()

        if cancel:
            try:
                if system == "Windows":
                    subprocess.run(["shutdown", "/a"], check=True)
                else:
                    subprocess.run(["shutdown", "-c"], check=True)
                return [TextContent(type="text", text="✅ Scheduled shutdown has been cancelled.")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Could not cancel shutdown: {e}")]

        mode = arguments.get("mode")
        value = arguments.get("value", "")

        if mode == "after_minutes":
            try:
                minutes = int(value)
            except ValueError:
                return [TextContent(type="text", text="❌ Please provide the number of minutes as a number, e.g. '30'")]
            seconds = minutes * 60
            try:
                if system == "Windows":
                    subprocess.run(["shutdown", "/s", "/t", str(seconds)], check=True)
                else:
                    subprocess.run(["sudo", "shutdown", "-h", f"+{minutes}"], check=True)
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Could not schedule shutdown: {e}")]
            return [TextContent(type="text", text=f"💤 PC will shut down in {minutes} minute(s). Say 'cancel shutdown' to undo.")]

        elif mode == "at_time":
            try:
                target = datetime.datetime.strptime(value, "%H:%M").replace(
                    year=datetime.datetime.now().year,
                    month=datetime.datetime.now().month,
                    day=datetime.datetime.now().day,
                )
                if target < datetime.datetime.now():
                    target += datetime.timedelta(days=1)
            except ValueError:
                return [TextContent(type="text", text="❌ Invalid time. Use HH:MM, e.g. '23:00'")]
            seconds = int((target - datetime.datetime.now()).total_seconds())
            try:
                if system == "Windows":
                    subprocess.run(["shutdown", "/s", "/t", str(seconds)], check=True)
                else:
                    subprocess.run(["sudo", "shutdown", "-h", f"+{seconds // 60}"], check=True)
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Could not schedule shutdown: {e}")]
            return [TextContent(type="text", text=f"💤 PC will shut down at {target.strftime('%H:%M')}. Say 'cancel shutdown' to undo.")]

        return [TextContent(type="text", text="❌ Invalid mode. Use 'at_time' or 'after_minutes'.")]

    # ── find_file ─────────────────────────────
    elif name == "find_file":
        filename = arguments["filename"].lower()
        search_root = Path(os.path.expanduser(arguments.get("search_in", "~")))

        if not is_safe_path(str(search_root)):
            return [TextContent(type="text", text="🚫 Access denied: that directory is protected.")]

        matches = []
        try:
            for f in search_root.rglob("*"):
                if filename in f.name.lower():
                    try:
                        size = f.stat().st_size if f.is_file() else 0
                        matches.append((f, size))
                    except (PermissionError, OSError):
                        pass
                if len(matches) >= 20:
                    break
        except (PermissionError, OSError):
            pass

        if not matches:
            return [TextContent(type="text", text=f"🔍 No files matching '{filename}' found in {search_root}")]

        lines = [f"🔍 Found {len(matches)} result(s) for '{filename}':"]
        for f, size in matches:
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            icon = "📄" if f.is_file() else "📂"
            lines.append(f"  {icon} {f}  ({size_str})" if f.is_file() else f"  {icon} {f}")
        return [TextContent(type="text", text="\n".join(lines))]

    # ── find_largest_files ────────────────────
    elif name == "find_largest_files":
        search_root = Path(os.path.expanduser(arguments.get("search_in", "~")))

        if not is_safe_path(str(search_root)):
            return [TextContent(type="text", text="🚫 Access denied: that directory is protected.")]

        files = []
        try:
            for f in search_root.rglob("*"):
                if f.is_file():
                    try:
                        files.append((f, f.stat().st_size))
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass

        if not files:
            return [TextContent(type="text", text=f"No files found in {search_root}")]

        top5 = sorted(files, key=lambda x: x[1], reverse=True)[:5]
        lines = [f"📊 Top 5 largest files in {search_root}:\n"]
        for i, (f, size) in enumerate(top5, 1):
            if size >= 1024 ** 3:
                size_str = f"{size / 1024 ** 3:.2f} GB"
            elif size >= 1024 ** 2:
                size_str = f"{size / 1024 ** 2:.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"
            lines.append(f"  {i}. {size_str:>10}  {f}")
        lines.append("\n⚠️  This is read-only info. Nothing has been deleted.")
        return [TextContent(type="text", text="\n".join(lines))]

    # ── create_file ───────────────────────────
    elif name == "create_file":
        raw_path = arguments["path"]
        content = arguments.get("content", "")
        confirmed = arguments.get("confirmed", False)
        if confirmed and is_duplicate_action(("create_file", os.path.expanduser(raw_path))):
            return [TextContent(type="text", text="Ignored duplicate file creation request.")]

        expanded = os.path.expanduser(raw_path)
        target = Path(expanded)

        if not is_safe_path(expanded):
            return [TextContent(type="text", text="🚫 Access denied: that location is protected.")]

        if not confirmed:
            return [TextContent(type="text", text=(
                f"📋 Ready to create:\n"
                f"  Path: {target}\n"
                f"  Content: {content[:100] + '...' if len(content) > 100 else content or '(empty file)'}\n\n"
                f"Please confirm by calling this tool again with confirmed=true."
            ))]

        if target.exists():
            return [TextContent(type="text", text=f"❌ File already exists: {target}")]

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Could not create file: {e}")]

        return [TextContent(type="text", text=f"✅ File created: {target}")]

    # ── memory_set ────────────────────────────
    elif name == "memory_set":
        key = arguments["key"].strip().lower().replace(" ", "_")
        value = arguments["value"]
        mem = load_memory()
        mem[key] = {"value": value, "updated": datetime.datetime.now().isoformat()}
        save_memory(mem)
        return [TextContent(type="text", text=f"🧠 Remembered: '{key}' = '{value}'")]

    # ── memory_get ────────────────────────────
    elif name == "memory_get":
        key = arguments.get("key", "").strip().lower().replace(" ", "_")
        mem = load_memory()

        if not key:
            if not mem:
                return [TextContent(type="text", text="🧠 No memories stored yet.")]
            lines = ["🧠 All memories:"]
            for k, v in mem.items():
                lines.append(f"  • {k}: {v['value']}")
            return [TextContent(type="text", text="\n".join(lines))]

        # Exact match
        if key in mem:
            entry = mem[key]
            return [TextContent(type="text", text=(
                f"🧠 {key}: {entry['value']}\n"
                f"   (saved: {entry['updated'][:16]})"
            ))]

        # Fuzzy fallback — find keys that contain the query or vice versa
        fuzzy = [(k, v) for k, v in mem.items() if key in k or k in key]
        if fuzzy:
            lines = [f"🧠 No exact match for '{key}', but found similar:"]
            for k, v in fuzzy:
                lines.append(f"  • {k}: {v['value']}")
            return [TextContent(type="text", text="\n".join(lines))]

        return [TextContent(type="text", text=f"🧠 No memory found for '{key}'. Call memory_get with no key to list everything.")]

    # ── memory_search ─────────────────────────
    elif name == "memory_search":
        query = arguments["query"].strip().lower()
        mem = load_memory()
        if not mem:
            return [TextContent(type="text", text="🧠 No memories stored yet.")]

        matches = [(k, v) for k, v in mem.items()
                   if query in k or query in v["value"].lower()]

        if not matches:
            return [TextContent(type="text", text=f"🧠 No memories matching '{query}'.")]

        lines = [f"🧠 Memories matching '{query}':"]
        for k, v in matches:
            lines.append(f"  • {k}: {v['value']}")
        return [TextContent(type="text", text="\n".join(lines))]

    # ── memory_delete ─────────────────────────
    elif name == "memory_delete":
        key = arguments["key"].strip().lower().replace(" ", "_")
        mem = load_memory()
        if key not in mem:
            # Try fuzzy match to help
            fuzzy = [k for k in mem if key in k or k in key]
            if fuzzy:
                return [TextContent(type="text", text=(
                    f"🧠 No exact key '{key}'. Did you mean one of these?\n" +
                    "\n".join(f"  • {k}" for k in fuzzy)
                ))]
            return [TextContent(type="text", text=f"🧠 No memory found for '{key}'.")]
        del mem[key]
        save_memory(mem)
        return [TextContent(type="text", text=f"🧠 Forgot: '{key}'")]

    else:
        return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]


# ─────────────────────────────────────────────
# Popup helper (alarm / reminder)
# ─────────────────────────────────────────────

async def _show_popup(message: str):
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen([
                "powershell", "-Command",
                f"Add-Type -AssemblyName PresentationFramework; "
                f"[System.Windows.MessageBox]::Show('{message}', 'Pet AI', 'OK', 'Information')"
            ])
        elif system == "Darwin":
            subprocess.Popen(["osascript", "-e", f'display dialog "{message}" buttons {{"OK"}}'])
        else:
            subprocess.Popen(["notify-send", "Pet AI", message])
    except Exception:
        pass


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
