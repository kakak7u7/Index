# Telegram Class Indexer

A Telegram bot + Telethon indexer for organizing an **existing Telegram channel history** into topic-wise class links.

## What it does

- Scans existing channel messages with Telethon/MTProto.
- Extracts title/caption, Part number, date, media type and Telegram message ID.
- Groups similar titles into one topic.
- Sorts Parts numerically, then by date.
- Stores everything in SQLite.
- Provides a Telegram Bot UI:
  - Search Class
  - All Topics
  - Topic → Parts → direct Telegram link
  - Statistics
  - Rescan/Update Index (admin)
- Supports duplicate detection.
- Does **not** download class videos/PDFs.

## Important architecture note

The Bot API alone is not enough for reliably scanning a channel's old history. This project uses a **Telethon user session** for the historical scan. The Telegram bot is only the user-facing interface. Your user account must have access to the channel.

Telethon's `iter_messages()` supports iterating a chat's message history and can retrieve the whole history with `limit=None`. See the official docs:
https://docs.telethon.dev/en/stable/modules/client.html

## Setup

### 1. Create a Bot

Create a bot with `@BotFather` and copy its token.

### 2. Configure `.env`

The project includes `.env` with the API ID/hash you supplied. Fill in:

- `BOT_TOKEN`
- `CHANNEL`
- `ADMIN_IDS`

`CHANNEL` can be a public username such as `@mychannel`, or a numeric channel ID.

### 3. Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Termux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. First run

```bash
python main.py
```

On the first run, Telethon may ask for your phone number and Telegram login code. If 2FA is enabled, it will ask for the password. A local `user_session.session` file will then be created.

**Never upload or share that session file.**

### 5. Scan the existing channel

Send `/scan` to your bot from an ID listed in `ADMIN_IDS`.

The bot will scan the existing history and build the index.

### 6. Use the bot

- `/start`
- `/topics`
- `/search`
- `/stats`
- `/scan` (admin only)
- `/update` (admin only)

## Topic grouping

The parser removes common structural parts such as:

- `Part-1`, `Part 1`, `Part-01`
- dates such as `29-March`, `29 March`, `01-April`
- common metadata like `Question PDF` where appropriate

It then normalizes spacing/case and groups identical normalized topic names.

Because human-written titles can vary (for example `सामान्य पशुपालन` vs `सामान्य पशु पालन`), the bot includes a conservative normalization layer. It intentionally avoids aggressive fuzzy merging because that can incorrectly combine unrelated classes.

## Security

Do not publish `.env` or `user_session.session`.

If an API credential is ever exposed publicly, regenerate/rotate it from Telegram's developer settings.

## Files

- `main.py` — bot + scanner
- `config.py` — environment configuration
- `database.py` — SQLite schema and queries
- `parser.py` — title/part/date/topic parsing
- `ui.py` — Telegram inline keyboard UI
- `.env` — local configuration
- `.gitignore` — prevents secrets/session/database from being committed
- `requirements.txt` — dependencies
