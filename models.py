"""Data model for a single note.

A Note is a plain data object. Keeping it separate from the UI and the
storage layer makes the code easy to read and easy to test.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime


def _now_iso() -> str:
    """Current time as an ISO string, e.g. '2026-07-10T14:30:00'."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Note:
    """One note with a title, a category and a body of text."""

    title: str = "Untitled note"
    category: str = "General"
    body: str = ""
    pinned: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def touch(self) -> None:
        """Mark the note as modified right now."""
        self.updated_at = _now_iso()

    def preview(self, length: int = 60) -> str:
        """Short single-line snippet of the body for the sidebar list."""
        text = " ".join(self.body.split())  # collapse whitespace/newlines
        if len(text) > length:
            return text[:length].rstrip() + "…"
        return text or "No text yet"

    @staticmethod
    def _format(iso: str, pattern: str) -> str:
        """Format an ISO timestamp, falling back to the raw string on error."""
        try:
            return datetime.fromisoformat(iso).strftime(pattern)
        except ValueError:
            return iso

    def updated_label(self) -> str:
        """Human-friendly 'last edited' label, e.g. 'Jul 10, 2026 14:30'."""
        return self._format(self.updated_at, "%b %d, %Y %H:%M")

    def created_date_label(self) -> str:
        """Date the note was created, e.g. 'Jul 10, 2026'."""
        return self._format(self.created_at, "%b %d, %Y")

    def word_count(self) -> int:
        """Number of words in the body."""
        return len(self.body.split())

    # --- (de)serialization ------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to a plain dict so it can be saved as JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """Rebuild a Note from a dict, ignoring any unknown keys."""
        known = {name: data[name] for name in cls.__dataclass_fields__ if name in data}
        return cls(**known)
