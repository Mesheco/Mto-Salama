"""
Reports from the river: a tiny shared store.

Anyone near a crossing can send a short anonymous report; the local leader's
page reads the reports from the last 24 hours.

Privacy by design:
  - no name, phone number or location of the sender is asked for or stored
  - anything that looks like a phone number is removed from the text
  - only the crossing, the message text and the time are kept, for 24 hours

Prototype note: reports live in a small file on the server. On free hosting
the file is wiped whenever the app restarts - fine for a demo, not for real use.
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone

STORE = os.path.join("data", "live_reports.jsonl")
KEEP_HOURS = 24
MAX_LEN = 200
MAX_STORED = 300
NAIROBI = timezone(timedelta(hours=3))
_lock = threading.Lock()

_PHONE = re.compile(r"(\+?\d[\d\s-]{7,}\d)")


def clean_text(text: str) -> str:
    """Remove phone numbers and extra spaces; cut to a short SMS length."""
    t = _PHONE.sub("[number removed]", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:MAX_LEN]


def _read_all() -> list[dict]:
    if not os.path.exists(STORE):
        return []
    rows = []
    with open(STORE, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def add_report(crossing_id: str, text: str) -> tuple[bool, str]:
    t = clean_text(text)
    if len(t) < 3:
        return False, "Please write a short message. / Tafadhali andika ujumbe mfupi."
    row = {
        "id": uuid.uuid4().hex[:8],
        "crossing_id": crossing_id,
        "text": t,
        "time": datetime.now(NAIROBI).isoformat(timespec="minutes"),
    }
    with _lock:
        os.makedirs(os.path.dirname(STORE), exist_ok=True)
        rows = _read_all()[-(MAX_STORED - 1):] + [row]
        with open(STORE, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return True, t


def recent_reports(crossing_id: str, hours: int = KEEP_HOURS) -> list[dict]:
    cutoff = datetime.now(NAIROBI) - timedelta(hours=hours)
    out = []
    for r in _read_all():
        try:
            when = datetime.fromisoformat(r["time"])
        except (KeyError, ValueError):
            continue
        if r.get("crossing_id") == crossing_id and when >= cutoff:
            out.append(r)
    return out
