import asyncio
import logging
import os
import re

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

import config
import database
from parser import (
    extract_part, extract_date, topic_from_title,
    message_type, content_hash
)
from ui import main_menu, topics_keyboard, topic_keyboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("class-indexer")

telethon_client = None
scan_lock = asyncio.Lock()

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

def telegram_message_link(entity, message_id):
    # Public channel
    username = getattr(entity, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"

    # Private channel direct link format.
    # Telegram uses the channel's internal numeric ID without -100.
    cid = getattr(entity, "id", None)
    if cid is None:
        raise RuntimeError("Cannot determine channel ID")
    return f"https://t.me/c/{cid}/{message_id}"

async def get_channel():
    return await telethon_client.get_entity(config.CHANNEL)

async def scan_history(progress_callback=None, full=True):
    global telethon_client

    async with scan_lock:
        entity = await get_channel()
        channel_key = str(getattr(entity, "id", config.CHANNEL))
        total = 0
        saved = 0

        log.info("Scanning channel: %s", getattr(entity, "title", entity))

        # reverse=True scans oldest -> newest.
        async for message in telethon_client.iter_messages(
            entity, limit=None if full else 3000, reverse=True, wait_time=1
        ):
            total += 1
            raw = message.raw_text or ""
            if not raw and not (message.video or message.document or message.photo):
                continue

            title = raw.splitlines()[0].strip() if raw else "Untitled"
            # Prefer the full caption if first line is only a generic media label.
            if len(title) < 3 and raw.strip():
                title = raw.strip()

            part = extract_part(raw)
            date_text = extract_date(raw, message.date)
            topic = topic_from_title(raw)

            link = telegram_message_link(entity, message.id)
            row = (
                message.id,
                channel_key,
                title,
                topic,
                part,
                date_text,
                message_type(message),
                link,
                content_hash(title, message.id),
            )
            database.upsert_message(config.DB_PATH, row)
            saved += 1

            if progress_callback and saved % 100 == 0:
                await progress_callback(saved, total)

        return total, saved

async def ensure_telethon():
    global telethon_client
    if telethon_client is None:
        telethon_client = TelegramClient(
            config.SESSION_NAME,
            config.API_ID,
            config.API_HASH
        )
        await telethon_client.start()
        log.info("Telethon connected.")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 CLASS LIBRARY\n\n"
        "आपके existing Telegram channel की classes को topic-wise खोजें।\n\n"
        "🔎 Search Class — keyword से खोजें\n"
        "📚 All Topics — सभी topics देखें\n"
        "📊 Statistics — index की जानकारी",
        reply_markup=main_menu()
    )

async def cmd_topics(update, context):
    await update.message.reply_text(
        "📚 ALL TOPICS",
        reply_markup=topics_keyboard(config.DB_PATH, 0, config.PAGE_SIZE)
    )

async def cmd_stats(update, context):
    s = database.stats(config.DB_PATH)
    await update.message.reply_text(
        "📊 STATISTICS\n\n"
        f"📚 Topics: {s['topics']}\n"
        f"🎬 Classes: {s['classes']}\n"
        f"🎞 Videos: {s['videos']}\n"
        f"📄 PDFs/Documents: {s['pdfs']}"
    )

async def cmd_search(update, context):
    if not context.args:
        await update.message.reply_text(
            "🔎 Usage:\n/search पशुपालन\n/search अरावली"
        )
        return
    q = " ".join(context.args)
    rows = database.search(config.DB_PATH, q)
    if not rows:
        await update.message.reply_text(f"❌ '{q}' नहीं मिला।")
        return

    lines = [f"🔎 SEARCH: {q}\n"]
    buttons = []
    for r in rows[:20]:
        label = r["title"][:55]
        buttons.append([InlineKeyboardButton(label, url=r["telegram_link"])])
    await update.message.reply_text(
        "\n".join(lines) + f"\n{len(rows)} result(s) मिले।",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def cmd_scan(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    await update.message.reply_text(
        "🔄 Full scan शुरू हो रहा है।\n"
        "Existing channel history पढ़ी जाएगी; classes download नहीं होंगी."
    )

    async def progress(saved, total):
        # Keep logging; avoid flooding the bot with messages.
        log.info("Scan progress: saved=%s scanned=%s", saved, total)

    try:
        total, saved = await scan_history(progress, full=True)
        s = database.stats(config.DB_PATH)
        await update.message.reply_text(
            "✅ SCAN COMPLETED\n\n"
            f"Messages scanned: {total}\n"
            f"Indexed messages: {saved}\n"
            f"Topics: {s['topics']}\n"
            f"Classes: {s['classes']}"
        )
    except FloodWaitError as e:
        await update.message.reply_text(
            f"⏳ Telegram ने rate limit लगाया है। {e.seconds} seconds बाद फिर चलाएँ."
        )
    except Exception as e:
        log.exception("Scan failed")
        await update.message.reply_text(f"❌ Scan failed: {e}")

async def cmd_update(update, context):
    # Safe default: incremental scan currently re-upserts the history.
    # It is intentionally admin-only.
    await cmd_scan(update, context)

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    if data == "home":
        await q.edit_message_text(
            "📚 CLASS LIBRARY",
            reply_markup=main_menu()
        )
        return

    if data == "stats":
        s = database.stats(config.DB_PATH)
        await q.edit_message_text(
            "📊 STATISTICS\n\n"
            f"📚 Topics: {s['topics']}\n"
            f"🎬 Classes: {s['classes']}\n"
            f"🎞 Videos: {s['videos']}\n"
            f"📄 PDFs/Documents: {s['pdfs']}",
            reply_markup=main_menu()
        )
        return

    if data.startswith("topics:"):
        page = int(data.split(":", 1)[1])
        await q.edit_message_text(
            f"📚 ALL TOPICS — Page {page+1}",
            reply_markup=topics_keyboard(
                config.DB_PATH, page, config.PAGE_SIZE
            )
        )
        return

    if data.startswith("topic:"):
        topic = data.split(":", 1)[1]
        rows = database.get_topic_messages(config.DB_PATH, topic)
        if not rows:
            await q.edit_message_text(
                "❌ Topic नहीं मिला।",
                reply_markup=topics_keyboard(config.DB_PATH, 0, config.PAGE_SIZE)
            )
            return
        await q.edit_message_text(
            f"📚 {rows[0]['topic_key']}\n\n"
            f"Total Classes: {len(rows)}",
            reply_markup=topic_keyboard(rows)
        )
        return

    if data == "search":
        await q.edit_message_text(
            "🔎 Search के लिए command इस्तेमाल करें:\n\n"
            "/search पशुपालन\n"
            "/search अरावली\n"
            "/search जलवायु",
            reply_markup=main_menu()
        )
        return

    if data == "update":
        if not is_admin(update.effective_user.id):
            await q.answer("Admin only.", show_alert=True)
            return
        await q.edit_message_text(
            "🔄 Update के लिए /update command चलाएँ।"
        )

async def error_handler(update, context):
    log.exception("Unhandled bot error", exc_info=context.error)

async def run():
    config.validate()
    await ensure_telethon()

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("update", cmd_update))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_error_handler(error_handler)

    log.info("Bot starting.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        if telethon_client:
            await telethon_client.disconnect()

if __name__ == "__main__":
    asyncio.run(run())
