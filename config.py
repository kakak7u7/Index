import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL = os.getenv("CHANNEL", "")
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
DB_PATH = os.getenv("DB_PATH", "classes.db")
SESSION_NAME = os.getenv("SESSION_NAME", "user_session")
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "8"))

def validate():
    missing = []
    for name, value in [
        ("API_ID", API_ID),
        ("API_HASH", API_HASH),
        ("BOT_TOKEN", BOT_TOKEN),
        ("CHANNEL", CHANNEL),
    ]:
        if not value:
            missing.append(name)
    if missing:
        raise RuntimeError(
            "Missing configuration: " + ", ".join(missing) +
            ". Edit .env and run again."
        )
