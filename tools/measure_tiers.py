#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: tools/measure_tiers.py
====================================
Build every published tier and measure it, so the numbers in README.md can be
regenerated (and checked) instead of hand-typed.

    python tools/measure_tiers.py --table            # markdown table for the README
    python tools/measure_tiers.py --json             # machine-readable dump
    python tools/measure_tiers.py --check README.md  # exit 1 if README numbers drift
    python tools/measure_tiers.py --include-recall   # also build the ~2.6M machine tier

Tiers are written to a temporary directory and deleted unless --keep DIR is given.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import build_urdu_database as core          # noqa: E402
import urduofdani as front                  # noqa: E402

# min / default / exhaustive / wide / full are cheap; recall is opt-in (slow, ~7 MB)
LIGHT_TIERS = ("mini", "default", "exhaustive", "wide", "full")


def measure(mode: str, out_dir: Path) -> dict:
    """Build one tier and return its measurements."""
    path = out_dir / ("urdu_database.%s.txt.gz" % mode)
    t0 = time.perf_counter()
    stats = core.build_urdu_database(output_path=path, verbose=False, **front.build_kwargs(mode))
    build_s = time.perf_counter() - t0
    bench = core.benchmark(path, repeats=3, quiet=True)
    return {
        "mode": mode,
        "blurb": front.MODES[mode]["blurb"],
        "words": int(stats["0_total_words"]),
        "packed_bytes": int(stats["0_packed_bytes"]),
        "raw_bytes": int(stats["0_raw_bytes"]),
        "compression_percent": float(stats["0_compression_percent"]),
        "load_best_ms": round(bench["best_ms"], 2),
        "load_avg_ms": round(bench["avg_ms"], 2),
        "build_s": round(build_s, 2),
        "sha256": stats["0_sha256"],
    }


def as_table(rows: list[dict]) -> str:
    """GitHub-flavoured markdown table, one row per tier."""
    head = ("| tier | words | `.gz` size | saved | cold load | build |\n"
            "|---|---:|---:|---:|---:|---:|\n")
    body = "".join(
        "| `--mode %s` | %s | %s | %.1f%% | %.2f ms | %.2f s |\n" % (
            r["mode"], f"{r['words']:,}", core._human(r["packed_bytes"]),
            r["compression_percent"], r["load_best_ms"], r["build_s"],
        ) for r in rows)
    return head + body


def check_readme(rows: list[dict], readme: Path) -> int:
    """Fail when a documented tier row disagrees with a fresh measurement."""
    text = readme.read_text(encoding="utf-8")
    problems = []
    for r in rows:
        needle = "| `--mode %s` |" % r["mode"]
        line = next((l for l in text.splitlines() if l.startswith(needle)), None)
        if line is None:
            problems.append("README has no row for --mode %s" % r["mode"])
            continue
        if f"{r['words']:,}" not in line:
            problems.append("README %s row says %r, measured %s words"
                            % (r["mode"], line.split("|")[2].strip(), f"{r['words']:,}"))
        if core._human(r["packed_bytes"]) not in line:
            problems.append("README %s row says %r, measured %s"
                            % (r["mode"], line.split("|")[3].strip(), core._human(r["packed_bytes"])))
    if problems:
        print("[measure_tiers] README is out of date:")
        for p in problems:
            print("   - %s" % p)
        print("   regenerate with: python tools/measure_tiers.py --table")
        return 1
    print("[measure_tiers] README tier table matches a fresh build of all %d tiers" % len(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="measure every urduofdani tier")
    ap.add_argument("--table", action="store_true", help="print a markdown table")
    ap.add_argument("--json", action="store_true", help="print JSON")
    ap.add_argument("--check", metavar="README.md", help="exit 1 when README numbers drift")
    ap.add_argument("--include-recall", action="store_true", help="also build the machine tier")
    ap.add_argument("--keep", metavar="DIR", help="keep the built .gz files in DIR")
    args = ap.parse_args(argv)

    modes = list(LIGHT_TIERS) + (["recall"] if args.include_recall else [])
    out_dir = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="urdu_tiers_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        rows = []
        for mode in modes:
            row = measure(mode, out_dir)
            rows.append(row)
            if not (args.table or args.json or args.check):
                print("%-11s %9s words  %9s  %5.1f%%  %6.2f ms" % (
                    mode, f"{row['words']:,}", core._human(row["packed_bytes"]),
                    row["compression_percent"], row["load_best_ms"]))
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        if args.table:
            print(as_table(rows))
        if args.check:
            return check_readme(rows, Path(args.check))
        return 0
    finally:
        if not args.keep:
            shutil.rmtree(out_dir, ignore_errors=True)
        elif not (args.table or args.json or args.check):
            print("kept builds in %s" % out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
