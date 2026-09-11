"""Read Elite Dangerous Journal JSONL and Status.json without semantic guessing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

JsonObject = dict[str, Any]


def iter_journal_events(path: str | Path) -> Iterator[JsonObject]:
    """Yield Journal events in file order.

    Blank lines are ignored. Every non-blank line must decode to a JSON object;
    malformed input raises ValueError with the source line number instead of
    silently dropping an event.
    """
    journal_path = Path(path)
    with journal_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                event = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid Journal JSON at line {line_number}: {exc.msg}"
                ) from exc
            if not isinstance(event, dict):
                raise ValueError(
                    f"Journal line {line_number} must contain a JSON object"
                )
            yield event


def read_journal_events(path: str | Path) -> list[JsonObject]:
    """Read all Journal events in file order."""
    return list(iter_journal_events(path))


def latest_journal_event(path: str | Path, event_name: str) -> JsonObject | None:
    """Return the latest event whose ``event`` field matches ``event_name``."""
    latest: JsonObject | None = None
    for event in iter_journal_events(path):
        if event.get("event") == event_name:
            latest = event
    return latest


def read_status(path: str | Path) -> JsonObject:
    """Read Status.json and require a JSON object at the top level."""
    status_path = Path(path)
    with status_path.open("r", encoding="utf-8") as handle:
        status = json.load(handle)
    if not isinstance(status, dict):
        raise ValueError("Status.json must contain a JSON object")
    return status
