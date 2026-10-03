import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    channel_id TEXT NOT NULL,
    title TEXT NOT NULL,
    topic_key TEXT NOT NULL,
    part_number INTEGER,
    message_date TEXT,
    message_type TEXT,
    telegram_link TEXT NOT NULL,
    content_hash TEXT,
    UNIQUE(channel_id, id)
);

CREATE INDEX IF NOT EXISTS idx_messages_topic ON messages(topic_key);
CREATE INDEX IF NOT EXISTS idx_messages_title ON messages(title);
CREATE INDEX IF NOT EXISTS idx_messages_part ON messages(part_number);
"""

@contextmanager
def db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()

def upsert_message(path, row):
    with db(path) as conn:
        conn.execute("""
        INSERT INTO messages
        (id, channel_id, title, topic_key, part_number, message_date,
         message_type, telegram_link, content_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          channel_id=excluded.channel_id,
          title=excluded.title,
          topic_key=excluded.topic_key,
          part_number=excluded.part_number,
          message_date=excluded.message_date,
          message_type=excluded.message_type,
          telegram_link=excluded.telegram_link,
          content_hash=excluded.content_hash
        """, row)

def clear_channel(path, channel_id):
    with db(path) as conn:
        conn.execute("DELETE FROM messages WHERE channel_id=?", (str(channel_id),))

def topic_count(path):
    with db(path) as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT topic_key) FROM messages"
        ).fetchone()[0]

def message_count(path):
    with db(path) as conn:
        return conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

def get_topics(path, offset, limit):
    with db(path) as conn:
        return conn.execute("""
        SELECT topic_key, MIN(title) AS display_title, COUNT(*) AS total
        FROM messages
        GROUP BY topic_key
        ORDER BY LOWER(topic_key)
        LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()

def get_topic_messages(path, topic_key):
    with db(path) as conn:
        return conn.execute("""
        SELECT * FROM messages
        WHERE topic_key=?
        ORDER BY
          CASE WHEN part_number IS NULL THEN 999999 ELSE part_number END,
          COALESCE(message_date, '')
        """, (topic_key,)).fetchall()

def search(path, query, limit=30):
    q = f"%{query}%"
    with db(path) as conn:
        return conn.execute("""
        SELECT * FROM messages
        WHERE title LIKE ? OR topic_key LIKE ?
        ORDER BY topic_key, part_number
        LIMIT ?
        """, (q, q, limit)).fetchall()

def stats(path):
    with db(path) as conn:
        return {
            "topics": conn.execute(
                "SELECT COUNT(DISTINCT topic_key) FROM messages"
            ).fetchone()[0],
            "classes": conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0],
            "videos": conn.execute(
                "SELECT COUNT(*) FROM messages WHERE message_type='video'"
            ).fetchone()[0],
            "pdfs": conn.execute(
                "SELECT COUNT(*) FROM messages WHERE message_type='document'"
            ).fetchone()[0],
        }
