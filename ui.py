"""The graphical interface, built with CustomTkinter.

Layout:

    ┌─────────────┬───────────────────────────────┐
    │  Sidebar    │  Editor                       │
    │             │                               │
    │  search     │  title                        │
    │  category   │  category                     │
    │  + New      │  body ...                     │
    │  note list  │                               │
    │  dark mode  │  [Save]  [Delete]   edited …  │
    └─────────────┴───────────────────────────────┘
"""
from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

import storage
from models import Note

ALL_CATEGORIES = "All categories"

# --- warm / soft colour palette (light, dark) ------------------------------
ACCENT = "#6C5CE7"           # indigo
ACCENT_HOVER = "#5A4BD4"     # darker indigo for hover
ACCENT_TEXT = "#FFFFFF"      # text on top of the accent colour

SIDEBAR_BG = ("gray94", "#1C1922")   # warm-tinted greys
EDITOR_BG = ("gray98", "#16131C")
FIELD_BG = ("white", "#211D2A")

CARD_NORMAL = ("gray92", "#272231")
CARD_HOVER = ("gray87", "#332C40")
CARD_ACTIVE = (ACCENT, ACCENT)

TITLE_TEXT = ("gray10", "gray95")
MUTED_TEXT = ("gray45", "gray60")
SUBTLE_ON_ACCENT = "#E7E3FF"         # secondary text on a selected row


class NoteListItem(ctk.CTkFrame):
    """A single clickable row in the sidebar note list."""

    def __init__(self, master, note: Note, selected: bool, on_click):
        super().__init__(master, corner_radius=10, fg_color="transparent")
        self.note = note
        self.on_click = on_click
        self._selected = selected

        self._normal = CARD_NORMAL
        self._hover = CARD_HOVER
        self._active = CARD_ACTIVE

        title_text = ("📌  " if note.pinned else "") + (note.title or "Untitled note")
        self.title_lbl = ctk.CTkLabel(
            self,
            text=title_text,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.title_lbl.pack(fill="x", padx=12, pady=(9, 0))

        self.sub_lbl = ctk.CTkLabel(
            self,
            text=f"{note.category} · {note.preview(40)}",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self.sub_lbl.pack(fill="x", padx=12, pady=(0, 9))

        # Make the whole row (and its labels) respond to clicks and hover.
        for widget in (self, self.title_lbl, self.sub_lbl):
            widget.bind("<Button-1>", self._clicked)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

        self._render_selected(selected)

    def _render_selected(self, selected: bool):
        """Colour the row and its text for the selected / unselected state."""
        if selected:
            self.configure(fg_color=self._active)
            self.title_lbl.configure(text_color=ACCENT_TEXT)
            self.sub_lbl.configure(text_color=SUBTLE_ON_ACCENT)
        else:
            self.configure(fg_color=self._normal)
            self.title_lbl.configure(text_color=TITLE_TEXT)
            self.sub_lbl.configure(text_color=MUTED_TEXT)

    def _clicked(self, _event):
        self.on_click(self.note)

    def _enter(self, _event):
        if not self._selected:
            self.configure(fg_color=self._hover)

    def _leave(self, _event):
        if not self._selected:
            self.configure(fg_color=self._normal)


class NotesApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # --- window basics ------------------------------------------------
        self.title("Notes")
        self.geometry("960x620")
        self.minsize(760, 480)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- state --------------------------------------------------------
        self.notes: list[Note] = storage.load_notes()
        self.current: Note | None = None
        self.search_var = ctk.StringVar()
        self.category_var = ctk.StringVar(value=ALL_CATEGORIES)
        self.search_var.trace_add("write", lambda *_: self.refresh_sidebar())

        # --- layout: two columns -----------------------------------------
        self.grid_columnconfigure(0, weight=0, minsize=290)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_editor()

        self.refresh_sidebar()
        self._show_editor(self.current)  # start with empty editor

        # Save everything when the window is closed.
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-s>", lambda _e: self.save_current())
        self.bind("<Control-n>", lambda _e: self.new_note())

    # ------------------------------------------------------------------ UI
    def _build_sidebar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, fg_color=SIDEBAR_BG)
        bar.grid(row=0, column=0, sticky="nsew")
        bar.grid_rowconfigure(4, weight=1)  # note list expands
        bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bar, text="📝  Notes",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))

        self.search_entry = ctk.CTkEntry(
            bar, textvariable=self.search_var, placeholder_text="Search notes…"
        )
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=6)

        self.category_menu = ctk.CTkOptionMenu(
            bar, variable=self.category_var,
            values=[ALL_CATEGORIES], command=lambda _v: self.refresh_sidebar(),
            fg_color=FIELD_BG, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
        )
        self.category_menu.grid(row=2, column=0, sticky="ew", padx=16, pady=6)

        ctk.CTkButton(
            bar, text="＋  New note", command=self.new_note,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=3, column=0, sticky="ew", padx=16, pady=(6, 10))

        self.list_frame = ctk.CTkScrollableFrame(bar, fg_color="transparent")
        self.list_frame.grid(row=4, column=0, sticky="nsew", padx=8, pady=4)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.dark_switch = ctk.CTkSwitch(
            bar, text="Dark mode", command=self._toggle_theme,
            progress_color=ACCENT,
        )
        self.dark_switch.select()  # starts in dark mode
        self.dark_switch.grid(row=5, column=0, sticky="w", padx=18, pady=12)

    def _build_editor(self):
        editor = ctk.CTkFrame(self, corner_radius=0, fg_color=EDITOR_BG)
        editor.grid(row=0, column=1, sticky="nsew")
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(2, weight=1)  # body expands
        self.editor = editor

        self.title_entry = ctk.CTkEntry(
            editor, placeholder_text="Title",
            font=ctk.CTkFont(size=20, weight="bold"), height=44,
        )
        self.title_entry.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))

        self.category_entry = ctk.CTkEntry(
            editor, placeholder_text="Category (e.g. Work, Ideas, Personal)"
        )
        self.category_entry.grid(row=1, column=0, sticky="ew", padx=24, pady=8)

        self.body_box = ctk.CTkTextbox(
            editor, font=ctk.CTkFont(size=14), wrap="word", corner_radius=10,
            fg_color=FIELD_BG, border_width=0,
        )
        self.body_box.grid(row=2, column=0, sticky="nsew", padx=24, pady=8)
        self.body_box.bind("<KeyRelease>", self._update_counts)

        # Word / character count and creation date, just under the text area.
        self.stats_lbl = ctk.CTkLabel(
            editor, text="", anchor="w", text_color=MUTED_TEXT,
            font=ctk.CTkFont(size=11),
        )
        self.stats_lbl.grid(row=3, column=0, sticky="ew", padx=26, pady=(0, 2))

        actions = ctk.CTkFrame(editor, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=24, pady=(4, 20))
        actions.grid_columnconfigure(4, weight=1)

        self.save_btn = ctk.CTkButton(
            actions, text="💾  Save", width=92, command=self.save_current,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
        )
        self.save_btn.grid(row=0, column=0, padx=(0, 8))

        self.pin_btn = ctk.CTkButton(
            actions, text="📌  Pin", width=96, command=self.toggle_pin,
        )
        self.pin_btn.grid(row=0, column=1, padx=(0, 8))

        self.export_btn = ctk.CTkButton(
            actions, text="⬆  Export", width=96, command=self.export_current,
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray20", "gray85"),
            hover_color=("gray85", "#332C40"),
        )
        self.export_btn.grid(row=0, column=2, padx=(0, 8))

        self.delete_btn = ctk.CTkButton(
            actions, text="🗑  Delete", width=96, command=self.delete_current,
            fg_color="transparent", hover_color=("gray85", "#332C40"),
            text_color=("#B23A3A", "#E86D6D"), border_width=1,
            border_color=("#B23A3A", "#E86D6D"),
        )
        self.delete_btn.grid(row=0, column=3, padx=(0, 8))

        self.meta_lbl = ctk.CTkLabel(
            actions, text="", anchor="e", text_color=("gray45", "gray60")
        )
        self.meta_lbl.grid(row=0, column=4, sticky="e")

    # -------------------------------------------------------------- helpers
    def categories(self) -> list[str]:
        """All category names currently in use, sorted."""
        names = sorted({n.category.strip() or "General" for n in self.notes})
        return [ALL_CATEGORIES] + names

    def filtered_notes(self) -> list[Note]:
        """Notes that match the current search text and category filter."""
        query = self.search_var.get().strip().lower()
        category = self.category_var.get()

        def matches(note: Note) -> bool:
            if category != ALL_CATEGORIES and note.category != category:
                return False
            if query:
                haystack = f"{note.title} {note.category} {note.body}".lower()
                if query not in haystack:
                    return False
            return True

        result = [n for n in self.notes if matches(n)]
        # Newest first, then float pinned notes to the top (stable sort keeps
        # each group in newest-first order).
        result.sort(key=lambda n: n.updated_at, reverse=True)
        result.sort(key=lambda n: not n.pinned)
        return result

    # ------------------------------------------------------------- rendering
    def refresh_sidebar(self):
        """Rebuild the category dropdown and the visible note list."""
        # Keep the category dropdown in sync with existing categories.
        cats = self.categories()
        self.category_menu.configure(values=cats)
        if self.category_var.get() not in cats:
            self.category_var.set(ALL_CATEGORIES)

        # Clear the old list items.
        for child in self.list_frame.winfo_children():
            child.destroy()

        notes = self.filtered_notes()
        if not notes:
            ctk.CTkLabel(
                self.list_frame, text="No notes found.",
                text_color=("gray50", "gray55"),
            ).grid(row=0, column=0, pady=20)
            return

        for row, note in enumerate(notes):
            item = NoteListItem(
                self.list_frame, note,
                selected=(self.current is not None and note.id == self.current.id),
                on_click=self.select_note,
            )
            item.grid(row=row, column=0, sticky="ew", pady=3, padx=2)

    def _show_editor(self, note: Note | None):
        """Load a note into the editor, or show the empty state."""
        self.title_entry.delete(0, "end")
        self.category_entry.delete(0, "end")
        self.body_box.delete("1.0", "end")

        has_note = note is not None
        state = "normal" if has_note else "disabled"
        for widget in (self.title_entry, self.category_entry, self.body_box,
                       self.save_btn, self.pin_btn, self.export_btn,
                       self.delete_btn):
            widget.configure(state=state)

        if has_note:
            self.title_entry.insert(0, note.title)
            self.category_entry.insert(0, note.category)
            self.body_box.insert("1.0", note.body)
            self.meta_lbl.configure(text=f"Last edited {note.updated_label()}")
        else:
            self.meta_lbl.configure(text="Select a note or create a new one")

        self._update_pin_button()
        self._update_counts()

    # ---------------------------------------------------------------- actions
    def select_note(self, note: Note):
        """Switch to another note, auto-saving the current one first."""
        if self.current is not None and note.id == self.current.id:
            return
        self._commit_editor_to_current()  # don't lose unsaved edits
        self.current = note
        self._show_editor(note)
        self.refresh_sidebar()

    def new_note(self):
        self._commit_editor_to_current()
        note = Note(title="Untitled note", category="General", body="")
        self.notes.append(note)
        self.current = note
        storage.save_notes(self.notes)
        self._show_editor(note)
        self.refresh_sidebar()
        self.title_entry.focus_set()
        self.title_entry.select_range(0, "end")

    def _commit_editor_to_current(self) -> bool:
        """Copy the editor fields into the current note. Returns True if saved."""
        if self.current is None:
            return False
        title = self.title_entry.get().strip() or "Untitled note"
        category = self.category_entry.get().strip() or "General"
        body = self.body_box.get("1.0", "end").rstrip("\n")

        changed = (
            title != self.current.title
            or category != self.current.category
            or body != self.current.body
        )
        if changed:
            self.current.title = title
            self.current.category = category
            self.current.body = body
            self.current.touch()
            storage.save_notes(self.notes)
        return changed

    def save_current(self):
        if self.current is None:
            return
        self._commit_editor_to_current()
        self.meta_lbl.configure(text=f"Saved · {self.current.updated_label()}")
        self.refresh_sidebar()

    def delete_current(self):
        if self.current is None:
            return
        if not messagebox.askyesno(
            "Delete note",
            f"Delete “{self.current.title}”?\nThis cannot be undone.",
        ):
            return
        self.notes = [n for n in self.notes if n.id != self.current.id]
        self.current = None
        storage.save_notes(self.notes)
        self._show_editor(None)
        self.refresh_sidebar()

    def toggle_pin(self):
        """Pin or unpin the current note so it floats to the top of the list."""
        if self.current is None:
            return
        self.current.pinned = not self.current.pinned
        storage.save_notes(self.notes)
        self._update_pin_button()
        self.refresh_sidebar()

    def _update_pin_button(self):
        """Style the Pin button to reflect the current note's pinned state."""
        pinned = self.current is not None and self.current.pinned
        if pinned:
            self.pin_btn.configure(
                text="📌  Pinned", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                text_color=ACCENT_TEXT, border_width=0,
            )
        else:
            self.pin_btn.configure(
                text="📌  Pin", fg_color="transparent",
                hover_color=("gray85", "#332C40"),
                text_color=("gray20", "gray85"),
                border_width=1, border_color=("gray70", "gray40"),
            )

    def _update_counts(self, _event=None):
        """Refresh the 'N words · M characters · Created …' line."""
        if self.current is None:
            self.stats_lbl.configure(text="")
            return
        text = self.body_box.get("1.0", "end").strip()
        words = len(text.split()) if text else 0
        chars = len(text)
        self.stats_lbl.configure(
            text=f"{words} words · {chars} characters"
            f" · Created {self.current.created_date_label()}"
        )

    def export_current(self):
        """Save the current note to a .txt or .md file chosen by the user."""
        if self.current is None:
            return
        self._commit_editor_to_current()  # export the latest text
        note = self.current
        safe = "".join(
            c for c in note.title if c.isalnum() or c in " -_"
        ).strip() or "note"
        path = filedialog.asksaveasfilename(
            title="Export note",
            defaultextension=".md",
            initialfile=f"{safe}.md",
            filetypes=[
                ("Markdown", "*.md"),
                ("Text file", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return  # user cancelled
        if path.lower().endswith(".md"):
            content = f"# {note.title}\n\n*{note.category}*\n\n{note.body}\n"
        else:
            content = f"{note.title}\n{note.category}\n\n{note.body}\n"
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.meta_lbl.configure(text=f"Exported · {note.title}")

    # ------------------------------------------------------------------ misc
    def _toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.dark_switch.get() else "light")

    def _on_close(self):
        self._commit_editor_to_current()
        self.destroy()
