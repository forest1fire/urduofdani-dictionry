#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: run_tests.py
==========================
Windows-friendly test entry point (no pytest required).

::

    python run_tests.py            # run the whole suite
    python run_tests.py -v         # verbose
    python run_tests.py -p         # also print the environment banner
    python run_tests.py -q         # only the final result

Exit code is 0 when everything passes, 1 otherwise - so it drops straight into
CI or a pre-commit hook. ``python urduofdani.py test`` calls this for you.
"""

from __future__ import annotations

import argparse
import pathlib
import platform
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _banner() -> None:
    print("urduofdani :: test suite")
    print("  python  : %s" % sys.version.split()[0])
    print("  platform: %s %s" % (platform.system(), platform.release()))
    print("  root    : %s" % HERE)
    try:
        import build_urdu_database as core
        print("  version : %s" % core.SCRIPT_VERSION)
        for name in (core.DB_FILENAME, "urdu_database.full.txt.gz"):
            path = HERE / name
            print("  db      : %-26s %s" % (
                name, "%s bytes" % f"{path.stat().st_size:,}" if path.exists() else "not built"))
    except Exception as exc:                      # pragma: no cover
        print("  engine  : import failed -> %r" % exc)
    print("-" * 66)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="run_tests", description="Run the urduofdani test suite.")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose test output")
    parser.add_argument("-p", "--print-env", action="store_true", help="print the environment banner")
    parser.add_argument("-k", "--pattern", default="test*.py", help="test file pattern")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="only print the final result (used by urduofdani.py audit)")
    args = parser.parse_args(argv)

    if args.print_env:
        _banner()

    loader = unittest.TestLoader()
    suite = loader.discover(str(HERE / "tests"), pattern=args.pattern, top_level_dir=str(HERE))
    if args.quiet:
        import contextlib
        import io
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            result = unittest.TextTestRunner(verbosity=0).run(suite)
        lines = [l.strip() for l in stream.getvalue().splitlines()
                 if l.strip() and set(l.strip()) != {"-"}]
        ran = next((l for l in lines if l.startswith("Ran ")), "no tests run")
        status = next((l for l in reversed(lines) if l.startswith(("OK", "FAILED"))), "")
        print("%s  %s" % (ran, status))
        if result.wasSuccessful():
            print("all tests passed")
    else:
        result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
