#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: urduofdani.py
===========================
The friendly front door. One command for every routine task, so you never have
to remember the long flag names of ``build_urdu_database.py``.

::

    python urduofdani.py info                     # what is in the database?
    python urduofdani.py build                    # rebuild (balanced, ~25k words)
    python urduofdani.py build --mode full        # 113k-word unlimited build
    python urduofdani.py verify                   # 7 integrity checks
    python urduofdani.py bench                    # cold-load benchmark
    python urduofdani.py search کمپیوٹر            # prefix search
    python urduofdani.py check کتاب               # is this a word? (rc 0/1)
    python urduofdani.py suggest کمپیو --limit 10  # what would autocomplete show?
    python urduofdani.py export urdu_database.txt # plain single-line text
    python urduofdani.py test                     # run the test suite
    python urduofdani.py modes                    # explain the build modes

Everything is stdlib-only and Windows-safe. Exit codes are script-friendly:
``0`` success, ``1`` check failed / problems found, ``2`` usage error.
"""

from __future__ import annotations

import argparse
import gzip
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_urdu_database as core   # noqa: E402  (path set above)

HERE = Path(__file__).resolve().parent
DEFAULT_DB = "urdu_database.txt.gz"
FULL_DB = "urdu_database.full.txt.gz"

MODES = {
    "mini": dict(max_words=3000, exhaustive=False, unlimited=False, depth=2,
                 blurb="~3k words - embedded / low-RAM targets (a few KB)"),
    "default": dict(max_words=0, exhaustive=False, unlimited=False, depth=2,
                    blurb="~25k words - curated + gated morphology (recommended)"),
    "exhaustive": dict(max_words=0, exhaustive=True, unlimited=False, depth=2,
                       blurb="~42k words - section-gated affix families"),
    "wide": dict(max_words=0, exhaustive=True, unlimited=True, depth=2,
                 blurb="~57k words - relational forms, والا family, market heads"),
    "full": dict(max_words=0, exhaustive=True, unlimited=True, depth=4,
                 blurb="~114k words - deep combinatorics (the shipped .full build)"),
    "recall": dict(max_words=0, exhaustive=True, unlimited=True, depth=2, recall=True,
                   blurb="~2.6M tokens - raw cross product, machine tier only"),
}


# --------------------------------------------------------------------- helpers
def _utf8_console() -> None:
    """Windows cp1252 consoles must not crash when printing Urdu."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def _resolve_db(value: Optional[str], prefer_full: bool = False) -> Path:
    """Pick the database: explicit path > full build (if asked) > default > error."""
    if value:
        chosen = Path(value)
        if not chosen.exists():                     # friendly failure, not a traceback
            raise SystemExit("[urduofdani] database not found: %s" % chosen)
        return chosen
    candidates = [HERE / FULL_DB, HERE / DEFAULT_DB] if prefer_full else \
                 [HERE / DEFAULT_DB, Path.cwd() / DEFAULT_DB, HERE / FULL_DB]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("[urduofdani] no database found - run:  python urduofdani.py build")


def _engine(path: Optional[str], prefer_full: bool = False) -> core.UrduEngine:
    return core.UrduEngine(_resolve_db(path, prefer_full))


def _rule(title: str = "") -> None:
    print("─" * 66 + ("\n " + title if title else ""))


# --------------------------------------------------------------------- commands
def cmd_info(args: argparse.Namespace) -> int:
    engine = _engine(args.db, prefer_full=args.full)
    info = engine.info()
    packed = int(info["packed_bytes"])
    raw = sum(len(w.encode("utf-8")) + 1 for w in engine.words()) - 1
    storage = HERE / DEFAULT_DB
    print("urduofdani :: info")
    _rule()
    print("  database          : %s" % Path(info["path"]).name)
    print("  words             : %s" % f"{len(engine):,}")
    print("  packed (.gz)      : %s" % core._human(packed))
    print("  unpacked (UTF-8)  : %s" % core._human(raw))
    print("  compression saved : %.1f%%" % ((1 - packed / raw) * 100 if raw else 0))
    print("  cold load         : %.3f ms" % (engine.load_seconds * 1000))
    print("  sacred names      : %d protected" % len(core.SACRED_NAMES))
    print("  compiler version  : %s" % core.SCRIPT_VERSION)
    print("  all databases     : %s" % ", ".join(
        p.name for p in (storage, HERE / FULL_DB) if p.exists()))
    _rule()
    rng = random.Random(20261004)          # deterministic sample for the summary
    print("  " + "   ".join(rng.choice(engine.words()) for _ in range(9)))
    print("  %s  |  %s" % (engine.suggest("کم", 4), engine.suggest("علی", 3)))
    return 0


def build_kwargs(mode: str) -> Dict[str, object]:
    """Builder kwargs for a mode (drops the human-readable blurb)."""
    return {k: v for k, v in MODES[mode].items() if k != "blurb"}


def cmd_build(args: argparse.Namespace) -> int:
    spec = build_kwargs(args.mode)
    output = args.output or (FULL_DB if args.mode in ("full", "recall") else DEFAULT_DB)
    print("urduofdani :: build  (mode=%s - %s)" % (args.mode, MODES[args.mode]["blurb"]))
    stats = core.build_urdu_database(
        output_path=HERE / output,
        min_len=args.min_len,
        max_len=args.max_len,
        keep_diacritics=args.keep_diacritics,
        **spec,
    )
    if args.verify and not core.verify_database(HERE / output):
        return 1
    print("[urduofdani] words: %s | artifact: %s" %
          (f"{stats['0_total_words']:,}", output))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    ok = core.verify_database(_resolve_db(args.db, prefer_full=args.full),
                              export_txt=args.export)
    return 0 if ok else 1


def cmd_bench(args: argparse.Namespace) -> int:
    core.benchmark(_resolve_db(args.db, prefer_full=args.full), repeats=args.runs)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    engine = _engine(args.db, prefer_full=args.full)
    hits = engine.suggest(args.query, limit=args.limit)
    if not hits and args.contains:
        hits = engine.search(args.query, limit=args.limit)
    if not hits:
        print("[urduofdani] no matches for %r" % args.query)
        return 1
    for word in hits:
        print(word)
    print("[urduofdani] %d match(es) for %r" % (len(hits), args.query), file=sys.stderr)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    engine = _engine(args.db, prefer_full=args.full)
    valid = args.word in engine
    print("%s  %s" % ("✅ YES" if valid else "❌ NO ", args.word))
    if not valid:
        close = engine.suggest(core.canonicalize(args.word)[:3], 5)
        if close:
            print("    did you mean: %s" % "  ".join(close))
    return 0 if valid else 1


def cmd_suggest(args: argparse.Namespace) -> int:
    engine = _engine(args.db, prefer_full=args.full)
    print(" | ".join(engine.suggest(args.prefix, args.limit)))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    db = _resolve_db(args.db, prefer_full=args.full)
    target = Path(args.output)
    with gzip.open(db, "rb") as src:
        target.write_bytes(src.read())
    print("[urduofdani] exported single-line text -> %s (%s)" %
          (target, core._human(target.stat().st_size)))
    return 0


def cmd_random(args: argparse.Namespace) -> int:
    engine = _engine(args.db, prefer_full=args.full)
    rng = random.Random()
    print(" ".join(rng.choice(engine.words()) for _ in range(args.count)))
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    runner = HERE / "run_tests.py"
    cmd = [sys.executable, str(runner)] + (["-v"] if args.verbose else [])
    return subprocess.call(cmd, cwd=str(HERE))


AUDIT_GATES = (
    ("tests", "run_tests.py", ["--quiet"]),
    ("verify default", "urduofdani.py", ["verify"]),
    ("verify full", "urduofdani.py", ["verify", "--full"]),
    ("docs", "tools/audit_docs.py", []),
    ("tier table", "tools/measure_tiers.py", ["--check", "README.md"]),
    ("examples", "examples/quickstart.py", []),
)


def cmd_audit(args: argparse.Namespace) -> int:
    """Run every audit gate in sequence; one failure is enough to fail the run."""
    print("urduofdani :: audit protocol")
    _rule()
    failures = []
    for label, script, extra in AUDIT_GATES:
        path = HERE / script
        if not path.exists():
            failures.append(label)
            print("  [SKIP] %-16s %s is missing" % (label, script))
            continue
        proc = subprocess.run([sys.executable, str(path)] + extra,
                              cwd=str(HERE), capture_output=True, text=True)
        ok = proc.returncode == 0
        first = next((l.strip() for l in (proc.stdout or "").splitlines()
                      if l.strip() and not l.startswith("[urduofdani]")), "")
        print("  [%s] %-16s %s" % ("PASS" if ok else "FAIL", label,
                                   first[:64] if ok else (proc.stdout or proc.stderr).strip().splitlines()[-1][:64]))
        if not ok:
            failures.append(label)
    _rule()
    if failures:
        print("  %d gate(s) failed: %s" % (len(failures), ", ".join(failures)))
        print("  details: rerun the failing tool directly, e.g. python %s"
              % next(e[1] for e in AUDIT_GATES if e[0] == failures[0]))
        return 1
    print("  all %d gates passed - tests, artifacts, docs, tier table, examples" % len(AUDIT_GATES))
    return 0


def cmd_modes(args: argparse.Namespace) -> int:
    print("urduofdani :: build modes")
    _rule()
    for name, spec in MODES.items():
        print("  %-11s %s" % (name, spec["blurb"]))
    _rule()
    print("  python urduofdani.py build --mode full      # the 116k build")
    print("  python urduofdani.py build --mode recall    # 2.6M-token machine tier")
    print("  python urduofdani.py modes                  # this list")
    return 0


# --------------------------------------------------------------------- argparse
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="urduofdani",
        description="urduofdani - Modern High-Speed Urdu Text Engine (front door).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python urduofdani.py info
  python urduofdani.py build --mode full --verify
  python urduofdani.py bench --runs 10
  python urduofdani.py search کمپیوٹر --limit 5
  python urduofdani.py check کتاب ; echo "exit=$?"
  python urduofdani.py test
""",
    )
    p.add_argument("--version", action="version", version="urduofdani %s" % core.SCRIPT_VERSION)
    sub = p.add_subparsers(dest="command", required=True)

    def add_db_flags(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-d", "--db", default=None, metavar="PATH",
                            help="database .gz to use (default: auto-detect)")
        parser.add_argument("-F", "--full", action="store_true",
                            help="prefer the unlimited .full database when present")

    info = sub.add_parser("info", help="summarise the loaded database")
    add_db_flags(info)
    info.set_defaults(func=cmd_info)

    build = sub.add_parser("build", help="compile a database")
    build.add_argument("-m", "--mode", choices=sorted(MODES), default="default",
                       help="build size / quality (see: urduofdani.py modes)")
    build.add_argument("-o", "--output", default=None, help="output .gz path")
    build.add_argument("--min-len", type=int, default=2)
    build.add_argument("--max-len", type=int, default=40)
    build.add_argument("--keep-diacritics", action="store_true")
    build.add_argument("--verify", action="store_true", help="verify right after building")
    build.set_defaults(func=cmd_build)

    verify = sub.add_parser("verify", help="run the integrity checks")
    add_db_flags(verify)
    verify.add_argument("-e", "--export", default=None, metavar="TXT",
                        help="also write the plain single-line text")
    verify.set_defaults(func=cmd_verify)

    bench = sub.add_parser("bench", help="benchmark cold load")
    add_db_flags(bench)
    bench.add_argument("-r", "--runs", type=int, default=5)
    bench.set_defaults(func=cmd_bench)

    search = sub.add_parser("search", help="prefix search (autocomplete)")
    add_db_flags(search)
    search.add_argument("query")
    search.add_argument("-l", "--limit", type=int, default=15)
    search.add_argument("-c", "--contains", action="store_true",
                        help="fall back to substring search when no prefix matches")
    search.set_defaults(func=cmd_search)

    check = sub.add_parser("check", help="test whether a word is in the dictionary")
    add_db_flags(check)
    check.add_argument("word")
    check.set_defaults(func=cmd_check)

    suggest = sub.add_parser("suggest", help="print autocomplete suggestions on one line")
    add_db_flags(suggest)
    suggest.add_argument("prefix")
    suggest.add_argument("-l", "--limit", type=int, default=8)
    suggest.set_defaults(func=cmd_suggest)

    export = sub.add_parser("export", help="write the plain single-line .txt")
    add_db_flags(export)
    export.add_argument("output")
    export.set_defaults(func=cmd_export)

    rnd = sub.add_parser("random", help="print random words (for demos / tests)")
    add_db_flags(rnd)
    rnd.add_argument("-n", "--count", type=int, default=10)
    rnd.set_defaults(func=cmd_random)

    test = sub.add_parser("test", help="run the bundled test suite")
    test.add_argument("-v", "--verbose", action="store_true")
    test.set_defaults(func=cmd_test)

    modes = sub.add_parser("modes", help="explain the build modes")
    modes.set_defaults(func=cmd_modes)

    audit = sub.add_parser("audit", help="run every audit gate (tests, artifacts, docs, tiers)")
    audit.set_defaults(func=cmd_audit)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    _utf8_console()
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\n[urduofdani] interrupted", file=sys.stderr)
        return 130
    except SystemExit as exc:                    # from _resolve_db
        print(exc.code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
