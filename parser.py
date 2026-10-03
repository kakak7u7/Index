import re
import hashlib
from datetime import datetime

# Handles common forms:
# Part-1, Part 1, Part-01, PART-1
PART_RE = re.compile(r"\bpart\s*[-_:]?\s*0*(\d+)\b", re.I)

# Dates such as 29-March, 29 March, 01-April, 01 April
DATE_RE = re.compile(
    r"\b\d{1,2}\s*[-/ ]\s*"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b"
    r"|\b\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?\b",
    re.I
)

def extract_part(text):
    m = PART_RE.search(text or "")
    return int(m.group(1)) if m else None

def extract_date(text, fallback=None):
    text = text or ""
    m = DATE_RE.search(text)
    if m:
        return m.group(0)
    return fallback.strftime("%d-%b-%Y") if fallback else None

def topic_from_title(text):
    text = (text or "").strip()
    # Remove part/date/extra structural labels.
    text = PART_RE.sub(" ", text)
    text = DATE_RE.sub(" ", text)
    text = re.sub(r"\b(question\s*pdf|pdf|video)\b", " ", text, flags=re.I)

    # Remove common punctuation while preserving Unicode letters.
    text = re.sub(r"[_|•·]+", " ", text)
    text = re.sub(r"\s*[-–—:]+\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—:|")

    # Conservative normalization for repeated spacing.
    text = text.casefold().strip()

    # A few safe Hindi spacing normalizations.
    replacements = {
        "सामान्य पशु पालन": "सामान्य पशुपालन",
        "नवीनतम पशु गणना": "नवीनतम पशुगणना",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    return text or "अन्य"

def display_topic(key):
    return key

def message_type(message):
    if getattr(message, "video", None):
        return "video"
    if getattr(message, "document", None):
        return "document"
    if getattr(message, "photo", None):
        return "photo"
    if getattr(message, "audio", None):
        return "audio"
    return "text"

def content_hash(title, message_id):
    return hashlib.sha256(f"{message_id}|{title}".encode("utf-8")).hexdigest()
