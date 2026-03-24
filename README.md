# Jarvis — Personal AI Agent 🤖

A fully custom personal AI assistant built from scratch with Python and Claude API.
Inspired by Jarvis from Iron Man — runs 24/7, remembers everything, and works on your phone.

## Features

- Natural conversation powered by Claude AI (Anthropic)
- Persistent memory — remembers you across every conversation
- Daily job search briefings at 7 AM automatically
- Searches Calgary, Edmonton and Remote jobs
- Telegram interface — works on phone and desktop
- Smart deduplication — never shows the same job twice
- On-demand job search with /jobs command

## Tech Stack

| Layer | Technology |
|-------|------------|
| AI Brain | Claude API (Anthropic) |
| Memory | ChromaDB (vector database) |
| Interface | Python Telegram Bot |
| Job Search | Adzuna API |
| Language | Python 3.10+ |
| Storage | JSON + ChromaDB |

## Project Structure

jarvis/
├── jarvis.py          # Core AI agent + Claude API integration
├── memory.py          # Two-layer memory system (ChromaDB + JSON)
├── telegram_bot.py    # Telegram interface + command handlers
├── job_search.py      # Job search + daily briefing scheduler
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variables template
└── .gitignore         # Keeps secrets out of GitHub

## Setup

### 1 — Clone the repo

git clone https://github.com/danishk1999/Jarvis.git
cd Jarvis

### 2 — Create virtual environment

python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

### 3 — Set up environment variables

Copy .env.example to .env and fill in your keys:

ANTHROPIC_API_KEY=your_claude_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key

### 4 — Run Jarvis

python telegram_bot.py

### 5 — Talk to Jarvis on Telegram

Find your bot and send /start

## Telegram Commands

| Command | Description |
|---------|-------------|
| /start | Introduction and command list |
| /jobs | Search IT jobs instantly |
| /profile | See what Jarvis knows about you |
| /clear | Clear conversation history |

## Memory System

Jarvis uses a two-layer memory architecture:

- Short term — Last 20 conversation turns sent to Claude on every message
- Long term — ChromaDB vector database stores all messages, searched by semantic similarity
- User profile — Key facts auto-extracted from conversations and persisted as JSON

## Job Search

Jarvis searches for these roles daily across Calgary, Edmonton and Remote Canada:

- Network Engineer
- IT Support / Help Desk
- Cybersecurity Analyst
- System Administrator
- Network Administrator
- Junior IT / IT Intern

Searches run automatically at 7 AM every day and results are sent directly to Telegram.
Only new jobs are shown — Jarvis remembers which jobs it has already sent you.

## Roadmap

- [x] Core AI agent with memory
- [x] Telegram interface — phone and desktop
- [x] Automated daily job search
- [ ] Voice interface — wake word and speech
- [ ] Certification expiry tracker
- [ ] Web UI dashboard
- [ ] DIY AI glasses hardware build

## Author

Danish — Network Engineer based in Edmonton, Alberta
Certifications: Cisco CCNA | AWS Cloud Practitioner | CompTIA A+ | Fortinet NSE 1 and 2
GitHub: https://github.com/danishk1999

## License

MIT License — free to use and modify
