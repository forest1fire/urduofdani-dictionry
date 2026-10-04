#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: examples/quickstart.py
====================================
The five-minute tour. Run it from the repository root:

    python examples/quickstart.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_urdu_database import (          # noqa: E402
    SACRED_NAMES,
    UrduEngine,
    canonicalize,
    iter_urdu_words,
    load_urdu_database,
)


def main() -> int:
    # 1 ------------------------------------------------------------------ load
    start = time.perf_counter()
    words = load_urdu_database()            # default database, next to the module
    elapsed = (time.perf_counter() - start) * 1000
    print("1. loaded %s words in %.2f ms" % (f"{len(words):,}", elapsed))
    print("   first three: %s" % " ".join(words[:3]))

    # 2 --------------------------------------------------------------- engine
    engine = UrduEngine()                   # ~2.5 ms, indexes set + sorted list
    print("2. engine ready in %.2f ms" % (engine.load_seconds * 1000))
    print("   'کمپیوٹر' in engine  -> %s" % ("کمپیوٹر" in engine))
    print("   'كِتاب' (Arabic kaf) -> %s   (folded to %s)" % ("كِتاب" in engine, canonicalize("كِتاب")))
    print("   autocomplete 'کمپیو' -> %s" % engine.suggest("کمپیو", 4))

    # 3 ------------------------------------------------------------ your words
    engine.extend(["بلوچستان", "گوادر", "میرا لفظ"])   # multi-word input is skipped
    print("3. after extend: %s words (+%d added, %d skipped)"
          % (f"{len(engine):,}", 2, engine.last_extend_skipped))

    # 4 ---------------------------------------------------------------- sacred
    hits = [w for w in ("اللہ", "رحمٰن", "محمد", "علی", "فاطمہ", "حسین", "زینب") if w in engine]
    print("4. sacred names: %d protected, sample present -> %s" % (len(SACRED_NAMES), " ".join(hits)))
    print("   'اللہوں' in engine   -> %s   (never generated)" % ("اللہوں" in engine))

    # 5 --------------------------------------------------------------- stream
    streamed = sum(1 for _ in iter_urdu_words(block_bytes=1 << 16))
    print("5. streamed %s words with constant memory" % f"{streamed:,}")

    # 6 ----------------------------------------------------------------- info
    info = engine.info()
    text_kb = sum(len(w) for w in engine.words()) * 2 / 1024      # 2 bytes per Urdu letter
    print("6. %s | %s packed | %.1f KB of text in RAM"
          % (Path(info["path"]).name, "%d bytes" % info["packed_bytes"], text_kb))
    print("\nNext: python urduofdani.py modes   ->  pick a bigger build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
