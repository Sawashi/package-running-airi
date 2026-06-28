# 🐾 Pet AI MCP Server — Windows Setup

No technical skills needed. Just follow these 3 steps!

---

## ✅ What's in this folder

| File | What it does |
|---|---|
| `START_SERVER.bat` | Starts the Pet AI server (keep open while using Claude) |
| `SETUP_CLAUDE.bat` | Connects Pet AI to Claude Desktop automatically |
| `server.py` | The actual server code (you don't need to touch this) |

---

## 🚀 3 steps to get started

### Step 1 — Run the setup (one time only)
Double-click **`SETUP_CLAUDE.bat`**

This automatically connects Pet AI to Claude Desktop. No editing files!

### Step 2 — Start the server (every time you want to use it)
Double-click **`START_SERVER.bat`**

- If Python is not installed, it will download and install it for you automatically
- A black window will appear — **keep it open** while you use Claude
- To stop the server, just close that window

### Step 3 — Use it in Claude Desktop
- Fully quit and reopen Claude Desktop
- Start a new chat
- You will see a small tools icon near the message box — click it to see your Pet AI tools!

---

## 🌤️ Weather setup (optional)

To get real weather forecasts:
1. Go to https://openweathermap.org/api and sign up free
2. Copy your API key
3. Open START_SERVER.bat in Notepad, find the line that says:
      set OPENWEATHER_API_KEY=
   and paste your key after the equals sign
4. Save and restart the server

---

## ❓ Common issues

The black window closes immediately?
  → Right-click START_SERVER.bat and choose "Run as administrator"

Tools not showing in Claude?
  → Make sure you fully quit Claude Desktop (right-click taskbar icon → Quit) and reopen it

Python installed but still not found?
  → Restart your computer once, then double-click START_SERVER.bat again
