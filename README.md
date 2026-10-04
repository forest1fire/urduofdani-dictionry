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

**15,848 audited Urdu words in a 43.9 KB gzip binary (~2.0 ms load) — every single token checked by a word audit that finds structural violations across the whole lexicon — including the 99 names of Allah, the prophets, Ahl al-Bayt and the Sahaba. Compact tier: the same words in 16.8 KB. Machine tier: 2,592,831 tokens. No cap, no dependencies, no lag.**

<p>
  <a href="#4-quickstart-setup"><img src="https://img.shields.io/badge/QUICKSTART-2_minutes-14b8a6?style=for-the-badge&logo=gnometerminal&logoColor=white" alt="Quickstart"></a>
  <a href="#6-python-api-reference"><img src="https://img.shields.io/badge/API-reference-8b5cf6?style=for-the-badge&logo=python&logoColor=white" alt="API reference"></a>
  <a href="https://github.com/forest1fire/urduofdani-dictionary/issues"><img src="https://img.shields.io/badge/ISSUES-report_a_bug-e11d48?style=for-the-badge&logo=github&logoColor=white" alt="Report a bug"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-0ea5e9?style=for-the-badge&logo=git&logoColor=white" alt="PRs welcome"></a>
</p>

<p>
  <a href="https://github.com/forest1fire/urduofdani-dictionary/actions/workflows/ci.yml"><img src="https://github.com/forest1fire/urduofdani-dictionary/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/dependencies-0-22c55e?style=flat-square" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" alt="MIT License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-64748b?style=flat-square&logo=windows&logoColor=white" alt="Platforms">
  <img src="https://img.shields.io/badge/words-25%2C320-a855f7?style=flat-square" alt="Words">
  <img src="https://img.shields.io/badge/.gz-73.0%20KB-14b8a6?style=flat-square" alt="Database size">
  <img src="https://img.shields.io/badge/saved-79.5%25-f59e0b?style=flat-square" alt="Compression saved">
  <img src="https://img.shields.io/badge/load-~2.9%20ms-0ea5e9?style=flat-square" alt="Load time">
  <img src="https://img.shields.io/badge/integrity-8%2F8%20PASS-22c55e?style=flat-square" alt="Integrity checks">
  <img src="https://img.shields.io/badge/sacred%20names-373%20protected-10b981?style=flat-square&logo=readthedocs&logoColor=white" alt="Sacred names protected">
  <img src="https://img.shields.io/badge/unlimited-25k%E2%86%92116k%E2%86%922.6M-8b5cf6?style=flat-square" alt="Unlimited mode">
</p>

<sub><b>Single-Space Tokenization</b> · <b>Gzip (.txt.gz)</b> · <b>Deterministic builds</b> · <b>Windows-first</b> · <b>Stdlib only</b></sub>

</div>

---

## ✨ Highlights

| | |
|---|---|
| 🧠 **15,848 audited Urdu words** | Curated across 34 domains + deterministic Urdu morphology (plurals, gender agreement, verb families, agentives, compounds) — audit: **0 structural violations, 0 junk classes** |
| 🗜️ **43.9 KB instead of 107.8 KB** | One line, one space separator, gzip level 9 → **59.3% smaller**; the front-coded `compact` tier packs the same 15,848 words into **16.8 KB** |
| ⚡ **~2.0 ms cold load** | Decompress + split + index 15,848 words in about one frame (6.5 ms for the compact tier) |
| 🎯 **O(1) lookup / O(log n) autocomplete** | `set` membership + binary-search suggestions |
| 🔤 **Arabic → Urdu smart folding** | `كِتاب`, `كتاب`, `کتاب` all resolve to one canonical word |
| 🧩 **Zero dependencies** | Pure Python stdlib: `gzip`, `zlib`, `re`, `unicodedata` — no `pip install`, ever |
| 🪟 **Windows-first engineering** | UTF-8 console, atomic writes, PyInstaller `--onefile` aware, no app freeze |
| 🔬 **Word-audited** | `python tools/audit_words.py` checks every token (structural rules + regression lists) — the build fails if junk ever returns |
| 🧾 **Reproducible artifacts** | Identical seeds ⇒ identical SHA-256 (verified in CI) |
| 🧪 **Tested** | `python run_tests.py` → 63 tests covering orthography, morphology, sacred-name safety, the word audit, the build, the engine and the CLI |
| 🖥️ **One front door** | `python urduofdani.py info/build/verify/bench/search/check/suggest/export/random/test/modes` |
| 🚀 **Unlimited mode** | `--mode full` = 17,539 audited words; `--mode recall` = 2,592,831 tokens (machine tier) |
| 🕌 **373 sacred names, protected** | The 99 names of Allah, the prophets, Ahl al-Bayt (including Hazrat Ali's family) and the Sahaba — **never pluralised, suffixed or compounded**, in any mode |

---

## 📚 Table of Contents

1. [The Problem: MB-sized word lists and Windows app lag](#1-the-problem-mb-sized-word-lists-and-windows-app-lag)
2. [The Solution: Single-Space Tokenization + Gzip](#2-the-solution-single-space-tokenization--gzip)
3. [Real Benchmarks](#3-real-benchmarks)
3b. [The Word Audit](#3b-the-word-audit-every-token-checked)
4. [Quickstart (Setup)](#4-quickstart-setup)
5. [Integration: Load `urdu_database.txt.gz` at Runtime](#5-integration-load-urdu_databasetxtgz-at-runtime)
6. [Python API Reference](#6-python-api-reference)
7. [CLI Reference](#7-cli-reference)
7b. [The Front Door: `urduofdani.py`](#7b-the-front-door-urduofdanipy)
7c. [Tests, Examples & Tools](#7c-tests-examples--tools)
8. [Dictionary Coverage](#8-dictionary-coverage)
8b. [Sacred Names (Protected)](#sacred-names-protected)
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
| **UTF-8 bloat** | Every Urdu letter (`ا`, `ب`, `پ`, `ٹ`, `ں`) costs **2 bytes** in UTF-8, plus 1 byte for every separator | This 15,848-word lexicon is **107.8 KB** of raw text; the machine tier is **34.6 MB** |
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
356.1 KB  of raw single-line Urdu text
        │  gzip level 9 (DEFLATE) — standard .gz, readable by Python, Node, Java, .NET, 7-Zip
        ▼
 43.9 KB  urdu_database.txt.gz        → 59.3% smaller
```

* The container is a **standard gzip stream**, not a private format — `gzip`, `zcat`, `GZIPInputStream` (Java), `GZipStream` (.NET), `node:zlib` and `7-Zip` all open it.
* The gzip header `MTIME` field is forced to `0`, so the build is **byte-for-byte reproducible** (same seeds → same SHA-256).
* Writing is **atomic** (`tempfile` + `os.replace`), so a crash mid-write can never leave a corrupted database on disk.
* Files go **from MBs to KBs**: the depth-4 full build turns **121.2 KB → 48.1 KB (60.3%)**, and the front-coded compact tier reaches **16.8 KB (84.4%)**, and the ratio *improves* as the lexicon grows because morphemes repeat more often.

### Step 3 — Index once, serve instantly

On startup the engine decompresses the 44 KB blob (~2.0 ms; compact tier: 16.8 KB / 6.5 ms), splits it once, and builds a `set` + sorted `list` index. After that:

* membership (`"کمپیوٹر" in engine`) is **O(1)**,
* autocomplete (`engine.suggest("کم")`) is a **binary search — O(log n)**,
* RAM footprint for the whole dictionary is **~2.7 MB** — smaller than one emoji font.

## 3. Real Benchmarks

Measured on this repository's machine with `python tools/measure_tiers.py` (Python 3.11, x86-64, warm page cache; Windows numbers are typically within ±15%). Every row below is regenerated by that one command — run it yourself, or `--check README.md` to prove the table is not stale.

| tier | words | `.gz` size | saved | cold load | build |
|---|---:|---:|---:|---:|---:|
| `--mode mini` | 3,000 | 11.36 KB | 44.3% | 0.62 ms | 0.21 s |
| `--mode default` | 15,848 | 43.90 KB | 59.3% | 1.98 ms | 0.11 s |
| `--mode exhaustive` | 16,243 | 45.05 KB | 59.4% | 2.61 ms | 0.15 s |
| `--mode wide` | 16,875 | 46.72 KB | 59.6% | 2.61 ms | 0.18 s |
| `--mode full` | 17,539 | 48.13 KB | 60.3% | 2.16 ms | 0.22 s |
| `--mode recall` | 2,592,831 | 7.00 MB | 79.3% | 512.30 ms | 33.6 s |

| Shipped artifact | Words | Raw payload (UTF-8) | Committed `.gz` | Saved | Cold load (best) | Peak RAM (loader) |
|---|---|---|---|---|---|---|
| `urdu_database.txt.gz` (default) | **15,848** | 107.8 KB | **43.9 KB** | **59.3%** | **2.0 ms** | 1.64 MB |
| `urdu_database.compact.gz` (front-coded) | **15,848** | 107.8 KB | **16.8 KB** | **84.4%** | 6.5 ms | 2.1 MB |
| `urdu_database.full.txt.gz` (`--mode full`) | **17,539** | 121.2 KB | **48.1 KB** | **60.3%** | 2.2 ms | 1.83 MB |
| `urdu_database.full.compact.gz` (front-coded) | **17,539** | 121.2 KB | **18.0 KB** | **85.1%** | 7.4 ms | 2.3 MB |

| Stage | Default (15.8k) | Full (17.5k) | Recall (2.6M) |
|---|---|---|---|
| Compile lexicon (morphology = all the CPU work) | **0.11 s** | 0.15 s | ~28 s |
| Compress + write `.gz` | **0.05 s** | 0.07 s | ~5 s |
| **Total (in-process)** | **0.16 s** | **0.22 s** | ~33 s |
| Total including Python startup | ~0.25 s | ~1.03 s | — |

> **Memory note.** The builder holds the lexicon in RAM while de-duplicating and
> sorting, so peak RSS scales with the token count: ~120 MB for 116k words,
> ~500 MB for the 2.6M-token recall tier. The shipped builds stay far below that.

> **Why the ratio tracks quality:** DEFLATE pays off with repetition, and a
> clean lexicon repeats far less than a noisy one — the audited default build
> saves **59.3%**, while the *front-coded* compact tier reaches **84.4%** on the
> same 15,848 words and the 2.6M-token recall tier saves **79.3%**. 16.8 KB–43.9 KB
> is smaller than one JPEG icon, and it loads in about the time one frame takes to
> render.

## 3b. The Word Audit: every token checked

Big word lists are easy; *correct* word lists are not. Earlier builds were larger
because the generator glued morphemes together blindly. `tools/audit_words.py`
now reads **every token of a shipped tier** and fails the build on anything a real
Urdu word never does:

| layer | what it checks |
|---|---|
| structural rules | presentation-form codepoints, medial `آ`, impossible 5+ consonant runs, doubled plural markers (`بازؤنوں`), a derivational suffix on an already-inflected stem (`جوتوںی`), repeated agentive tails (`فنکارگر`), stray diacritics |
| regression lists | ~55 real words that **must** be present and ~60 junk tokens that must **never** appear in any tier — every bug the audit ever found is pinned here |
| fluency queue | an informational bigram score that ranks odd tokens for human review (never a hard gate: it also dislikes rare-but-real words like `آؤ`) |

Run it yourself:

```bash
python tools/audit_words.py            # the shipped default tier
python tools/audit_words.py --full     # the full tier
python tools/audit_words.py --queue 25 # show the human-review queue
```

Current result — both tiers:

```text
urduofdani :: word audit - urdu_database.txt.gz
====================================================================
  tokens               : 15,848
  structural violations: 0
  missing real words   : none
  junk still present   : none
====================================================================
[audit_words] PASS  (every structural rule and regression list is clean)
```

### What the audit found and removed

| # | bug class | examples the audit caught | fix |
|---|---|---|---|
| 1 | **blind head attachment** — `خانہ/گاہ/دکان/منڈی` were glued to whole sections | `آلوخانہ`, `آنکھگاہ`, `آلودگیگودام`, `اجرتمنڈی` | every head has a curated host list (`HEAD_HOSTS`), same idea as the agentive hosts |
| 2 | **blind agentive cross product** — 226 stems × 10 suffixes | `اسٹیڈیمفروش`, `آبپاشیدان`, `اخبارساز`, `انجندان` | curated per-suffix host tables (`AGENTIVE_SUFFIX_HOSTS`) |
| 3 | **silent phrase fusion** — a spaced seed was fused into one token | `اٹھائی والا → اٹھائیوالا`, `صافکرنےوالا` | fusion is allowed only inside hand-written banks; generators can never fuse |
| 4 | **verb banks that were not verbs** — infinitives and nouns listed as roots | `آرامنےوالا`, `کامنا`, `آرامتا` | roots are repaired (`ابھرنا → ابھر`) or refused (`NON_VERB_ROOTS`) |
| 5 | **noun sections wearing adjective suffixes** | `گردنپن`, `ہڑتالگی`, `کمانڈرپن`, `کمانڈرناک` | a section may only use the morphology its own rule allows |
| 6 | **sacred names stored inflected** — the Anbiya bank itself listed `نبیوں` / `پیغمبروں` | plural forms of prophets "protected" by the never-inflect guard | inflected entries removed; the guarantee is now tested for every name × 8 markers |

The 2,000+ real words a strict guard would have deleted are kept in curated tables
with their reasons written down (`KEEP_FORMS`, `LOAN_PLURAL_HOSTS`, the place-head
whitelist) — that is how `چائےخانہ`, `اسٹیشنز`, `کمپیوٹرز` and `کتابدار` survive a
strict audit.

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

Expected output (abridged — the compiler reports every section):

```text
[urduofdani] lexicon compiled in 0.111s
    + 1_curated                     3,722
    + 2_tech                          931
    + 7_verb_forms                  5,065
    + 9_compounds                      89
    + 9b_agentives                    167
    = TOTAL                        15,848 unique Urdu words
[urduofdani] wrote urdu_database.txt.gz
    raw      : 107.75 KB
    gzip     : 43.90 KB  (59.3% smaller)
    io time  : 0.050s
    sha256   : d1081d60509e760d...   (rebuild it: the build is deterministic)
```

### Step 3 — Verify the artifact (recommended)

```bash
python urduofdani.py verify --export urdu_database.txt
```

```text
[urduofdani] verifying urdu_database.txt.gz
    [PASS] gzip readable      44954 bytes packed payload
    [PASS] sacred names intact 373 present, 0 inflected
    [PASS] no newline         single line
    [PASS] no comma           comma-free
    [PASS] no digits          digit-free
    [PASS] non-empty database 15848 tokens
    [PASS] no duplicates      15848 tokens / 15848 unique
    [PASS] all tokens legal   100% Urdu letters
```

`verify` exits **0** when all eight checks pass and **1** when any check fails,
so it drops straight into CI (`run: python urduofdani.py verify`).

### Step 4 — Load it in your app

See [Section 5](#5-integration-load-urdu_databasetxtgz-at-runtime).

### Optional — build the massive variants

```bash
# 17,539 words / 48 KB - the shipped "full" build (already in this repo)
python urduofdani.py build --mode full -o urdu_database.full.txt.gz

# 16,243 words - compounds + agentives + affix families, quality-gated
python urduofdani.py build --mode exhaustive

# 2,592,831 tokens / 7.0 MB - raw maximum recall, machine-oriented
python urduofdani.py build --mode recall -o urdu_database.recall.txt.gz
```

**Mode ladder**

| Mode | Words | What it adds | Quality |
|---|---|---|---|
| `--mode mini` | 3,000 | a small, fast subset for embedded / low-RAM targets | ✅ hand-verified vocabulary |
| `--mode default` | 15,848 | seeds + plurals + gender + verb families + curated compounds/agentives + 373 sacred names | ✅ **word-audited, 0 violations** |
| `--mode exhaustive` | 16,243 | section-gated affix families, prefix hosts | ✅ word-audited |
| `--mode wide` | 16,875 | relational `-ی`, the curated `والا` family, plural+`والا`, market heads | ✅ word-audited |
| `--mode full` | 17,539 | the wide ladder plus the depth-4 derivations that survive the audit | ✅ word-audited |
| `--mode recall` | 2,592,831 | full prefix × root × suffix × head cross product | ⚠️ machine only (raw by design) |

> `--unlimited` never caps the lexicon (`--max-words 0`), and `--depth` controls how
> far the combinatorial ladder goes. Every emitted token is still **letter-legal
> Urdu** (no digits, no Latin, no punctuation) — which is exactly what a
> spell-checker or "did you mean…" engine needs.
>
> The audited tiers shrank when the word audit ran: the old 25k/116k numbers came
> from blind section-wide glue (`آلوخانہ`, `اسٹیڈیمفروش`, `آرامنےوالا`) that a real
> Urdu speaker would never call a word. Quality first: the machine tier still gives
> you 2.59 M tokens when you want raw recall.

## 5. Integration: Load `urdu_database.txt.gz` at Runtime

### Recipe 1 — Minimal loader (copy-paste, 6 lines)

```python
import gzip

def load_urdu_database(path: str = "urdu_database.txt.gz") -> list[str]:
    """Decompress the single-line database and return a list of Urdu words."""
    with gzip.open(path, "rb") as fh:
        payload = fh.read().decode("utf-8")
    return payload.split(" ") if payload else []

WORDS = load_urdu_database()        # e.g. 15,848 words - takes ~2.0 ms
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
    engine = UrduEngine()            # auto-locates urdu_database.txt.gz, ~2.0 ms
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
engine = UrduEngine()                      # loaded ONCE at import time (~2.0 ms)

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
    load_urdu_database,  # -> list[str]   (whole DB, ~2.0 ms)
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
| `--exhaustive` | off | Section-gated affix families (16,243 audited words). |
| `--unlimited` | off | No cap at all — keep every generated token (pair with `--depth`). |
| `--depth {1,2,3,4}` | `2` | How far the combinatorial ladder climbs under `--unlimited`/`--recall` (4 = largest). |
| `--recall` | off | Raw maximum-recall cross product (2,592,831 tokens, machine-oriented). |
| `--min-len` / `--max-len` | `2` / `40` | Token length window. |
| `--keep-diacritics` | off | Keep harakat (`اَ`) instead of folding them. |
| `--format {plain,compact}` | `plain` | Payload layout: `plain` = one space-separated line (fastest); `compact` = front-coded, ~2.6× smaller gz (16.8 KB vs 43.9 KB) for ~4.5 ms more load time. |
| `--verify` | off | Run the 8 integrity checks after building. |
| `--export TXT` | – | Also write the plain single-line `.txt`. |
| `--benchmark [N]` | – | Benchmark N decompression runs. |
| `--no-build` | off | Skip compilation (benchmark/verify an existing `.gz`). |
| `--samples N` | `6` | Print N random words + a `suggest()` demo. |
| `--version` | – | Print the compiler version. |

Common invocations:

```bash
python build_urdu_database.py                                  # recommended build
python build_urdu_database.py --verify --benchmark 10          # build + prove + measure
python build_urdu_database.py --exhaustive                     # 16,243-word quality expansion
python build_urdu_database.py --unlimited --depth 4 -o urdu_database.full.txt.gz
python build_urdu_database.py --recall -o urdu_database.recall.txt.gz
python build_urdu_database.py --no-build --benchmark 5         # measure an existing .gz only
python build_urdu_database.py --keep-diacritics -o harakat.txt.gz
python build_urdu_database.py --max-words 3000 -o small.txt.gz # light build for embedded apps
```

The front door wraps all of this — see [§7b](#7b-the-front-door-urduofdanipy) for
`info`, `build`, `verify`, `bench`, `search`, `check`, `suggest`, `export`,
`random`, `test` and `modes`.

## 7b. The Front Door: `urduofdani.py`

`build_urdu_database.py` stays the engine (and keeps its own flags for
backwards compatibility). Day to day you only need **one** command:

```bash
python urduofdani.py <command> [options]
```

| Command | What it does | Example |
|---|---|---|
| `info` | show the active database: words, packed size, RAM, load time, samples | `python urduofdani.py info` |
| `build` | compile a tier (`--mode`) to a `.gz` | `python urduofdani.py build --mode full` |
| `verify` | run the 8 integrity checks (exit 1 on failure) | `python urduofdani.py verify -F` |
| `bench` | benchmark decompression + indexing | `python urduofdani.py bench -r 10` |
| `search` | prefix search from the shell | `python urduofdani.py search کمپیو -l 10` |
| `check` | spell-check a word (exit 0 = present, 1 = missing) | `python urduofdani.py check کتاب` |
| `suggest` | autocomplete list for a prefix | `python urduofdani.py suggest کم` |
| `export` | write the plain single-line `.txt` | `python urduofdani.py export out.txt` |
| `random` | print random words (seeded = reproducible) | `python urduofdani.py random -n 5` |
| `modes` | list every tier with its size and purpose | `python urduofdani.py modes` |
| `test` | run the test suite (delegates to `run_tests.py`) | `python urduofdani.py test` |
| `audit` | run **every** gate: tests · artifact verification · docs audit · tier table · examples | `python urduofdani.py audit` |

Shared flags: `-d/--db PATH` (use a specific database) and `-F/--full` (use
`urdu_database.full.txt.gz`). Exit codes are script-friendly: **0** success,
**1** check failed, **2** database missing.

`build` only writes the shipped `urdu_database.txt.gz` for `--mode default`;
every other tier defaults to its own file (`urdu_database.mini.txt.gz`,
`urdu_database.full.txt.gz`, …) unless you pass `-o`, so a casual
`build --mode mini` can never clobber the release artifact.

```bash
python urduofdani.py audit       # the whole protocol, six gates, one exit code
python urduofdani.py verify
python urduofdani.py search دانا -l 5
python urduofdani.py check دانا        # -> present (exit 0)
python urduofdani.py check ززززز        # -> missing (exit 1)
```

## 7c. Tests, Examples & Tools

```bash
python run_tests.py             # 60 tests, ~3 s, no dependencies
python run_tests.py -v          # verbose
python run_tests.py -k sacred   # only tests whose name matches
```

| Path | Purpose |
|---|---|
| `tests/test_urduofdani.py` | The suite: orthography folding, morphology, sacred-name safety, the build (determinism, gzip format, multibyte boundaries), the engine, the CLI, and the shipped artifacts. |
| `examples/quickstart.py` | Guided five-minute tour: load, index, fold, extend, stream, report. |
| `examples/autocomplete_app.py` | A complete Tkinter autocomplete app (Windows-ready, `--list` for headless checks, PyInstaller recipe in the header). |
| `tools/measure_tiers.py` | Builds every tier and prints the benchmark table; `--check README.md` fails if the docs go stale. |
| `tools/audit_docs.py` | Documentation audit: anchors, links, word-count claims, documented CLI surface. |
| `tools/audit_words.py` | **Word audit**: structural rules + regression lists over every shipped token (`--full` audits the full tier). |

```

## 8. Dictionary Coverage

**34 domain sections** · 5,188 curated entries · 259 verb roots · 373 protected sacred names


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
| `name` | احمد، فاطمہ، عبدالرحمٰن، زینب، قریشی | **none** (names are never inflected) |
| `medical` | بخار، ڈینگی، انجیکشن، سرجری، نسخہ، ویکسین | plurals, `-ی`, `والا`, compound heads |
| `law` | مقدمہ، عرضی، ضمانت، گواہ، اپیل، ڈگری | plurals, `-ی` |
| `military` | رینجرز، کرنل، مورچہ، میزائل، تمغہ، شہادت | plurals, `-ی` |
| `business` | انوائس، ٹینڈر، اسٹاک، برآمد، محصول، بروکر | plurals, `-ی`, market heads |
| `agri` | کاشت، آبپاشی، کھاد، ہارویسٹر، گندم، گنا | plurals, `-ی`, `والا`, market heads |
| `religion` | اعتکاف، تراویح، تفسیر، فاتحہ، صدقہ | plurals, `-ی`, `گاہ/خانہ` |
| `science` | طبیعیات، ایٹم، سالمہ، مدار، تعدد، وولٹ | plurals, `-ی` |
| `art` | غزل، سارنگی، خطاطی، اسکرپٹ، ایڈیٹنگ | plurals, `-ی`, `گاہ/خانہ` |
| `emotion` | مسرت، افسردگی، ہیبت، طمانچہ، وجدان | plurals, `-ی/پن`, gender agreement |
| `transport` | بوگی، پٹری، موٹروے، گودام، ٹینکر | plurals, `-ی` |
| `tool` | رندہ، بسولا، سریا، ویلڈنگ، ٹھیکہ | plurals, `-ی`, `والا`, shop heads |
| agentives | کتاب ساز، مچھلی فروش، دکان دار، پھول والا | 226 curated host stems × 10 suffixes |
| `allah` 🕌 | اللہ، رحمٰن، رحیم، ملک، قدوس، غفور، ودود، ذوالجلال | **none** (sacred - never inflected) |
| `nabi` 🕌 | آدم، نوح، ابراہیم، موسی، داؤد، عیسی، محمد، مصطفی | **none** (sacred - never inflected) |
| `ahlbayt` 🕌 | علی، فاطمہ، حسن، حسین، زینب، عباس، مہدی، خدیجہ | **none** (sacred - never inflected) |
| `sahaba` 🕌 | ابوبکر، عمر، عثمان، سلمان، بلال، ابوہریرہ | **none** (sacred - never inflected) |
| verbs | کرنا، دیکھنا، پڑھنا، ڈھونڈنا … | infinitive, habitual, subjunctive, perfective, future, imperative, polite, causative, verbal nouns |
| curated irregulars | باغبان، دکاندار، گندگی، ٹھنڈک، کتابچہ، میٹھاس | hand-written (no rule should invent these) |

**Two build modes**

* **`--mode default`** — every rule is gated by real Urdu phonology and by hand-written host sets: `بے` only attaches to bases that truly take it (`بےکار`, `بےنام`, `بےوفا`), agentive suffixes (`دار`, `فروش`, `ساز`) only to the curated host stems, market heads (`منڈی`, `بازار`, `گودام`) only to the curated host stems. Result: **15,848** clean tokens.
* **`--mode exhaustive` / `--mode wide`** — section-gated affix families and relational forms: **16,243** / **16,875** tokens, still quality-gated.
* **`--mode full`** — no cap, `--depth 4`: **17,539** tokens, all of them audited.
* **`--mode recall`** — the unfiltered cross product: **2,592,831** machine-oriented tokens for spell-correction and fuzzy search.

## Sacred Names (Protected)

<div align="center">
  <img src="assets/logo.png" alt="" width="42" height="42">
</div>

The dictionary ships **373 unique sacred names** (387 entries as written), stored
**exactly as written in Urdu**, across four dedicated sections:

| Section | Count | Contents |
|---|---|---|
| `allah` | **213** | أسماء الحسنى — the 99 names of Allah in both bare (`رحمٰن`, `کریم`) and `ال`-prefixed (`الرحمن`, `الکریم`) forms, plus related terms (`اسم اعظم`, `تسبیح`, `تحمید`, `تکبیر`, `تقدیس`) |
| `nabi` | **51** | أنبياء و رسل — آدم، ادریس، نوح، ہود، صالح، ابراہیم، لوط، اسماعیل، اسحاق، یعقوب، یوسف، ایوب، شعیب، موسی، ہارون، ذوالکفل، داؤد، سلیمان، الیاس، الیسع، یونس، زکریا، یحیی، عیسی، محمد ﷺ (+ احمد، مصطفی، خضر، لقمان، ذوالقرنین …) |
| `ahlbayt` | **82** | اہل بیت و آلِ علی — علی، حیدر، مرتضی، ابوتراب، اسداللہ، فاطمہ، زہرا، حسن، حسین، زینب، عباس، قاسم، اُمّ کلثوم، اُمّ البنین، the twelve Imams (زین العابدین، باقر، صادق، کاظم، رضا، تقی، نقی، عسکری، مہدی …), the Prophet's household (آمنہ، عبداللہ، ابوطالب، حمزہ، جعفر طیار، حلیمہ) and the mothers of the believers (خدیجہ، عائشہ، حفصہ، اُمّ سلمہ، جویریہ، صفیہ، میمونہ …) |
| `sahaba` | **41** | صحابہ کرام — ابوبکر، عمر، عثمان، علی، طلحہ، زبیر، عبدالرحمن، سعد، سعید، ابو عبیدہ، ابوذر، سلمان، عمار، بلال، حذیفہ، مقداد، ابوہریرہ، انس، جابر … |

### The guarantee

> **A sacred name is never inflected.** No plural, no suffix, no prefix, no
> compound head is ever attached to it — in *any* build mode.

This is enforced twice, so it cannot be bypassed:

1. **Section rule** — all four sections use `Rule()` (no morphology) and are listed in `SACRED_SECTIONS`, which the forge skips for every derivation stage, including `--exhaustive`, `--unlimited` and `--recall`.
2. **Compiler guard** — `is_sacred_derivative()` runs inside `_add()` and rejects any candidate token whose base is a sacred name plus an inflection marker (`وں، یں، اں، ات، ے، ؤں`). Even a future rule change cannot emit `اللہوں`, `محمدوں` or `علیوں`. A self-check makes sure no inflected form can ever sneak *into* the pool in the first place (`tests/test_urduofdani.py::test_pool_contains_no_inflected_entries`).
3. **Homograph exception** — a handful of divine names are also everyday Urdu nouns (`ملک` = king/country, `حق` = right, `حکم` = order, `شہید` = martyr, `مقدم` = lawsuit). There the ordinary reading wins, so `ملکوں`, `حقوں`, `حکموں`, `شہیدوں` and `مقدمے` stay in the dictionary; every proper name (`اللہ`, `محمد`, `علی`, `حسن`, `حسین`, `فاطمہ`, `مریم`, `نوح`, `ابراہیم`, …) remains fully protected. The exception list lives in `SACRED_HOMOGRAPH_STEMS`.

`--verify` proves it on the shipped artifact:

```text
[urduofdani] verifying urdu_database.txt.gz
    [PASS] gzip readable      74683 bytes packed payload
    [PASS] sacred names intact 373 present, 0 inflected     <-- the guarantee
    [PASS] no newline         single line
    ...
```

Verified across every tier (build is deterministic, so these numbers are reproducible):

| Mode | Tokens | Sacred names present | Inflected sacred names |
|---|---|---|---|
| `--mode mini` | 3,000 | 373 / 373 | **0** |
| `--mode default` | 15,848 | 373 / 373 | **0** |
| `--mode exhaustive` | 16,243 | 373 / 373 | **0** |
| `--mode wide` | 16,875 | 373 / 373 | **0** |
| `--mode full` | 17,539 | 373 / 373 | **0** |
| `--mode recall` | 2,592,831 | 373 / 373 | **0** |

### Using them at runtime

Because sacred names live in the same single-space payload, they arrive through the
same fast path — and behave like any other dictionary word:

```python
from build_urdu_database import UrduEngine, SACRED_NAMES

engine = UrduEngine()
print(len(SACRED_NAMES))                      # 373
print("اللہ" in engine, "محمد" in engine, "فاطمہ" in engine)   # True True True
print(engine.suggest("علی", 5))               # ['علی', 'علیم', 'علیحدہ', ...]
print("اللہوں" in engine)                     # False  <- never generated
```

Practical uses: religious-text normalisation, honorific handling, name-lookup
fields (madrasa / mosque apps), Islamic calendar & dua tools, and any UI that must
never auto-pluralise a sacred name.

---

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
<summary><b>Why is compression 80% instead of exactly 90%?</b></summary>

DEFLATE pays off with repetition, and Urdu morphology repeats constantly (‑وں، ‑یں، ‑دار، ‑مند، ‑خانہ). The shipped 25.3k-word build saves **79.5%**; the 116.2k full build saves **85.7%**; the 2.6M-token recall tier reaches **89.2%**. The practical outcome is the same every time: a file orders of magnitude smaller than the raw text that decompresses in milliseconds.
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
<summary><b>Is the unlimited / recall build safe to ship?</b></summary>

Both are *technically* safe (valid gzip, single line, every token letter-legal), but they are **generated vocabulary**, not verified word lists. Guidance:

| Tier | Use it for |
|---|---|
| default (25.3k) | user-visible "is this a real word?" checks, autocomplete ranking |
| `--unlimited --depth 2` (57k) | large suggestion pools, taggers |
| `--unlimited --depth 4` (114k) | spell-correction candidates, fuzzy match |
| `--recall` (2.6M) | offline spelling correction / corpus indexing only |

The default build derives agentives and compounds exclusively from **curated host stems**, so `کتاب ساز` and `مچھلی فروش` exist while `ذہانت ساز` does not.
</details>

<details>
<summary><b>Does it work with non-Urdu text (English/Arabic/Persian)?</b></summary>

The container (single-line + gzip + atomic write) is language-agnostic: point `--min-len/--max-len` and the seed constants at any vocabulary you like. The normalisation layer is Urdu-oriented (Arabic + Urdu folds), but Hindi/Persian lists work with minor seed changes.
</details>

<details>
<summary><b>What's the actual bottleneck?</b></summary>

Morphology generation — the "compile every variant" step: 0.11 s for the default 15.8k build, 0.15 s for the 17.5k full build, ~33 s for the 2.6M recall tier. Decompression is essentially free (2.0 ms) and happens once per process.
</details>

<details>
<summary><b>Why are sacred names never inflected?</b></summary>

Because pluralising or suffixing them would be both grammatically wrong and
disrespectful. The compiler enforces it twice (a section rule plus
`is_sacred_derivative()` inside `_add()`), and `--verify` proves it on the shipped
artifact — see [Sacred Names (Protected)](#sacred-names-protected). Even the
2.6M-token `--recall` tier contains zero inflected sacred names.
</details>

<details>
<summary><b>How do I add more names (prophets, companions, family)?</b></summary>

Append to the relevant block in `build_urdu_database.py`:

```python
AHL_BAYT_NAMES: str = "... your additions here ..."
```

Then rebuild — the new names are automatically protected (they enter
`SACRED_NAMES`, so no rule can inflect them) and `--verify` re-checks the guarantee.
</details>

<details>
<summary><b>How do I get <i>even more</i> words?</b></summary>

Three independent dials, all uncapped:

```bash
python build_urdu_database.py --unlimited --max-words 0             # no token cap
python build_urdu_database.py --unlimited --depth 4                 # deeper combinatorics
python build_urdu_database.py --recall                              # raw cross product (millions)
```

…plus the highest-quality dial of all: **add curated seeds**. Drop your words into
`ADDITIONAL_SEEDS`, `NAME_WORDS`, `MEDICAL_WORDS`, `AGRI_WORDS`, … in
`build_urdu_database.py` and rebuild — every new seed multiplies through the
plural, gender, verb, compound and agentive stages automatically.
</details>

## 13. Repository Layout

```text
urduofdani-dictionary/
├── urduofdani.py              # the front door: info/build/verify/bench/search/check/…
├── build_urdu_database.py     # the whole engine: compiler + runtime + CLI (stdlib only)
├── urdu_database.txt.gz       # default database (15,848 audited words / 43.9 KB)
├── urdu_database.compact.gz   # front-coded twin (15,848 words / 16.8 KB, ~6.5 ms)
├── urdu_database.full.txt.gz  # full build (17,539 words / 48.1 KB)
├── urdu_database.full.compact.gz  # front-coded full tier (17,539 words / 18.0 KB)
├── run_tests.py               # test runner (verbosity + -k pattern filters)
├── tests/test_urduofdani.py   # 60 tests: orthography, morphology, sacred names, build, CLI
├── examples/                  # quickstart tour + Tkinter autocomplete app
├── tools/                     # measure_tiers.py (benchmark table) + audit_docs.py (docs audit)
├── CHANGELOG.md               # release history
├── ROADMAP.md                 # audit protocol and next steps
├── assets/
│   ├── banner.jpg             # README banner (1600x500, fast-loading)
│   ├── banner.png             # lossless master of the banner
│   ├── logo.png               # project mark (512x512)
│   ├── logo.svg               # hand-authored vector version
│   ├── social-preview.png     # GitHub social preview card (1280x640)
│   ├── banner-bg.jpg          # base artwork (input for build_assets.sh)
│   └── build_assets.sh        # regenerates the raster assets (ImageMagick)
├── CONTRIBUTING.md            # how to add words, style guide, format contract
├── README.md                  # this document
├── LICENSE                    # MIT
└── .gitignore
```

After `--export` / `--recall` runs you may also see `urdu_database.txt` (plain single-line text) and `urdu_database.recall.txt.gz` (the 2.6M-token machine tier).

## 14. Roadmap

The full plan — including the audit protocol this project is maintained with — lives in [ROADMAP.md](ROADMAP.md); the release history lives in [CHANGELOG.md](CHANGELOG.md).

* [x] **Single-space tokenization + gzip** — 15,848 audited words in 43.9 KB, 2.0 ms cold load
* [x] **Unlimited builds** — no cap, depth-controlled expansion (`--mode recall` = 2,592,831 tokens)
* [x] **30+ domain sections** with per-section morphology rules and curated host gates
* [x] **373 sacred names** (Allah · Anbiya · Ahl al-Bayt · Sahaba) with a never-inflect guarantee
* [x] **Front door, tests, CI, reproducible builds** — `urduofdani.py`, 60 tests, byte-identical artifacts
* [ ] Optional **suffix-index compression** (front-coding) for smaller artifacts
* [ ] **Roman-Urdu → Urdu** transliteration hints (`kitab → کتاب`)
* [ ] **Hunspell / SymSpell export** (`--export-dic`, `--export-frequency`)
* [ ] Word-frequency weights for better autocomplete ranking
* [ ] Prebuilt CI artifacts (default / full / recall) published as GitHub Release assets

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
