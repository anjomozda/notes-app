"""Entry point for the Notes app.

Run it with:

    python main.py
"""
from ui import NotesApp


def main() -> None:
    app = NotesApp()
    app.mainloop()


if __name__ == "__main__":
    main()
