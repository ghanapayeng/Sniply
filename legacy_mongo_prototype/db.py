"""
MongoDB data layer.

Uses pymongo (the official MongoDB driver — infrastructure, not a
shortening library) to talk to Mongo. All the actual short-code
logic lives in shortener.py, not here.
"""

import os
from datetime import datetime, timezone

from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "url_shortener")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

links = db["links"]        # {_id/code, long_url, created_at, expires_at, password_hash, click_count}
clicks = db["clicks"]      # {code, timestamp, ip, referrer}  -- one doc per click, for analytics
counters = db["counters"]  # {_id: "link_id", seq: N}  -- our own auto-increment, Mongo doesn't have one built in


def init_indexes():
    links.create_index([("code", ASCENDING)], unique=True)
    clicks.create_index([("code", ASCENDING)])
    counters.update_one({"_id": "link_id"}, {"$setOnInsert": {"seq": 0}}, upsert=True)


def get_next_counter() -> int:
    """Our own auto-increment counter, since Mongo doesn't provide one natively."""
    result = counters.find_one_and_update(
        {"_id": "link_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


def save_link(code: str, long_url: str, expires_at=None, password_hash=None) -> bool:
    """Insert a new link doc. Returns False on code collision (caller should retry)."""
    try:
        links.insert_one({
            "code": code,
            "long_url": long_url,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "password_hash": password_hash,
            "click_count": 0,
        })
        return True
    except DuplicateKeyError:
        return False


def get_link(code: str):
    return links.find_one({"code": code})


def record_click(code: str, ip: str = None, referrer: str = None):
    clicks.insert_one({
        "code": code,
        "timestamp": datetime.now(timezone.utc),
        "ip": ip,
        "referrer": referrer,
    })
    links.update_one({"code": code}, {"$inc": {"click_count": 1}})


def get_click_history(code: str, limit: int = 100):
    return list(
        clicks.find({"code": code}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )


def delete_link(code: str) -> bool:
    result = links.delete_one({"code": code})
    return result.deleted_count > 0
