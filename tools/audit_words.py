#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: tools/audit_words.py
==================================
Audit **every word**, not just the file format.

Three layers, cheapest first:

1. **Structural rules** - things a real Urdu word never does:
   presentation-form codepoints, doubled plural markers ("بازؤنوں"), a
   derivational suffix on an already-inflected stem ("جوتوںی"), a repeated
   agentive tail ("فنکارگر"), ``آ`` in a non-initial position ("کمآسان").
2. **Curated regression lists** - real words that must exist in the shipped
   build, and known junk that must not exist in *any* tier. These encode every
   bug the audit has caught so far, so a refactor cannot quietly bring one back.
3. **Fluency review queue** (informational) - a bigram model trained on the
   curated seeds ranks the most unusual generated tokens. It is a *review* aid,
   not a gate: it also ranks rare-but-real short words low, so a human decides.

    python tools/audit_words.py                 # shipped default build
    python tools/audit_words.py --full          # the unlimited build
    python tools/audit_words.py --queue 25      # show the review queue
    python tools/audit_words.py --json          # machine-readable summary

Exit 1 on any structural violation or any regression-list mismatch.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import build_urdu_database as core          # noqa: E402

# --------------------------------------------------------------------------- #
# The regression lists: every entry is a bug that was once shipped (or a word a
# guard once deleted). Keep them small, real and commented.
# --------------------------------------------------------------------------- #
MUST_EXIST: tuple[str, ...] = (
    # plurals and obliques of ordinary nouns
    "کتابیں", "کتابوں", "لڑکوں", "لڑکیاں", "جوتے", "بکریاں", "دلوں", "خطیں", "غموں",
    "بموں", "زروں", "سروں", "پلوں", "فنوں", "آموں", "گھروں", "بچوں", "آنکھیں",
    "دوائیں", "پھولوں", "دریاؤں", "چڑیاں", "چڑیوں", "مائیں", "دھواں", "پاؤں", "گاؤں",
    # loanword plurals that Urdu really uses
    "کمپیوٹرز", "لنکس", "فائلیں", "ٹچز", "موبائلوں", "اسٹیشنز",
    # homograph divine names keep their everyday inflections
    "ملکوں", "شہیدوں", "مقدمے", "حکموں", "وکیلوں", "برے",
    # curated real words that look like junk to a conservative guard
    "چائےخانہ", "دواخانہ", "ہفتےوار", "مہینےوار", "دلدار", "سردار", "کارمند",
    "کارگر", "ہنرمند", "کتابدار", "دکاندار", "پھولفروش", "باغبان", "قلمدان",
    "ریشےدار", "ریشمی", "کمپیوٹر", "کتاب", "میز", "باغ",
    # curated place / occupation compounds (round 3 of the word audit)
    "مہمانخانہ", "ورزشگاہ", "تفریحگاہ", "عبادتگاہ", "شکارگاہ", "زیارتگاہ", "کھیلمیدان",
    "سبزیمنڈی", "مچھلیمنڈی", "اناجگودام", "پھولبازار", "کتاببازار", "دودھفروش",
    "مچھلیفروش", "سبزیفروش", "کتابفروش", "زیورساز", "گھڑیساز", "عقلمند", "دردمند",
    "خدمتکار", "دربان", "چائےدکان", "جوتادکان", "نمکدان", "گلدان", "اٹھانےوالا",
    "کرنےوالا", "ابھرنا", "گنگنانا", "بونا", "اٹھائی", "پڑھائی",
    # sacred names (the protected set)
    "اللہ", "رحمن", "محمد", "علی", "فاطمہ", "حسین", "زینب", "ابوبکر", "بلال",
)

MUST_NOT_EXIST: tuple[str, ...] = (
    # inflected sacred names
    "اللہوں", "محمدوں", "علیوں", "حسینوں", "فاطمہوں", "نبیوں", "پیغمبروں", "رسولوں",
    # presentation-form codepoints (U+FE85) instead of a real ؤ
    "بازﺅں", "دریاﺅں", "بھنوﺅں",
    # doubled plural markers / double pluralisation
    "بازؤنوں", "جوتےاں", "بچےاں", "بکریاںی", "کتابیںی", "چڑییوں",
    "مانوں", "اےاں", "کوےاں",
    # derivational suffix on an inflected stem
    "کیفےدان", "انڈےخانہ", "جوتےگھر", "ریشےی", "انڈےباغ", "اولےگاہ",
    # repeated agentive tails / impossible heads
    "فنکارگر", "فنکاردار", "کارفروش", "میداندار",
    # blind section-wide head attachment ("آلوخانہ" class) - fixed in round 3
    "آلوخانہ", "آنکھگاہ", "آلودگیگاہ", "آلودگیگودام", "آبپاشیگودام", "آوازمنڈی",
    "اجرتمنڈی", "اجرتدکان", "آرڈرمنڈی", "آرڈردکان", "آسمانگھر", "آلوگھر", "آنکھگھر",
    # blind agentive cross product ("اسٹیڈیمفروش" class)
    "اسٹیڈیمفروش", "آبپاشیدان", "اخبارساز", "آٹاساز", "بلبفروش", "بوتلفروش",
    "انجندان", "اشتہارگر", "باغفروش", "اسٹیڈیمساز", "اخباردان", "فنکاریفروش",
    # noun treated as a verb root ("آرامنےوالا" class)
    "آرامنےوالا", "انکارنےوالا", "آرامنا", "کامنا", "یادنا", "ہنسیوالا", "آرامتا",
    # spaced phrase silently fused into one token ("اٹھاائی والا" class)
    "اٹھاائیوالا", "اٹھائیوالا", "بوناائیوالا", "صافکرنےوالا", "ضدکرنےوالا",
    # two-letter fragments that are not words on their own
    "اپس", "اپز", "آنز", "آنوس", "بلز", "زپس", "سمز",
    # junk from the old adjective/plural rules
    "ادنیی", "اعلیی", "چڑیؤں", "انیمییوں", "دھنیؤں", "کیمیؤں",
)

# Saaf exceptions to the structural rules (real words that break them):
STRUCTURAL_EXCEPTIONS: dict[str, set[str]] = {
    # real compounds that legitimately carry a non-initial آ after a prefix
    # real words with a non-initial آ: القرآن، برآمد/درآمد (import-export) and قرآن
    "آ not word-initial": {"الآخر", "برآمد", "برآمدی", "برآمدیں", "برآمدات",
                           "برآمدگاہ", "برآمدخانہ", "برآمددکان", "برآمدکنندہ",
                           "درآمد", "درآمدی", "درآمدیں", "درآمدات",
                           "قرآن", "قرآنی", "قرآنوں", "قرآنیں", "قرآنپاک"},
}


# --------------------------------------------------------------------------- #
# 1. structural rules
# --------------------------------------------------------------------------- #
VOWELS = set("اآویےہںھۃئء")   # incl. hamza seats: they never start a real cluster

# A long consonant run is only suspicious when the *generator* built it. Real
# words like آرکسٹرا / اسسٹنٹ / اسمگلنگ are curated seeds, and ابنمسعود / اثرمند
# are two real morphemes joined (ابن+مسعود، اثر+مند). So the rule is
# compound-boundary aware instead of a rising numeric threshold.
_SEED_CACHE: "set[str] | None" = None
_INFLECT = ("وں", "یں", "اں", "ات", "ے", "ؤں")


def _blob(value, out: "list[str]") -> None:
    if isinstance(value, str):
        out.extend(value.split())
    elif isinstance(value, dict):
        for key, item in value.items():
            _blob(key, out)
            _blob(item, out)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _blob(item, out)


def _collect_curated(value, into: "set[str]") -> None:
    """Recursively gather hand-written vocabulary out of the compiler's data."""
    if isinstance(value, str):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _collect_curated(key, into)
            _collect_curated(item, into)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _collect_curated(item, into)


def seed_words() -> "set[str]":
    """Every hand-written token in the project: banks, host tables, KEEP_FORMS.

    The structural rules must judge *generated* tokens, so the curated
    vocabulary they are built from counts as known-good by definition.
    """
    global _SEED_CACHE
    if _SEED_CACHE is None:
        words: set[str] = set()
        for name, value in vars(core).items():
            if name.startswith("_") or name not in name.upper():
                continue
            blob: "list[str]" = []
            _blob(value, blob)
            for token in blob:
                folded = core.fold_seed(token)
                if folded:
                    words.add(folded)
        for entries in core.LexiconForge()._sections().values():
            for entry in entries:
                folded = core.fold_seed(entry)
                if folded:
                    words.add(folded)
        _SEED_CACHE = words
    return _SEED_CACHE


def morphology() -> "set[str]":
    """Affixes and compound heads the compiler is allowed to glue on."""
    return ({"ی", "پن", "گی", "ات", "ت", "ں", "وں", "یں", "اں", "ے", "ؤں", "ائی",
             "یت", "انہ", "ناک", "والا", "والی", "ہار", "اوٹ", "انا", "ز", "س",
             "ئی", "ئ", "ہار", "وار", "دان", "پور", "آباد"}
            | set(core.HEAD_HOSTS) | set(core.AGENTIVE_SUFFIX_HOSTS)
            | set(core.KEEP_FORMS))


def _known(part: str, seeds: "set[str]", morph: "set[str]") -> bool:
    if part in seeds or part in morph:
        return True
    for marker in _INFLECT:
        if not part.endswith(marker):
            continue
        stem = part[:-len(marker)]
        # alef/he-final stems lose their ending in the plural/oblique
        # (آرکسٹرا -> آرکسٹروں، کمرہ -> کمرے)
        if stem in seeds or stem + "ا" in seeds or stem + "ہ" in seeds:
            return True
    return False


def is_clean_compound(word: str, seeds: "set[str]", morph: "set[str]",
                      depth: int = 3) -> bool:
    """True when *word* is curated vocabulary, or real morphemes stacked.

    Handles chains, so "برکتمندوں" (برکت + مند + ں) counts as clean while a
    generated glue token such as "آرڈردکان" (آرڈر + دکان, neither an affix nor a
    listed host) still fails.
    """
    if word in seeds:
        return True
    if _known(word, seeds, morph):
        return True
    if depth <= 0:
        return False
    for i in range(1, len(word)):
        left, right = word[:i], word[i:]
        if not _known(right, seeds, morph):
            continue
        if _known(left, seeds, morph) or is_clean_compound(left, seeds, morph, depth - 1):
            return True
    return False


def structural(word: str, seeds: "set[str] | None" = None,
               morph: "set[str] | None" = None) -> list[str]:
    """Everything a real Urdu word never does."""
    issues: list[str] = []
    if any(0xFB50 <= ord(ch) <= 0xFEFF for ch in word):
        issues.append("presentation-form codepoint")
    if "آ" in word[1:]:
        # Real Urdu does hold a medial آ: قرآن، کوآلا، برآمد، مظفرآباد. It is only
        # suspicious when the generator invented it, so curated/morpheme-built
        # vocabulary is exempt (the same escape hatch as the cluster rule).
        built_from_real_parts = (seeds is not None
                                 and is_clean_compound(word, seeds, morph or set()))
        if not built_from_real_parts:
            issues.append("آ not word-initial")
    if re.search(r"([\u0621-\u06FF])\1\1", word):
        issues.append("same letter 3x")
    for marker in ("وںیں", "یںوں", "وںی", "یںی", "اںی", "وںوں", "یںیں"):
        if marker in word:
            issues.append("marker+suffix %s" % marker)
    # "اتے" is a normal verb ending (الجھاتے، بناتے); only a *doubled* marker
    # ("جوتےاتے", "بازوںاتے") is impossible.
    for doubled in ("وںاتے", "یںاتے", "اںاتے", "ےاتے"):
        if doubled in word:
            issues.append("marker+suffix %s" % doubled)
    for tail in ("داردار", "گرگر", "دانдан", "سازساز"):
        if tail in word:
            issues.append("repeated tail %s" % tail)
    run = 0
    for ch in word:
        if ch in VOWELS:
            run = 0
        else:
            run += 1
            if run >= 5:                    # 4-runs are normal in loanwords: آرکسٹرا
                if seeds is not None and is_clean_compound(word, seeds, morph or set()):
                    break                   # curated seed or morpheme-joined compound
                issues.append("5+ consonant cluster")
                break
    if re.search(r"[\u064b-\u0652\u0670\u06d6-\u06ed]", word):
        issues.append("stray diacritic")
    return [i for i in issues if word not in STRUCTURAL_EXCEPTIONS.get(i, set())]


# --------------------------------------------------------------------------- #
# 2. fluency review queue (informational)
# --------------------------------------------------------------------------- #
def seed_corpus() -> list[str]:
    forge = core.LexiconForge()
    words: list[str] = []
    for entries in forge._base_sections().values():
        for entry in entries:
            words.extend(entry.split())
    return [w for w in (core.fold_seed(w) for w in words) if core.is_valid_token(w)]


def train(seeds: list[str]):
    bounds = "\u0000"
    bigrams: Counter = Counter()
    unigrams: Counter = Counter()
    for word in seeds:
        padded = bounds + word + bounds
        for a, b in zip(padded, padded[1:]):
            bigrams[a + b] += 1
            unigrams[a] += 1
    total_bi = sum(bigrams.values())
    total_uni = sum(unigrams.values())
    vocab = len(unigrams) + 1
    bi = {k: math.log(v / (total_bi + vocab)) for k, v in bigrams.items()}
    uni = {k: math.log(v / (total_uni + vocab)) for k, v in unigrams.items()}
    return bi, uni


def fluency(word: str, bi, uni) -> float:
    padded = "\u0000" + word + "\u0000"
    total = 0.0
    for a, b in zip(padded, padded[1:]):
        total += bi.get(a + b, uni.get(a, -12.0) * 0.5)
    return total / max(1, len(padded) - 1)


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def audit(path: Path, queue: int) -> dict:
    words = core.load_urdu_database(path, verify_checksum=True)
    word_set = set(words)

    seeds = seed_words()
    morph = morphology()
    structural_hits = {}
    for word in words:
        issues = structural(word, seeds, morph)
        if issues:
            structural_hits[word] = issues

    missing = [w for w in MUST_EXIST if w not in word_set]
    present_junk = [w for w in MUST_NOT_EXIST if w in word_set]

    bi, uni = train(seed_corpus())
    scored = sorted(((fluency(w, bi, uni), w) for w in words), key=lambda pair: pair[0])
    return {
        "database": path.name,
        "bytes": path.stat().st_size,
        "tokens": len(words),
        "structural": {w: issues for w, issues in list(structural_hits.items())[:200]},
        "structural_count": len(structural_hits),
        "missing_real_words": missing,
        "junk_present": present_junk,
        "review_queue": [(round(s, 2), w) for s, w in scored[:queue]],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="audit every word in an urduofdani tier")
    ap.add_argument("-d", "--db", default=None, help="database .gz to audit")
    ap.add_argument("--full", action="store_true", help="audit urdu_database.full.txt.gz")
    ap.add_argument("--queue", type=int, default=0, help="show N unusual words for review")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args(argv)

    db = Path(args.db) if args.db else REPO / ("urdu_database.full.txt.gz" if args.full
                                               else core.DB_FILENAME)
    if not db.exists():
        print("[audit_words] missing database: %s" % db, file=sys.stderr)
        return 2

    result = audit(db, args.queue)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("urduofdani :: word audit - %s" % result["database"])
        print("=" * 68)
        print("  tokens               : %s" % f"{result['tokens']:,}")
        print("  structural violations: %s" % result["structural_count"])
        print("  missing real words   : %s" % (result["missing_real_words"] or "none"))
        print("  junk still present   : %s" % (result["junk_present"] or "none"))
        if result["structural"]:
            print("-" * 68)
            for word, issues in list(result["structural"].items())[:15]:
                print("  %-22s %s" % (word, ", ".join(issues)))
        if result["review_queue"]:
            print("-" * 68)
            print("  review queue (unusual tokens - a human decides):")
            for score, word in result["review_queue"]:
                print("    %-22s %6.2f" % (word, score))
        print("=" * 68)

    ok = (result["structural_count"] == 0 and not result["missing_real_words"]
          and not result["junk_present"])
    print("[audit_words] %s  (%s)" % ("PASS" if ok else "FAIL",
                                      "every structural rule and regression list is clean"
                                      if ok else "see the report above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
