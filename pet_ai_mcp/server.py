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
import urllib.parse
import urllib.request
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

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

app = Server("pet-ai")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def is_safe_path(path_str: str) -> bool:
    """Return True only if path is not inside a blocked directory."""
    try:
        p = Path(path_str).resolve()
    except Exception:
        return False
    for blocked in BLOCKED_PATHS:
        try:
            p.relative_to(Path(blocked).resolve())
            return False  # inside a blocked dir
        except ValueError:
            pass
    return True


def _run(cmd: list[str], timeout: int = 10) -> str:
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip() or result.stderr.strip()


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
            description=(
                "Fetch current weather for a city. "
                "Requires OPENWEATHER_API_KEY env var, or returns a demo stub."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. 'Ho Chi Minh City'"},
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Temperature units (metric = °C, imperial = °F). Default: metric.",
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="open_browser",
            description="Open a URL or perform a web search in the default browser.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A full URL (https://...) or a plain search query.",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="play_music",
            description=(
                "Play a music file by name from your Music, Downloads, or Desktop folder. "
                "Pass a partial filename; the tool finds the first match."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Partial or full filename to search for (e.g. 'lofi', 'bohemian')",
                    }
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="list_folder",
            description=(
                "List the contents (files and subdirectories) of a folder on your computer. "
                "Safe paths only — system directories are blocked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or ~ path to a folder. E.g. '~/Documents'",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "How many levels deep to list (1–3). Default: 1.",
                        "minimum": 1,
                        "maximum": 3,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="capture_screen",
            description=(
                "Take a screenshot of the current screen and return it as an image "
                "so you can describe or analyse what is on screen."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
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
        text = now.strftime("🕐 %A, %d %B %Y  —  %H:%M:%S (%Z)")
        return [TextContent(type="text", text=text)]

    # ── get_weather ───────────────────────────
    elif name == "get_weather":
        city = arguments["city"]
        units = arguments.get("units", "metric")
        unit_sym = "°C" if units == "metric" else "°F"

        if not OPEN_WEATHER_API_KEY:
            return [TextContent(
                type="text",
                text=(
                    f"⚠️  No OPENWEATHER_API_KEY set.\n\n"
                    f"To get real weather for **{city}**:\n"
                    f"1. Sign up free at https://openweathermap.org/api\n"
                    f"2. Set the env var: export OPENWEATHER_API_KEY=your_key\n"
                    f"3. Restart the MCP server."
                ),
            )]

        encoded_city = urllib.parse.quote(city)
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={encoded_city}&units={units}&appid={OPEN_WEATHER_API_KEY}"
        )
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
        icon_map = {
            "clear": "☀️", "cloud": "☁️", "rain": "🌧️",
            "thunder": "⛈️", "snow": "❄️", "mist": "🌫️",
            "haze": "🌫️", "drizzle": "🌦️",
        }
        icon = next(
            (v for k, v in icon_map.items() if k in desc.lower()), "🌡️"
        )
        text = (
            f"{icon} **{city}** — {desc}\n"
            f"🌡️  Temp: {temp}{unit_sym}  (feels like {feels}{unit_sym})\n"
            f"💧 Humidity: {humidity}%\n"
            f"💨 Wind: {wind} {wind_unit}"
        )
        return [TextContent(type="text", text=text)]

    # ── open_browser ──────────────────────────
    elif name == "open_browser":
        query = arguments["query"].strip()
        if query.startswith("http://") or query.startswith("https://"):
            url = query
        else:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded}"

        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.Popen(["open", url])
            elif system == "Windows":
                os.startfile(url)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", url])
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Could not open browser: {e}")]

        return [TextContent(type="text", text=f"🌐 Opened in browser:\n{url}")]

    # ── play_music ────────────────────────────
    elif name == "play_music":
        filename = arguments["filename"].lower()
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
            searched = ", ".join(str(d) for d in SAFE_MUSIC_DIRS)
            return [TextContent(
                type="text",
                text=(
                    f"🎵 No audio file matching **'{filename}'** found.\n"
                    f"Searched in: {searched}"
                ),
            )]

        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.Popen(["open", str(found)])
            elif system == "Windows":
                os.startfile(str(found))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(found)])
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Could not play file: {e}")]

        return [TextContent(type="text", text=f"🎵 Now playing: **{found.name}**\n📂 {found}")]

    # ── list_folder ───────────────────────────
    elif name == "list_folder":
        raw_path = arguments["path"]
        depth = min(max(int(arguments.get("depth", 1)), 1), 3)

        expanded = os.path.expanduser(raw_path)
        if not is_safe_path(expanded):
            return [TextContent(
                type="text",
                text=f"🚫 Access denied: '{raw_path}' is in a protected system directory.",
            )]

        target = Path(expanded)
        if not target.exists():
            return [TextContent(type="text", text=f"❌ Path does not exist: {expanded}")]
        if not target.is_dir():
            return [TextContent(type="text", text=f"❌ Not a directory: {expanded}")]

        lines = [f"📁 {target}"]

        def walk(path: Path, indent: int, current_depth: int):
            if current_depth > depth:
                return
            try:
                entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            except PermissionError:
                lines.append("  " * indent + "🔒 (permission denied)")
                return
            for entry in entries:
                prefix = "  " * indent
                icon = "📄" if entry.is_file() else "📂"
                lines.append(f"{prefix}{icon} {entry.name}")
                if entry.is_dir():
                    walk(entry, indent + 1, current_depth + 1)

        walk(target, 1, 1)
        return [TextContent(type="text", text="\n".join(lines))]

    # ── capture_screen ────────────────────────
    elif name == "capture_screen":
        system = platform.system()
        tmp_path = Path("/tmp/pet_ai_screenshot.png")

        try:
            if system == "Darwin":
                subprocess.run(["screencapture", "-x", str(tmp_path)], check=True, timeout=10)
            elif system == "Windows":
                # Use PowerShell Add-Type to capture
                ps_script = (
                    "Add-Type -AssemblyName System.Windows.Forms;"
                    "$bmp = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
                    "$bitmap = New-Object System.Drawing.Bitmap($bmp.Width, $bmp.Height);"
                    "$graphics = [System.Drawing.Graphics]::FromImage($bitmap);"
                    "$graphics.CopyFromScreen($bmp.Location, [System.Drawing.Point]::Empty, $bmp.Size);"
                    f"$bitmap.Save('{tmp_path}');"
                )
                subprocess.run(
                    ["powershell", "-Command", ps_script], check=True, timeout=15
                )
            else:
                # Linux — try scrot, then gnome-screenshot, then import (ImageMagick)
                for cmd in [
                    ["scrot", str(tmp_path)],
                    ["gnome-screenshot", "-f", str(tmp_path)],
                    ["import", "-window", "root", str(tmp_path)],
                ]:
                    try:
                        subprocess.run(cmd, check=True, timeout=10)
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                else:
                    raise RuntimeError(
                        "No screenshot tool found. Install scrot: sudo apt install scrot"
                    )
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Screenshot failed: {e}")]

        if not tmp_path.exists():
            return [TextContent(type="text", text="❌ Screenshot file was not created.")]

        img_bytes = tmp_path.read_bytes()
        b64 = base64.b64encode(img_bytes).decode()
        tmp_path.unlink(missing_ok=True)  # clean up

        return [
            TextContent(type="text", text="📸 Screenshot captured! Here's what I see:"),
            ImageContent(type="image", data=b64, mimeType="image/png"),
        ]

    else:
        return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
