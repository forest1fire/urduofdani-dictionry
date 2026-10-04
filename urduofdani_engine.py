#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani_engine — the heart of UrduOfDani
===========================================
A single self-contained file (stdlib only, MIT, free for everyone) that gives any
Python project a fast, storage-friendly Urdu dictionary engine.

Drop two files next to your app and you are done::

    your_app/
    ├── urduofdani_engine.py        <- this file (copy it)
    ├── urdu_database.compact.gz    <- 25 KB, 24,581 words   (smallest)
    └── urdu_database.txt.gz        <- 71 KB, 24,581 words   (fastest)

Quick start
-----------
::

    from urduofdani_engine import UrduEngine

    urdu = UrduEngine()                 # auto-finds the database, ~4 ms
    urdu.is_word("کتاب")                # True   (O(1), folded)
    urdu.is_word("كِتاب")               # True   (Arabic spelling + harakat folded)
    urdu.suggest("کمپیو")               # ['کمپیوٹر', 'کمپیوٹربان', ...]
    urdu.unknown("میں نے کتاب پڑھی")     # []     (spell-check a whole sentence)
    urdu.random_words(5)                # 5 random words

    urdu.preload()                      # optional: warm the index in a thread

Why it is fast
--------------
* **One gzip blob, one read.** No per-word objects on disk, no CSV parsing.
* **Two containers, auto-detected** from a magic header:
  - ``plain``   — single space separated: one C-level ``split`` (fastest).
  - ``compact`` — front-coded delta entries: ~3x smaller on disk, a few ms more.
* **O(1) membership** on a ``frozenset``, **O(log n)** autocomplete via ``bisect``.
* **Optional threaded preload** so the first keystroke never waits.
* **Lazy mode** for apps that only need a word count or an early suggestion.

Everything degrades gracefully: if no database is found, the engine still loads
(a 40-word built-in fallback) instead of crashing the host app.

Public API
----------
``UrduEngine(db=None, lazy=False, verify=False)``
    ``len(urdu)`` · ``word in urdu`` · ``urdu.words()`` · ``urdu.path``
    ``urdu.is_word(w)`` · ``urdu.suggest(p, limit)`` · ``urdu.starts(p)``
    ``urdu.unknown(text)`` · ``urdu.correct(word)`` · ``urdu.tokenize(text)``
    ``urdu.random_words(n)`` · ``urdu.extend(words)`` · ``urdu.info()``
    ``urdu.load()`` · ``urdu.load_seconds`` · ``urdu.preload()`` · ``urdu.wait()``
Module helpers: ``find_database()`` · ``read_database(path)`` · ``canonical(word)``

CLI: ``python urduofdani_engine.py --info`` · ``--bench`` · ``--check کتاب``
     · ``--suggest کمپیو`` · ``--spell "میں نے کتاب پڑھی"`` · ``--db PATH``

MIT License — see LICENSE in the repository this file came from.
"""

from __future__ import annotations

import bisect
import gzip
import os
import pathlib
import random
import re
import sys
import threading
import time
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

__version__ = "3.1.0"
__all__ = [
    "UrduEngine", "find_database", "read_database", "canonical", "COMPACT_MAGIC",
    "DB_NAMES", "FALLBACK_WORDS",
]

# --------------------------------------------------------------------------- #
# 1. Where the data lives
# --------------------------------------------------------------------------- #
DB_NAMES: Tuple[str, ...] = (
    "urdu_database.compact.gz",          # smallest first: 25 KB
    "urdu_database.txt.gz",              # fastest first: 71 KB
    "urdu_database.full.compact.gz",
    "urdu_database.full.txt.gz",
)
COMPACT_MAGIC = "URDUFC1"
SEPARATOR = " "

# A tiny built-in vocabulary so the engine never leaves the host app empty-handed.
FALLBACK_WORDS: Tuple[str, ...] = (
    "اردو زبان کا لفظ کتاب قلم دوست گھر شہر پانی آسمان زمین روشنی دن رات صبح شام "
    "ماں باپ بھائی بہن بچہ استاد شاگرد سکول دفتر کام پیسہ وقت سال مہینہ ہفتہ آج کل "
    "کمپیوٹر موبائل انٹرنیٹ فائل لنک صفحہ تلاش لفظ معنی درست غلط خوش آسان مشکل"
).split()


def find_database(start: Optional[str | os.PathLike[str]] = None) -> Optional[pathlib.Path]:
    """Locate the dictionary .gz next to the app, the cwd or a PyInstaller bundle."""
    here = pathlib.Path(__file__).resolve().parent
    roots: List[pathlib.Path] = []
    # An explicit path always wins - a file named directly, not a directory to
    # be searched with the default file names.
    override = os.environ.get("URDUOFDANI_DB")
    if override:
        env_path = pathlib.Path(override)
        if env_path.is_file():
            return env_path
        roots.append(env_path)
    if start is not None:
        candidate = pathlib.Path(start)
        if candidate.is_file():
            return candidate
        roots += [candidate, candidate.parent]
    roots += [
        pathlib.Path.cwd(),
        here,
        here / "data",
        here.parent,
        pathlib.Path(getattr(sys, "_MEIPASS", here)),        # PyInstaller --onefile
        pathlib.Path(sys.executable).resolve().parent,
    ]
    seen: Set[pathlib.Path] = set()
    for name in DB_NAMES:
        for root in roots:
            candidate = (root / name)
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.is_file():
                return candidate
    return None


# --------------------------------------------------------------------------- #
# 2. Orthography - the same folding the compiler used, so lookups always match
# --------------------------------------------------------------------------- #
_FOLD_MAP: Dict[int, str] = {
    0x0623: "\u0627",   # أ -> ا
    0x0625: "\u0627",   # إ -> ا
    0x0629: "\u06C1",   # ة -> ہ
    0x0647: "\u06C1",   # ه -> ہ
    0x0643: "\u06A9",   # ك -> ک
    0x0649: "\u06CC",   # ى -> ی
    0x064A: "\u06CC",   # ي -> ی
    0x06C0: "\u06C1",   # ۀ -> ہ
    0x06C2: "\u06C1",   # ۂ -> ہ
    0x06D3: "\u06D2",   # ۓ -> ے
    0x200B: "", 0x200E: "", 0x200F: "", 0x0640: "",
    0x0651: "", 0x0654: "", 0x0655: "", 0x0670: "",
}
_FOLD = str.maketrans(_FOLD_MAP)
_HARAKAT = re.compile(r"[\u064B-\u0650\u0652-\u0653\u0656-\u065F\u0670\u06D6-\u06ED]")
_PUNCT = re.compile(r"[\s,.;:!?،؛؟٪%\-_/\\|@#$^&*+=~`'\"()\[\]{}<>«»…\u2009\u2026\u060C\u061B\u061F]")
# one or more Urdu letters = one token (drives tokenize()/spell-check)
_TOKEN = re.compile(r"[\u0600-\u06FF\u0750-\u077F]+")


def canonical(word: str) -> str:
    """Fold a word to its canonical dictionary spelling.

    ``كِتاب`` → ``کتاب`` · ``خدا`` → ``خدا`` · ``ﻻہور`` (presentation form) → ``لاہور``
    """
    if not word:
        return ""
    word = unicodedata.normalize("NFKC", word).translate(_FOLD)
    word = _HARAKAT.sub("", word)
    word = _PUNCT.sub("", word)
    return unicodedata.normalize("NFC", word).strip()


# --------------------------------------------------------------------------- #
# 3. Reading a database (plain and compact containers)
# --------------------------------------------------------------------------- #
def _unpack_compact(payload: str, verify: bool = False) -> List[str]:
    """Decode front-coded entries: two base-36 prefix digits + suffix, per line."""
    lines = payload.split("\n")
    head = lines[0].split(" ")
    expected = int(head[1]) if len(head) > 1 and head[1].isdigit() else -1
    words: List[str] = []
    append = words.append
    prev = ""
    for line in lines[1:]:
        if line:
            word = prev[: int(line[:2], 36)] + line[2:]
            append(word)
            prev = word
    if expected >= 0 and len(words) != expected:
        raise ValueError("compact database truncated: %d of %d words" % (len(words), expected))
    return words


def read_database(path: str | os.PathLike[str], verify: bool = False) -> List[str]:
    """Read either container and return the sorted word list."""
    with gzip.open(path, "rb") as fh:
        payload = fh.read().decode("utf-8")
    if not payload:
        return []
    if payload.startswith(COMPACT_MAGIC):
        return _unpack_compact(payload, verify=verify)
    return payload.split(SEPARATOR)


# --------------------------------------------------------------------------- #
# 4. The engine
# --------------------------------------------------------------------------- #
class UrduEngine:
    """A tiny, fast Urdu dictionary: membership, autocomplete and spell-check.

    ``lazy=True`` defers the gzip read until the first query, so a GUI can build
    its window first and load the 71 KB dictionary afterwards - or call
    :meth:`preload` to warm it in a background thread.
    """

    def __init__(self, db: Optional[str | os.PathLike[str]] = None,
                 lazy: bool = False, verify: bool = False) -> None:
        self.path = pathlib.Path(db) if db else find_database()
        self.load_seconds = 0.0
        self.source = "fallback"
        self._lazy = lazy
        self._verify = verify
        self._words: List[str] = []
        self._index: Dict[str, int] = {}
        self._set: Set[str] = set()
        self._thread: Optional[threading.Thread] = None
        if not lazy:
            self.load()

    # ---------------------------------------------------------------- loading
    def load(self) -> List[str]:
        """Read the database (idempotent). Returns the word list."""
        if self._words:
            return self._words
        t0 = time.perf_counter()
        words: List[str] = []
        if self.path and pathlib.Path(self.path).is_file():
            try:
                words = read_database(self.path, verify=self._verify)
                self.source = "compact" if _is_compact(self.path) else "plain"
            except (OSError, EOFError, ValueError) as exc:      # never crash the app
                print("[urduofdani] could not read %s (%s) - using fallback words"
                      % (self.path, exc), file=sys.stderr)
        if not words:
            words = list(FALLBACK_WORDS)
            self.source = "fallback"
        self._words = words
        self._set = set(words)
        self._index = {word: i for i, word in enumerate(words)}
        self.load_seconds = time.perf_counter() - t0
        return words

    def preload(self) -> "UrduEngine":
        """Warm the index in a daemon thread; call :meth:`wait` to join it.

        This is the zero-lag trick for a GUI: build your window while the
        dictionary loads in parallel, then query it.
        """
        if self._words:
            return self
        self._thread = threading.Thread(target=self.load, name="urduofdani-load", daemon=True)
        self._thread.start()
        return self

    def wait(self, timeout: Optional[float] = None) -> "UrduEngine":
        """Block until a :meth:`preload` finished."""
        if self._thread is not None:
            self._thread.join(timeout)
        return self

    # ------------------------------------------------------------------- data
    def words(self) -> List[str]:
        """The full sorted word list (loads on demand in lazy mode)."""
        return self.load()

    def info(self) -> Dict[str, object]:
        """Everything a status line or an About box wants to show."""
        packed = pathlib.Path(self.path).stat().st_size if self.path and pathlib.Path(self.path).is_file() else 0
        return {
            "path": str(self.path) if self.path else "",
            "source": self.source,
            "words": len(self),
            "packed_bytes": packed,
            "load_ms": round(self.load_seconds * 1000, 3),
            "version": __version__,
        }

    # -------------------------------------------------------------- queries
    def is_word(self, word: str) -> bool:
        """True when *word* is in the dictionary (folded: ك→ک، harakat stripped)."""
        if not self._words:
            self.load()
        return canonical(word) in self._set

    __contains__ = is_word

    def starts(self, prefix: str, limit: int = 0) -> List[str]:
        """Every dictionary word starting with *prefix* (binary search, O(log n))."""
        prefix = canonical(prefix)
        if not prefix:
            return []
        words = self.load()
        lo = bisect.bisect_left(words, prefix)
        out: List[str] = []
        for word in words[lo:]:
            if not word.startswith(prefix):
                break
            out.append(word)
            if limit and len(out) >= limit:
                break
        return out

    def suggest(self, prefix: str, limit: int = 10) -> List[str]:
        """Autocomplete. Exact match first, then the rest in dictionary order."""
        prefix = canonical(prefix)
        if not prefix:
            return []
        hits = self.starts(prefix, limit + 1 if limit else 0)
        if prefix in hits:
            hits.remove(prefix)
            hits.insert(0, prefix)
        return hits[:limit] if limit else hits

    def tokenize(self, text: str) -> List[str]:
        """Split Urdu text into words (drops Latin, digits and punctuation)."""
        return _TOKEN.findall(text or "")

    def unknown(self, text: str, fold: bool = True) -> List[str]:
        """Spell-check a whole sentence: the tokens that are *not* in the dictionary.

        Numbers and Latin words are ignored, so ``میں نے کتاب پڑھی`` → ``[]``.
        """
        if not self._words:
            self.load()
        checker = self._set if not fold else None
        out: List[str] = []
        for token in self.tokenize(text):
            candidate = canonical(token) if fold else token
            if candidate and (candidate not in checker if checker is not None else candidate not in self._set):
                if candidate not in self._set:
                    out.append(token)
        return out

    def correct(self, word: str, limit: int = 5) -> List[str]:
        """'Did you mean …' - cheap candidates (same first letter + length) then
        ``difflib`` ranking. Returns [] when the word is already known."""
        if self.is_word(word):
            return []
        target = canonical(word)
        if not target:
            return []
        pool = [w for w in self.starts(target[:1]) if abs(len(w) - len(target)) <= 3]
        if not pool:
            pool = self.starts(target[:2]) or self.load()[:4000]
        import difflib
        return difflib.get_close_matches(target, pool, n=limit, cutoff=0.6)

    def random_words(self, count: int = 5, seed: Optional[int] = None) -> List[str]:
        """Random dictionary words (pass a seed for reproducible demos/tests)."""
        words = self.load()
        rng = random.Random(seed)
        count = max(1, min(count, len(words)))
        return rng.sample(words, count)

    # ----------------------------------------------------------------- extending
    def extend(self, words: Iterable[str], strict: bool = True) -> int:
        """Add your own domain words at runtime (company names, product terms…).

        Returns how many were added. With ``strict=False`` a multi-word entry is
        fused into one token instead of being skipped.
        """
        added = 0
        for raw in words:
            candidate = canonical(raw)
            if not candidate:
                continue
            if not strict and len(candidate.split()) > 1:
                candidate = candidate.replace(" ", "")
            if candidate in self._set:
                continue
            self._set.add(candidate)
            bisect.insort(self._words, candidate)
            added += 1
        if added:
            self._index = {word: i for i, word in enumerate(self._words)}
        return added

    # ------------------------------------------------------------------ dunder
    def __len__(self) -> int:
        return len(self._words) if self._words else (len(read_database(self.path)) if
                                                     self.path and pathlib.Path(self.path).is_file()
                                                     else len(FALLBACK_WORDS))

    def __iter__(self):
        return iter(self.load())

    def __repr__(self) -> str:
        return "<UrduEngine %d words (%s) from %s>" % (len(self), self.source,
                                                       pathlib.Path(self.path).name if self.path else "-")


def _is_compact(path: str | os.PathLike[str]) -> bool:
    """Sniff the container without decoding the whole payload."""
    try:
        with gzip.open(path, "rb") as fh:
            return fh.read(len(COMPACT_MAGIC)).decode("utf-8", "ignore") == COMPACT_MAGIC
    except (OSError, EOFError):
        return False


# --------------------------------------------------------------------------- #
# 5. Small CLI - handy for debugging an app, and for benchmarks
# --------------------------------------------------------------------------- #
def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="urduofdani_engine",
                                 description="urduofdani engine - drop-in Urdu dictionary")
    ap.add_argument("--db", default=None, help="database .gz (default: auto-detect)")
    ap.add_argument("--info", action="store_true", help="show database stats")
    ap.add_argument("--bench", action="store_true", help="measure load + query speed")
    ap.add_argument("--check", metavar="WORD", help="is this a dictionary word?")
    ap.add_argument("--suggest", metavar="PREFIX", help="autocomplete a prefix")
    ap.add_argument("--spell", metavar="TEXT", help="list unknown words in TEXT")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--version", action="version", version="urduofdani_engine %s" % __version__)
    args = ap.parse_args(argv)

    engine = UrduEngine(args.db)
    if args.check:
        print("%s  %s" % ("YES" if engine.is_word(args.check) else "NO ", args.check))
        if not engine.is_word(args.check):
            print("   did you mean: %s" % " ".join(engine.correct(args.check)))
        return 0 if engine.is_word(args.check) else 1
    if args.suggest:
        print(" | ".join(engine.suggest(args.suggest, args.limit)))
        return 0
    if args.spell:
        bad = engine.unknown(args.spell)
        print("unknown: %s" % (" ".join(bad) if bad else "(none)"))
        return 1 if bad else 0
    if args.bench:
        fresh = UrduEngine(args.db, lazy=True)
        fresh.load()
        best = min(UrduEngine(args.db, lazy=True).load() is not None and
                   (lambda: (lambda t0: (UrduEngine(args.db, lazy=True).load(),
                                         (time.perf_counter() - t0) * 1000)[1])(time.perf_counter()))()
                   for _ in range(3))
        print("database : %s" % pathlib.Path(fresh.path).name)
        print("words    : %s" % f"{len(fresh):,}")
        print("load     : %.2f ms (best of 3)" % best)
        t0 = time.perf_counter()
        for _ in range(1000):
            "کمپیوٹر" in fresh
        print("lookup   : %.3f ms / query (1000 membership tests)" % ((time.perf_counter() - t0)))
        t0 = time.perf_counter()
        for _ in range(1000):
            fresh.suggest("کمپیو")
        print("suggest  : %.3f ms / query (1000 prefix searches)" % ((time.perf_counter() - t0)))
        return 0

    info = engine.info()
    print("urduofdani_engine %s" % __version__)
    print("  database : %s" % pathlib.Path(info["path"]).name if info["path"] else "  database : (fallback)")
    print("  container: %s" % info["source"])
    print("  words    : %s" % f"{info['words']:,}")
    print("  packed   : %s bytes" % f"{info['packed_bytes']:,}")
    print("  load     : %.3f ms" % info["load_ms"])
    print("  sample   : %s" % " ".join(engine.random_words(8, seed=7)))
    return 0


main = _main          # console-script entry point (pyproject.toml)


if __name__ == "__main__":
    raise SystemExit(_main())
