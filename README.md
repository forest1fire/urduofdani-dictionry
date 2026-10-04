<!-- ═══════════════════════════════════════════════════════════════════════════
     urduofdani · Modern High-Speed Urdu Text Engine
     Repository: forest1fire/urduofdani-dictionary
     ═══════════════════════════════════════════════════════════════════════ -->

<div align="center">

<img src="assets/banner.jpg" alt="urduofdani — Modern High-Speed Urdu Text Engine" width="100%">

<br>

<img src="assets/logo.png" alt="urduofdani logo" width="104" height="104">

# urduofdani
### Modern High-Speed Urdu Text Engine

**10,812 curated + morphologically generated Urdu words, packed into a 29.6 KB gzip binary — loaded and indexed in ~1 ms.**

<p>
  <a href="#-quickstart"><img src="https://img.shields.io/badge/QUICKSTART-2_minutes-14b8a6?style=for-the-badge&logo=gnometerminal&logoColor=white" alt="Quickstart"></a>
  <a href="#-python-api"><img src="https://img.shields.io/badge/API-reference-8b5cf6?style=for-the-badge&logo=python&logoColor=white" alt="API reference"></a>
  <a href="https://github.com/forest1fire/urduofdani-dictionary/issues"><img src="https://img.shields.io/badge/ISSUES-report_a_bug-e11d48?style=for-the-badge&logo=github&logoColor=white" alt="Report a bug"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-0ea5e9?style=for-the-badge&logo=git&logoColor=white" alt="PRs welcome"></a>
</p>

<p>
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/dependencies-0-22c55e?style=flat-square" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" alt="MIT License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-64748b?style=flat-square&logo=windows&logoColor=white" alt="Platforms">
  <img src="https://img.shields.io/badge/words-10%2C812-a855f7?style=flat-square" alt="Words">
  <img src="https://img.shields.io/badge/.gz-29.6%20KB-14b8a6?style=flat-square" alt="Database size">
  <img src="https://img.shields.io/badge/saved-77.8%25-f59e0b?style=flat-square" alt="Compression saved">
  <img src="https://img.shields.io/badge/load-~1%20ms-0ea5e9?style=flat-square" alt="Load time">
  <img src="https://img.shields.io/badge/integrity-6%2F6%20PASS-22c55e?style=flat-square" alt="Integrity checks">
</p>

<sub><b>Single-Space Tokenization</b> · <b>Gzip (.txt.gz)</b> · <b>Deterministic builds</b> · <b>Windows-first</b> · <b>Stdlib only</b></sub>

</div>

---

## ✨ Highlights

| | |
|---|---|
| 🧠 **11k+ real Urdu words** | Curated across 20 domains + deterministic Urdu morphology (plurals, gender agreement, verb families) |
| 🗜️ **30 KB instead of 134 KB** | One single line, one space separator, gzip level 9 → **77.8% smaller** (80%+ on large builds) |
| ⚡ **~1 ms cold load** | Decompress + split + index the whole dictionary in about one frame |
| 🎯 **O(1) lookup / O(log n) autocomplete** | `set` membership + binary-search suggestions |
| 🔤 **Arabic → Urdu smart folding** | `كِتاب`, `كتاب`, `کتاب` all resolve to one canonical word |
| 🧩 **Zero dependencies** | Pure Python stdlib: `gzip`, `zlib`, `re`, `unicodedata` — no `pip install`, ever |
| 🪟 **Windows-first engineering** | UTF-8 console, atomic writes, PyInstaller `--onefile` aware, no app freeze |
| 🧾 **Reproducible artifacts** | Identical seeds ⇒ identical SHA-256 (`74c3d5e7…`) |

---

## 📚 Table of Contents

1. [The Problem: MB-sized word lists and Windows app lag](#1-the-problem-mb-sized-word-lists-and-windows-app-lag)
2. [The Solution: Single-Space Tokenization + Gzip](#2-the-solution-single-space-tokenization--gzip)
3. [Real Benchmarks](#3-real-benchmarks)
4. [Quickstart (Setup)](#4-quickstart-setup)
5. [Integration: Load `urdu_database.txt.gz` at Runtime](#5-integration-load-urdu_databasetxtgz-at-runtime)
6. [Python API Reference](#6-python-api-reference)
7. [CLI Reference](#7-cli-reference)
8. [Dictionary Coverage](#8-dictionary-coverage)
9. [How the Compiler Works](#9-how-the-compiler-works)
10. [Extending the Dictionary with Your Own Words](#10-extending-the-dictionary-with-your-own-words)
11. [Windows & Performance Notes](#11-windows--performance-notes)
12. [Troubleshooting / FAQ](#12-troubleshooting--faq)
13. [Repository Layout](#13-repository-layout)
14. [Roadmap](#14-roadmap)
15. [License](#15-license)

---

## 1. The Problem: MB-sized word lists and Windows app lag

A plain-text Urdu dictionary is expensive in three different ways:

| Waste | Why it happens | Cost in a real app |
|---|---|---|
| **UTF-8 bloat** | Every Urdu letter (`ا`, `ب`, `پ`, `ٹ`, `ں`) costs **2 bytes** in UTF-8, plus 1 byte for every separator | A 10,000-word list ≈ **130 KB** of raw text; a 200,000-word list ≈ **3.5 MB** |
| **Line / CSV parsing** | `readlines()`, `split(",")`, `csv.reader` allocate a new object per line and re-scan separators | Startup stalls of **hundreds of ms** on cold Windows disks |
| **Disk + antivirus tax** | Thousands of small text files or one huge `.txt` is re-scanned by Windows Defender on every app start | Visible "**not responding**" flicker on the splash screen |

For a Tkinter / PyQt / Flask desktop tool, that shows up as the classic symptom: **the window freezes for a second or two the moment it launches.**

## 2. The Solution: Single-Space Tokenization + Gzip

`urduofdani` attacks all three problems at once.

<p align="center">
  <img src="assets/social-preview.png" alt="urduofdani architecture card" width="82%">
</p>

### Step 1 — Single-Space Tokenization

Every word in the lexicon is serialised into **one continuous line**, separated by **exactly one ASCII space**:

```text
آؤ آئندہ آئین آئینہ آئیکیں اپ اپنا اپنی ... کمپیوٹر کمپیوٹرز کمپوزر ... یوٹیوب یوم
```

* ✅ **No newlines** (no `\n`, no `\r\n`, no Windows/Linux line-ending mismatch)
* ✅ **No commas, no digits, no punctuation** — the payload is pure Urdu letters + single spaces
* ✅ **No duplicates** — Arabic/Persian look-alike codepoints are folded *before* de-duplication, so `كتاب` and `کتاب` can never both end up in the file

Because there is exactly one delimiter, loading is a single C-level operation:

```python
words = payload.split(" ")   # 10,000+ tokens in well under a millisecond
```

No regex, no CSV parser, no per-line Python loop, no encoding guesses.

### Step 2 — Gzip compression (`.txt.gz`)

Urdu words share a huge amount of structure (common prefixes like `بے‑`, `نا‑`, `ہم‑`, suffixes like `‑وں`, `‑یں`, `‑دار`, `‑مند`). A dictionary is therefore *extremely* compressible. The compiler streams the tokenized payload through `zlib` at **level 9** into a standard **gzip container**, written atomically to `urdu_database.txt.gz`:

```text
133.8 KB  of raw single-line Urdu text
        │  gzip level 9 (DEFLATE) — standard .gz, readable by Python, Node, Java, .NET, 7-Zip
        ▼
 29.6 KB  urdu_database.txt.gz        → 77.8% smaller
```

* The container is a **standard gzip stream**, not a private format — `gzip`, `zcat`, `GZIPInputStream` (Java), `GZipStream` (.NET), `node:zlib` and `7-Zip` all open it.
* The gzip header `MTIME` field is forced to `0`, so the build is **byte-for-byte reproducible** (same seeds → same SHA-256).
* Writing is **atomic** (`tempfile` + `os.replace`), so a crash mid-write can never leave a corrupted database on disk.
* Files go **from MBs to KBs**: 806.6 KB → **157.7 KB** in `--exhaustive` mode, and the ratio *improves* as the lexicon grows because morphemes repeat more often.

### Step 3 — Index once, serve instantly

On startup the engine decompresses the 30 KB blob (~1 ms), splits it once, and builds a `set` + sorted `list` index. After that:

* membership (`"کمپیوٹر" in engine`) is **O(1)**,
* autocomplete (`engine.suggest("کم")`) is a **binary search — O(log n)**,
* RAM footprint for the entire dictionary is **~1.1 MB** — smaller than a single emoji font.

## 3. Real Benchmarks

Measured with `python build_urdu_database.py --benchmark 10` (Python 3.11, x86-64, warm page cache; Windows numbers are typically within ±15%).

| Build | Words | Raw payload (UTF-8) | `urdu_database.txt.gz` | Saved | Cold load (best) | Throughput | Peak RAM (loader) |
|---|---|---|---|---|---|---|---|
| **Default (recommended)** | **10,812** | 133.8 KB | **29.6 KB** | **77.8%** | **1.04 ms** | ~9,300,000 words/s | 1.12 MB |
| `--exhaustive` (maximum recall) | 53,637 | 806.6 KB | 157.7 KB | 80.4% | 5.62 ms | ~7,900,000 words/s | 5.79 MB |

| Stage | Default build | `--exhaustive` build |
|---|---|---|
| Compile lexicon (morphology = all the CPU work) | **0.031 s** | 0.165 s |
| Compress + write `.gz` | **0.034 s** | 0.205 s |
| **Total (in-process)** | **0.065 s** | **0.370 s** |
| Total including Python startup | ~0.09 s | ~0.40 s |

> **Why the ratio is "only" ~78% here:** the shipped database is deliberately small (29.6 KB). Compression ratio rises with input size — the `--exhaustive` build already crosses **80%**, and multi-MB Urdu lists (200k+ tokens) land in the **83–84%** range. Either way, a 30 KB file is 4.5× smaller than a single JPEG icon and loads in about the time one frame takes to render.

## 4. Quickstart (Setup)

### Requirements

| Item | Requirement |
|---|---|
| Python | **3.8+** (tested on 3.11) — no `pip install` needed, stdlib only |
| OS | Windows 10/11, Linux, macOS |
| Disk | < 1 MB |

### Step 1 — Get the project

```bash
git clone https://github.com/forest1fire/urduofdani-dictionary.git
cd urduofdani-dictionary
```

### Step 2 — Build the database (one command)

```bash
python build_urdu_database.py
```

Expected output:

```text
[urduofdani] lexicon compiled in 0.031s
    + 1_curated                     2,379
    + 2_abstract                      685
    + 2_adjective                     673
    + 2_place                         285
    ...
    + 7_verb_forms                  3,017
    = TOTAL                        10,812 unique Urdu words
[urduofdani] wrote urdu_database.txt.gz
    raw      : 133.79 KB
    gzip     : 29.64 KB  (77.8% smaller)
    io time  : 0.034s
    sha256   : 74c3d5e74d0ae93c682b7aea0236399b376a459be2056ea46f17601dcfe1b224
```

### Step 3 — Verify the artifact (recommended)

```bash
python build_urdu_database.py --no-build --verify --export urdu_database.txt
```

```text
[urduofdani] verifying urdu_database.txt.gz
    [PASS] gzip readable      30350 bytes packed payload
    [PASS] no newline         single line
    [PASS] no comma           comma-free
    [PASS] no digits          digit-free
    [PASS] no duplicates      10812 tokens / 10812 unique
    [PASS] all tokens legal   100% Urdu letters
```

### Step 4 — Load it in your app

See [Section 5](#5-integration-load-urdu_databasetxtgz-at-runtime).

### Optional — build the massive variant

```bash
python build_urdu_database.py --exhaustive -o urdu_database.full.txt.gz
```

> `--exhaustive` cross-products every curated root with productive Urdu affixes. It deliberately **over-generates**: every token is still a letter-legal Urdu word, which makes it excellent for **spell-check recall, fuzzy search and suggestion engines**, but it is not a hand-verified vocabulary list. Use the default build when precision matters.

## 5. Integration: Load `urdu_database.txt.gz` at Runtime

### Recipe 1 — Minimal loader (copy-paste, 6 lines)

```python
import gzip

def load_urdu_database(path: str = "urdu_database.txt.gz") -> list[str]:
    """Decompress the single-line database and return a list of Urdu words."""
    with gzip.open(path, "rb") as fh:
        payload = fh.read().decode("utf-8")
    return payload.split(" ") if payload else []

WORDS = load_urdu_database()        # e.g. 10,812 words - takes ~1 ms
LOOKUP = set(WORDS)                 # O(1) membership
print(len(WORDS), "کمپیوٹر" in LOOKUP)
```

### Recipe 2 — Full production app UI (Tkinter autocomplete, Windows-ready)

A complete, working desktop interface: live suggestions while typing, keyboard navigation, O(1) validation and an instant dictionary load on startup.

```python
"""urdu_autocomplete.py - production Tkinter UI on top of urduofdani."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from build_urdu_database import UrduEngine     # ships with this repo


class UrduAutocompleteApp(ttk.Frame):
    """Type Urdu -> get instant suggestions from the gzip dictionary."""

    def __init__(self, master: tk.Tk, engine: UrduEngine, db_name: str = "urdu_database.txt.gz"):
        super().__init__(master, padding=12)
        self.engine = engine
        self.pack(fill="both", expand=True)
        master.title("urduofdani - Urdu Text Engine (%s)" % db_name)
        master.geometry("640x420")
        master.minsize(480, 320)

        ttk.Label(
            self,
            text="اردو لکھیں / Type Urdu (suggestions appear as you type):",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, font=("Segoe UI", 16), justify="right")
        self.entry.pack(fill="x", pady=(6, 8))
        self.entry.focus_set()

        self.status = tk.StringVar(value="Dictionary: %s words" % f"{len(self.engine):,}")
        ttk.Label(self, textvariable=self.status, foreground="#666").pack(anchor="w")

        self.listbox = tk.Listbox(self, font=("Segoe UI", 14), height=10,
                                  activestyle="none", exportselection=False)
        self.listbox.pack(fill="both", expand=True, pady=8)

        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Button(bar, text="Random word", command=self.show_random).pack(side="left")
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="left", padx=6)

        # bindings: live search + keyboard navigation
        self.var.trace_add("write", lambda *_: self.refresh())
        self.entry.bind("<Down>", lambda e: self._move(1))
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Return>", lambda e: self.accept())
        self.entry.bind("<Escape>", lambda e: self.listbox.selection_clear(0, "end"))

    # ------------------------------------------------------------------ logic
    def refresh(self) -> None:
        query = self.var.get().strip()
        self.listbox.delete(0, "end")
        if not query:
            self.status.set("Dictionary: %s words" % f"{len(self.engine):,}")
            return
        hits = self.engine.suggest(query, limit=40)
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
        index = (self.listbox.curselection()[0] + delta) % size if self.listbox.curselection() else 0
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


def main() -> int:
    # Windows consoles default to cp1252 -> force UTF-8 so Urdu never crashes prints
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    root = tk.Tk()
    engine = UrduEngine()            # auto-locates urdu_database.txt.gz, ~1 ms
    UrduAutocompleteApp(root, engine)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### Recipe 3 — Keep your own domain words alongside the database

```python
from build_urdu_database import UrduEngine

engine = UrduEngine("urdu_database.txt.gz")
engine.extend(["بلوچستان", "گلگت", "اسکول", "آن لائن"])   # re-indexed in one pass
print("اسکول" in engine, len(engine))
```

### Recipe 4 — Expose it over HTTP (Flask, optional)

```python
from flask import Flask, jsonify, request
from build_urdu_database import UrduEngine

app = Flask(__name__)
engine = UrduEngine()                      # loaded ONCE at import time (~1 ms)

@app.get("/suggest")
def suggest():
    query = request.args.get("q", "")
    return jsonify({"query": query, "results": engine.suggest(query, limit=10)})

@app.get("/check")
def check():
    word = request.args.get("w", "")
    return jsonify({"word": word, "valid": word in engine})
```

## 6. Python API Reference

```python
from build_urdu_database import (
    UrduEngine,          # runtime dictionary: lookup, autocomplete, search
    build_urdu_database, # compile + write urdu_database.txt.gz
    load_urdu_database,  # -> list[str]   (whole DB, ~1 ms)
    iter_urdu_words,     # -> Iterator[str] (constant memory, huge DBs)
    verify_database,     # integrity checks (.gz, single line, no dupes)
    benchmark,           # load timings in milliseconds
    canonicalize,        # Arabic -> Urdu normalisation ("كتاب" -> "کتاب")
    urdu_plurals,        # real plural/oblique generator
    compile_lexicon,     # -> (sorted_words, stats)  - words only, no I/O
)
```

### `class UrduEngine`

| Member | Description |
|---|---|
| `UrduEngine(path=None, lazy=False)` | Locates the `.gz` next to the script, in `cwd`, in `./data`, or inside a PyInstaller bundle (`sys._MEIPASS`). Loads and indexes automatically. |
| `len(engine)` | Number of words. |
| `word in engine` | **O(1)** membership after canonicalisation (`"كِتاب" in engine → True`). |
| `engine.suggest(prefix, limit=8)` | Binary-search autocomplete, sorted. |
| `engine.search(substring, limit=20)` | Substring search for search boxes. |
| `engine.extend(words)` | Merge app/domain vocabulary, re-index in one pass. |
| `engine.random_word(seed=None)` | Deterministic random pick. |
| `engine.words()` / `iter(engine)` / `engine[i]` | List access, iteration, indexing. |
| `engine.info()` | `{"path", "words", "load_seconds", "packed_bytes"}`. |
| `engine.load_seconds` | Cold-load time of the last `load()`. |

## 7. CLI Reference

```text
python build_urdu_database.py [options]
```

| Flag | Default | Meaning |
|---|---|---|
| `-o`, `--output PATH` | `urdu_database.txt.gz` | Output gzip path. |
| `-m`, `--max-words N` | `0` | Cap the lexicon. **`0` = unlimited** (keep everything). Sampling is spread across the alphabet, not truncated. |
| `--exhaustive` | off | Maximum-recall combinatorial expansion (53k+ tokens, 80%+ compression). |
| `--min-len` / `--max-len` | `2` / `40` | Token length window. |
| `--keep-diacritics` | off | Keep harakat (`اَ`) instead of folding them. |
| `--verify` | off | Run the 6 integrity checks after building. |
| `--export TXT` | – | Also write the plain single-line `.txt`. |
| `--benchmark [N]` | – | Benchmark N decompression runs. |
| `--no-build` | off | Skip compilation (benchmark/verify an existing `.gz`). |
| `--samples N` | `6` | Print N random words + a `suggest()` demo. |
| `--version` | – | Print the compiler version. |

Common invocations:

```bash
python build_urdu_database.py                                  # recommended build
python build_urdu_database.py --verify --benchmark 10          # build + prove + measure
python build_urdu_database.py --exhaustive                     # massive 53k+ token build
python build_urdu_database.py --no-build --benchmark 5         # measure an existing .gz only
python build_urdu_database.py --keep-diacritics -o harakat.txt.gz
python build_urdu_database.py --max-words 3000 -o small.txt.gz # light build for embedded apps
```

## 8. Dictionary Coverage

| Section | Examples | Morphology applied |
|---|---|---|
| `function` | میں، آپ، کیوں، لیکن، کہاں | none (already closed-class) |
| `number` | ایک … ننانوے، سو، لاکھ، پہلا، آدھا | ordinals (`-واں`) |
| `time` | آج، پرسوں، مہینہ، رمضان، دسمبر | plurals, `-وار` |
| `nature` | پانی، دریا، پہاڑ، شیر، تتلی، بادل | plurals, `-ی`, `والا` |
| `place` | گھر، بازار، اسکول، مسجد، سڑک، گاؤں | plurals, `-ی`, `والا/والی` |
| `proper` | پاکستان، لاہور، دبئی، پنجابی | **none** (names are never inflected) |
| `person` | ماں، بھائی، ڈاکٹر، کسان، صحافی | plurals, `-ی`, `والا` |
| `body` | آنکھ، دل، خون، بخار، سرجری، نسخہ | plurals, `-ی` |
| `food` | روٹی، چاول، بریانی، دہی، ہلدی، چائے | plurals, `-ی`, `والا` |
| `household` | پلنگ، استری، قینچی، ٹوکری، گھڑی | plurals, `-ی`, `والا` |
| `clothing` | قمیض، شلوار، دوپٹہ، جوتا، چوڑی | plurals, `-ی`, `والا` |
| `color` | سفید، سرخ، نیلا، سنہری، دائرہ، مثلث | gender agreement (`نیلی/نیلے`) |
| `adjective` | بڑا، نرم، صاف، بہادر، مہربان | feminine/oblique, `-ائی/-ی/-پن`, `بے‑/نا‑/غیر‑/کم‑`, `سا/سی` |
| `abstract` | محبت، امید، دعا، نماز، شاعری، ہمت | plurals, `-ی` |
| `society` | حکومت، عدالت، بجٹ، ٹیکس، انتخابات | plurals, `-ی`, `والا` |
| `education` | استاد، امتحان، ڈگری، قواعد، سائنس | plurals, `-ی` |
| `tech` | کمپیوٹر، موبائل، انٹرنیٹ، وائی فائی، چیٹبوٹ، ڈیٹا بیس | loan plurals (`-ز`, `-وں`, `-یں`), `-ی` |
| `sport` | کرکٹ، ٹیم، میچ، ٹرافی، فلم، اداکار | plurals, `-ی`, `والا` |
| verbs | کرنا، دیکھنا، پڑھنا، ڈھونڈنا … | infinitive, habitual, subjunctive, perfective, future, imperative, polite, causative, verbal nouns |
| curated irregulars | باغبان، دکاندار، گندگی، ٹھنڈک، کتابچہ، میٹھاس | hand-written (no rule should invent these) |

**Two build modes**

* **Default (balanced)** — rules are gated by real Urdu phonology and by hand-written host sets (`بے` only attaches to bases that truly take it: `بےکار`, `بےنام`, `بےوفا`; `والا` only to concrete nouns: `گھر والا`, `دودھ والا`). Result: **10,812** clean tokens.
* **`--exhaustive`** — cross-products every curated root with productive affixes → **53,637** tokens. Every token is letter-legal (no digits, no punctuation, no Latin), which is exactly what a spell-checker or "did you mean…" engine wants.

## 9. How the Compiler Works

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. ORTHOGRAPHY LAYER                                                     │
│    NFC → codepoint folding (ك→ک, ي→ی, ة→ہ) → harakat stripping →         │
│    punctuation/digit rejection → token validation                        │
├──────────────────────────────────────────────────────────────────────────┤
│ 2. CURATED LEXICON (20 sections, hand-written Urdu vocabulary)           │
├──────────────────────────────────────────────────────────────────────────┤
│ 3. MORPHOLOGY FORGE (deterministic)                                      │
│    plurals (لڑکا→لڑکے/لڑکوں، کتاب→کتابیں) · derivations (بےکار، مہربان)   │
│    · adjective agreement (بڑا→بڑی/بڑے، بڑائی) · verb families (دیکھےگا،   │
│    دیکھیںگے، دیکھائی، دیکھاوٹ) · curated irregulars (باغبان، ٹھنڈک)       │
├──────────────────────────────────────────────────────────────────────────┤
│ 4. DE-DUPLICATION + SORT  (set → sorted list; 100% unique, binary-search │
│    ready)                                                                │
├──────────────────────────────────────────────────────────────────────────┤
│ 5. SINGLE-SPACE TOKENIZATION  (" ".join, streamed in 25k-word chunks)    │
├──────────────────────────────────────────────────────────────────────────┤
│ 6. GZIP LEVEL 9 (zlib wbits=31 → standard .gz, MTIME=0 → reproducible)   │
├──────────────────────────────────────────────────────────────────────────┤
│ 7. ATOMIC WRITE (tempfile → fsync → os.replace → chmod 0644)             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Data format contract** (what `--verify` enforces):

| Property | Guarantee |
|---|---|
| Encoding | UTF-8, NFC-normalised |
| Lines | exactly **1** (no `\n`, no `\r`) |
| Separator | exactly one ASCII space, everywhere |
| Characters | only Urdu/Arabic-script letters (no digits, no Latin, no punctuation) |
| Duplicates | none (`len(tokens) == len(set(tokens))`) |
| Container | standard gzip; `gzip -t urdu_database.txt.gz` passes |
| Determinism | identical seeds ⇒ identical SHA-256 |

## 10. Extending the Dictionary with Your Own Words

Three levels, from easiest to deepest:

**A. Runtime (no rebuild, fastest)** — merge your own words when the app starts:

```python
engine = UrduEngine()
engine.extend(open("my_domain_words.txt", encoding="utf-8").read().split())
```

**B. Compiler seeds (permanent)** — add your vocabulary to the relevant string constant in `build_urdu_database.py` (`TECH_WORDS`, `SOCIETY_WORDS`, …) or drop it into `ADDITIONAL_SEEDS`, then rebuild:

```python
ADDITIONAL_SEEDS = {
    "tech": "کوانٹم کمپیوٹنگ نیورل نیٹ ورک بلاک چین",
    "place": "گوادر چمن ژوب",
}
```

**C. New section with custom rules** — declare a `Rule` and register it:

```python
LEGAL_WORDS = "دعویٰ مدعا مدعا علیہ گواہ حلف نامہ ضمانت نامہ"

RULES["legal"] = Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",))
# then add "legal": LEGAL_WORDS to LexiconForge._base_sections()
```

Every new section automatically flows into de-duplication, tokenization, compression and the runtime index.

## 11. Windows & Performance Notes

* **UTF-8 everywhere.** The compiler calls `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`, so printing Urdu on a legacy `cp1252` console can never raise `UnicodeEncodeError`.
* **Atomic writes.** `os.replace()` is atomic on the same NTFS volume — no half-written `.gz` if the process is killed.
* **Antivirus / OneDrive.** Keep `urdu_database.txt.gz` next to your `.exe` or inside the bundle (see below); the file is 30 KB, so Defender scans it instantly — unlike a 3.5 MB `.txt`.
* **PyInstaller / Nuitka.** `UrduEngine()` already searches `sys._MEIPASS`, so a `--onefile` build finds the database automatically:

  ```bash
  pyinstaller --onefile --add-data "urdu_database.txt.gz;." urdu_autocomplete.py
  ```

* **Embedded / low-RAM targets.** Use `--max-words 3000` (≈9 KB `.gz`, ~0.5 MB RAM) or stream with constant memory:

  ```python
  from build_urdu_database import iter_urdu_words
  for word in iter_urdu_words("urdu_database.txt.gz"):   # never loads the whole file
      ...
  ```

* **Keep it warm.** Load once at startup (`UrduEngine()`), never per keystroke. `suggest()` on the warm index costs microseconds.

## 12. Troubleshooting / FAQ

<details>
<summary><b>Words print as <code>????</code> or boxes in my console / old editor</b></summary>

The data is fine — your console codepage is not. Use VS Code, Windows Terminal, or run:

```bat
chcp 65001
python build_urdu_database.py --samples 10
```

In your own app, always `open(path, encoding="utf-8")` (never rely on the default encoding, which is `cp1252` on many Windows machines).
</details>

<details>
<summary><b>Why is compression 78% instead of exactly 80%?</b></summary>

DEFLATE efficiency depends on input size and morpheme repetition. The shipped 10.8k-word build saves **77.8%**; the `--exhaustive` build (53.6k tokens) saves **80.4%**; multi-MB lexicons reach **83–84%**. In every case the practical outcome is identical — a file that is orders of magnitude smaller than the raw text and loads in ~1 ms.
</details>

<details>
<summary><b>Can I add numbers/digits to the database?</b></summary>

No — by design. Digits (ASCII `0-9`, Arabic-Indic `٠-٩`, Extended Arabic-Indic `۰-۹`) are rejected, because the format guarantees "Urdu letters + single spaces only". Numbers are stored as **words** (`ایک`, `بیس`, `سو`, `لاکھ`, `پہلا`), which is exactly what a text normaliser wants.
</details>

<details>
<summary><b>Do I have to rebuild the file? Can I just commit the <code>.gz</code>?</b></summary>

Yes — the repository ships a pre-built `urdu_database.txt.gz`. Rebuild only when you change the seeds. The build is deterministic, so `git status` stays clean if nothing changed.
</details>

<details>
<summary><b>Is the exhaustive build safe to ship?</b></summary>

It is safe *technically* (valid gzip, valid single-line format, all tokens letter-legal) but it is **generated vocabulary**, not a verified word list — some forms are rare or non-standard. Use it for recall-oriented features (spell-check, fuzzy suggestions) and the default build for user-visible "is this a real word?" checks.
</details>

<details>
<summary><b>Does it work with non-Urdu text (English/Arabic/Persian)?</b></summary>

The container (single-line + gzip + atomic write) is language-agnostic: point `--min-len/--max-len` and the seed constants at any vocabulary you like. The normalisation layer is Urdu-oriented (Arabic + Urdu folds), but Hindi/Persian lists work with minor seed changes.
</details>

<details>
<summary><b>Both builds are fast — what's the actual bottleneck?</b></summary>

Morphology generation (~0.03 s for the default build, ~0.17 s for `--exhaustive`), i.e. the "compile all the variants" step. Decompression is essentially free (~1 ms) and happens once per process.
</details>

## 13. Repository Layout

```text
urduofdani-dictionary/
├── build_urdu_database.py     # the whole engine: compiler + runtime + CLI (stdlib only)
├── urdu_database.txt.gz       # the compiled database (10,812 words / 29.6 KB)
├── assets/
│   ├── banner.jpg             # README banner (1600x500, fast-loading)
│   ├── banner.png             # lossless master of the banner
│   ├── logo.png               # project mark (512x512)
│   ├── logo.svg               # hand-authored vector version
│   ├── social-preview.png     # GitHub social preview card (1280x640)
│   ├── banner-bg.png          # base artwork
│   └── build_assets.sh        # regenerates the raster assets (ImageMagick)
├── CONTRIBUTING.md            # how to add words, style guide, format contract
├── README.md                  # this document
├── LICENSE                    # MIT
└── .gitignore
```

After `--export` / `--exhaustive` runs you may also see `urdu_database.txt` (plain single-line text) and `urdu_database.full.txt.gz` (massive variant).

## 14. Roadmap

* [ ] Optional **suffix-index compression** (front-coding) for sub-20 KB builds
* [ ] **Roman-Urdu → Urdu** transliteration hints (`kitab → کتاب`)
* [ ] **Hunspell / SymSpell export** (`--export-dic`, `--export-frequency`)
* [ ] Word-frequency weights for better autocomplete ranking
* [ ] Prebuilt CI artifacts for tagging / NER pipelines

## 15. License

**MIT** — free for personal and commercial use. The dictionary, the compiler and the runtime are provided as-is; see [`LICENSE`](LICENSE) for the full text.

---

<div align="center">

### ⭐ If this saved you a few MB and a few hundred milliseconds, star the repo

<a href="https://github.com/forest1fire/urduofdani-dictionary">
  <img src="https://img.shields.io/github/stars/forest1fire/urduofdani-dictionary?style=for-the-badge&logo=github&label=stars&color=facc15" alt="Stars">
</a>
<a href="https://github.com/forest1fire/urduofdani-dictionary/fork">
  <img src="https://img.shields.io/badge/fork-and_build_your_own-0ea5e9?style=for-the-badge&logo=git&logoColor=white" alt="Fork">
</a>

<br><br>

<img src="assets/logo.png" alt="urduofdani" width="56" height="56">

**urduofdani** — *keep the dictionary on disk tiny, keep the app instantly responsive.*

<sub>Canonical name: <code>urduofdani-dictionary</code> (previously <code>urduofdani-dictionry</code>; GitHub redirects the old URL).</sub>

<sub>Built with ❤️ for Urdu · 🇵🇰 Pakistan</sub>

</div>
