"""Who may see what. Filtering happens BEFORE anything is generated for a reader."""
from __future__ import annotations
from . import config


def can_see(role: str, visibility: str) -> bool:
    return config.LEVELS.get(visibility, 3) <= config.ROLE_LEVEL.get(role, 1)


def filter_items(items: list, role: str) -> list:
    return [i for i in items if can_see(role, i["visibility"])]


def restricted_count(items: list, role: str) -> int:
    return sum(1 for i in items if not can_see(role, i["visibility"]))
