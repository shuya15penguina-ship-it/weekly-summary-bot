import json
import os
import uuid
from typing import Any

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")

GROUP_DEFAULTS: dict[str, Any] = {
    "name": "",
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
        return {"groups": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_groups() -> list[dict]:
    return load().get("groups", [])


def get_group(group_id: str) -> dict | None:
    return next((g for g in get_groups() if g["id"] == group_id), None)


def save_group(group: dict) -> None:
    data = load()
    groups = data.get("groups", [])
    for i, g in enumerate(groups):
        if g["id"] == group["id"]:
            groups[i] = group
            data["groups"] = groups
            save(data)
            return
    groups.append(group)
    data["groups"] = groups
    save(data)


def delete_group(group_id: str) -> None:
    data = load()
    data["groups"] = [g for g in data.get("groups", []) if g["id"] != group_id]
    save(data)


def new_group() -> dict:
    return {**GROUP_DEFAULTS, "id": str(uuid.uuid4())}
