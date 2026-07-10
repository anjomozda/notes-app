"""Persistence layer: load and save notes to a local JSON file.

The file lives next to this script (``notes_data.json``) so the app works
no matter which folder you run it from. This file is ignored by git, so
your personal notes never get committed to GitHub.
"""
from __future__ import annotations

import json
from pathlib import Path

from models import Note

# Store the data file right next to the source code.
DATA_FILE = Path(__file__).resolve().parent / "notes_data.json"


def load_notes() -> list[Note]:
    """Read all notes from disk. Returns an empty list on first run."""
    if not DATA_FILE.exists():
        return []
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # File is missing or corrupted -> start clean instead of crashing.
        return []
    if not isinstance(raw, list):
        return []
    return [Note.from_dict(item) for item in raw if isinstance(item, dict)]


def save_notes(notes: list[Note]) -> None:
    """Write all notes to disk as pretty-printed JSON (UTF-8)."""
    data = [note.to_dict() for note in notes]
    DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
