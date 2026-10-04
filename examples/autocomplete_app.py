#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: examples/autocomplete_app.py
==========================================
A complete desktop app: type Urdu, get instant suggestions from the gzip
dictionary. Windows-friendly (Segoe UI, UTF-8 console, no dependencies).

    python examples/autocomplete_app.py                 # default database
    python examples/autocomplete_app.py --db urdu_database.full.txt.gz
    python examples/autocomplete_app.py --list          # headless self-check (no Tk needed)
    python examples/autocomplete_app.py --words 5       # smoke test, print 5 suggestions

Package it as a single .exe with the database inside:

    pyinstaller --onefile --add-data "urdu_database.txt.gz;." examples/autocomplete_app.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_urdu_database import UrduEngine    # noqa: E402


# --------------------------------------------------------------------------- UI
def build_app(root, engine: UrduEngine, db_name: str):
    """Create the window. Imported lazily so --list works on headless machines."""
    import tkinter as tk
    from tkinter import ttk

    class UrduAutocompleteApp(ttk.Frame):
        """Live Urdu autocomplete backed by urdu_database.txt.gz."""

        def __init__(self, master, engine: UrduEngine, db_name: str):
            super().__init__(master, padding=12)
            self.engine = engine
            self.pack(fill="both", expand=True)
            master.title("urduofdani - Urdu Text Engine (%s)" % db_name)
            master.geometry("660x440")
            master.minsize(480, 320)

            ttk.Label(
                self,
                text="اردو لکھیں / Type Urdu (suggestions appear as you type):",
                font=("Segoe UI", 11, "bold"),
            ).pack(anchor="w")

            self.var = tk.StringVar()
            self.entry = ttk.Entry(self, textvariable=self.var, font=("Segoe UI", 16),
                                   justify="right")
            self.entry.pack(fill="x", pady=(6, 8))
            self.entry.focus_set()

            self.status = tk.StringVar(value="Dictionary: %s words" % f"{len(self.engine):,}")
            ttk.Label(self, textvariable=self.status, foreground="#666").pack(anchor="w")

            self.listbox = tk.Listbox(self, font=("Segoe UI", 14), height=11,
                                      activestyle="none", exportselection=False)
            self.listbox.pack(fill="both", expand=True, pady=8)

            bar = ttk.Frame(self)
            bar.pack(fill="x")
            ttk.Button(bar, text="Random word", command=self.show_random).pack(side="left")
            ttk.Button(bar, text="Clear", command=self.clear).pack(side="left", padx=6)
            ttk.Button(bar, text="Quit", command=master.destroy).pack(side="right")

            self.var.trace_add("write", lambda *_: self.refresh())
            self.entry.bind("<Down>", lambda e: self._move(1))
            self.entry.bind("<Up>", lambda e: self._move(-1))
            self.entry.bind("<Return>", lambda e: self.accept())
            self.entry.bind("<Escape>", lambda e: self.listbox.selection_clear(0, "end"))

        def refresh(self) -> None:
            query = self.var.get().strip()
            self.listbox.delete(0, "end")
            if not query:
                self.status.set("Dictionary: %s words" % f"{len(self.engine):,}")
                return
            hits = self.engine.suggest(query, limit=60)
            for word in hits:
                self.listbox.insert("end", word)
            self.status.set("%d suggestion(s) for '%s'%s" % (
                len(hits), query, "" if hits else " - word not found"))
            if hits:
                self.listbox.selection_set(0)

        def _move(self, delta: int) -> None:
            size = self.listbox.size()
            if not size:
                return
            index = (self.listbox.curselection()[0] + delta) % size \
                if self.listbox.curselection() else 0
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(index)
            self.listbox.see(index)

        def accept(self) -> None:
            selection = self.listbox.curselection()
            if selection:
                self.var.set(self.listbox.get(selection[0]))
                self.listbox.delete(0, "end")

        def show_random(self) -> None:
            self.var.set(self.engine.random_word())

        def clear(self) -> None:
            self.var.set("")
            self.entry.focus_set()

    return UrduAutocompleteApp(root, engine, db_name)


# ------------------------------------------------------------------------ main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="urduofdani autocomplete demo")
    parser.add_argument("--db", default=None, help="database .gz to load")
    parser.add_argument("--list", action="store_true",
                        help="headless check: print stats and exit (no Tk window)")
    parser.add_argument("--words", type=int, default=0,
                        help="print N sample suggestions for 'کمپیو' and exit")
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):          # Windows cp1252 safety
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    engine = UrduEngine(args.db)                     # ~2.5 ms, auto-locates the .gz
    if args.list or args.words:
        print("database : %s" % engine.path.name)
        print("words    : %s" % f"{len(engine):,}")
        print("load     : %.2f ms" % (engine.load_seconds * 1000))
        print("sample   : %s" % " ".join(engine.suggest("کمپیو", args.words or 6)))
        return 0

    try:
        import tkinter as tk
    except ImportError:
        print("[urduofdani] tkinter is not available in this Python build.\n"
              "             Use --list for a headless check, or install the Tk package.",
              file=sys.stderr)
        return 2

    root = tk.Tk()
    build_app(root, engine, engine.path.name)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
