import json
import os
from typing import Any

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")

_defaults: dict[str, Any] = {
    "guild_id": None,
    "target_channel_ids": [],
    "output_channel_id": None,
    "schedule_day": "monday",
    "schedule_hour": 9,
    "schedule_minute": 0,
}


def load() -> dict[str, Any]:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return dict(_defaults)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {**_defaults, **data}


def save(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
