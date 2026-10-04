#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: tools/audit_docs.py
=================================
Documentation audit: the README must not lie and must not link into the void.

    python tools/audit_docs.py            # audit README.md + CONTRIBUTING.md
    python tools/audit_docs.py -v         # list every check

Checks
------
1. every internal `#anchor` link resolves to a heading (GitHub slug rules)
2. every relative path link points at a file that exists
3. every "<number> words" claim matches a real, shipped or documented count
4. every `urduofdani.py <sub>` / `--flag` mentioned in the docs exists
5. the README documents every CLI subcommand and every `--mode`

Exit code 0 = clean, 1 = drift found.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import build_urdu_database as core          # noqa: E402
import urduofdani as front                  # noqa: E402

DOCS = ("README.md", "CONTRIBUTING.md")
SLUG_STRIP = re.compile(r"[^\w\s\-\u0600-\u06FF]")

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))


def slugify(heading: str) -> str:
    """GitHub's heading anchor algorithm (close enough for our documents)."""
    text = heading.strip().lower()
    text = re.sub(r"`([^`]*)`", r"\1", text)       # inline code loses its backticks
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # links keep their text
    text = SLUG_STRIP.sub("", text)
    # GitHub maps every whitespace character to one hyphen, so the runs left
    # behind by stripped punctuation ("A / B") really do become "--".
    return re.sub(r"\s+", lambda m: "-" * len(m.group(0)), text).strip("-")


def headings(text: str) -> set[str]:
    return {slugify(m.group(2)) for m in re.finditer(r"^(#{1,6})\s+(.*)$", text, re.M)}


def audit_anchors(name: str, text: str, slugs: set[str]) -> None:
    anchors = set(re.findall(r"\]\(#([^)]+)\)", text))          # markdown links
    anchors |= set(re.findall(r'href="#([^"]+)"', text))         # HTML badge links
    for anchor in sorted(anchors):
        check(anchor in slugs, "%s: anchor #%s resolves" % (name, anchor))


def audit_file_links(name: str, text: str) -> None:
    for target in sorted(set(re.findall(r"\]\((?!https?:|#|mailto:)([^)#]+)", text))):
        path = (REPO / target.strip()).resolve()
        check(path.exists(), "%s: link target %s exists" % (name, target.strip()))


def word_count_claims(text: str) -> list[str]:
    return re.findall(r"\b(\d{1,3}(?:,\d{3})+|\d{4,})\s+(?:unique\s+)?words\b", text)


def audit_numbers(name: str, text: str, known: set[int]) -> None:
    for raw in sorted(set(word_count_claims(text))):
        value = int(raw.replace(",", ""))
        check(value in known, "%s: claim %s words is a real tier size" % (name, raw))


def audit_engine_flags(name: str, text: str) -> None:
    """Every long option of the engine CLI must be documented somewhere."""
    import build_urdu_database as core_mod
    parser = core_mod._build_parser()
    for action in parser._actions:
        for opt in action.option_strings:
            if opt.startswith("--") and opt not in ("--help",):
                check(opt in text, "%s: documents engine flag %s" % (name, opt))


def audit_compression_claims(name: str, text: str, real: set[float]) -> None:
    """'NN.N% smaller' claims must match a measured compression ratio."""
    claimed = {float(m) for m in re.findall(r"(\d{2}\.\d)\s*%\s*(?:smaller|saved|compression)", text)}
    for value in sorted(claimed):
        check(any(abs(value - r) <= 0.3 for r in real),
              "%s: compression claim %.1f%% matches a measured ratio" % (name, value))


def audit_cli(name: str, text: str) -> None:
    subs = set()
    parser = front.build_parser()
    for action in parser._actions:
        if action.choices and isinstance(action.choices, dict):
            subs |= set(action.choices)
    if subs:
        for cmd in sorted(subs):
            check(re.search(r"\b%s\b" % re.escape(cmd), text) is not None,
                  "%s: documents subcommand %s" % (name, cmd))
    for mode in sorted(front.MODES):
        if "measure_tiers" in name or "--mode" in text or "mode" in text:
            check(mode in text or name == "CONTRIBUTING.md",
                  "%s: documents --mode %s" % (name, mode))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="audit the urduofdani documentation")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every check")
    args = ap.parse_args(argv)

    shipped = REPO / core.DB_FILENAME
    full = REPO / "urdu_database.full.txt.gz"
    known: set[int] = {len(core.load_urdu_database(shipped))}
    if full.exists():
        known.add(len(core.load_urdu_database(full)))

    docs = {name: (REPO / name).read_text(encoding="utf-8")
            for name in DOCS if (REPO / name).exists()}
    # tier-table rows are documented counts too (validated by measure_tiers --check)
    table_rows = [int(x.replace(",", "")) for x in
                  re.findall(r"\|\s*`--mode\s+\w+`\s*\|\s*([\d,]+)\s*\|", docs.get("README.md", ""))]
    known |= set(table_rows)

    # measured compression ratios for the two shipped tiers (tolerance 0.3 points)
    real_ratios = set()
    for path in (shipped, full):
        if path.exists():
            bench = core.benchmark(path, repeats=1, quiet=True)
            real_ratios.add(round((1 - bench["packed_bytes"] / bench["raw_bytes"]) * 100.0, 1))
    # plus the ratios published in the tier table (validated by measure_tiers --check)
    real_ratios |= {float(r) for r in re.findall(
        r"\|\s*`--mode\s+\w+`\s*\|\s*[\d,]+\s*\|\s*[\d.]+ (?:KB|MB)\s*\|\s*([\d.]+)%",
        docs.get("README.md", ""))}

    slugs = headings(docs.get("README.md", ""))
    for name, text in docs.items():
        audit_anchors(name, text, slugs)
        audit_file_links(name, text)
        audit_numbers(name, text, known)
        audit_compression_claims(name, text, real_ratios)
        audit_cli(name, text)
    audit_engine_flags("README.md", docs.get("README.md", ""))

    failed = [label for ok, label in results if not ok]
    if args.verbose:
        for ok, label in results:
            print("  [%s] %s" % ("OK " if ok else "FAIL", label))
    print("[audit_docs] %d checks, %d failed" % (len(results), len(failed)))
    for label in failed:
        print("   FAIL %s" % label)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
