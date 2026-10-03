from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Search Class", callback_data="search")],
        [InlineKeyboardButton("📚 All Topics", callback_data="topics:0")],
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
        [InlineKeyboardButton("🔄 Update Index", callback_data="update")],
    ])

def topics_keyboard(path, page, page_size):
    rows = database.get_topics(path, page * page_size, page_size)
    buttons = []
    for r in rows:
        buttons.append([
            InlineKeyboardButton(
                f"📚 {r['display_title']}  ({r['total']})",
                callback_data="topic:" + r["topic_key"][:55]
            )
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Previous", callback_data=f"topics:{page-1}"))
    if len(rows) == page_size:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"topics:{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
    return InlineKeyboardMarkup(buttons)

def topic_keyboard(rows):
    buttons = []
    for r in rows:
        label = f"▶️ Part-{r['part_number']}" if r["part_number"] else "▶️ Open"
        date = r["message_date"] or ""
        if date:
            label += f" — {date}"
        buttons.append([
            InlineKeyboardButton(label, url=r["telegram_link"])
        ])
    buttons.append([InlineKeyboardButton("◀️ Topics", callback_data="topics:0")])
    return InlineKeyboardMarkup(buttons)
