# Changelog

All notable changes to **urduofdani** are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] — 2026-10-04

**The word audit round.** Every token in both shipped tiers is now checked by
`tools/audit_words.py`, and the whole lexicon was rebuilt from what it found.

### Added

* **`tools/audit_words.py`** — three layers over every token: structural rules
  (presentation-form codepoints, medial `آ`, 5+ consonant runs, doubled plural
  markers, suffix-on-inflected-stem, repeated agentive tails, stray diacritics),
  curated regression lists (~55 real words that must exist, ~60 junk tokens that
  must never appear) and an informational fluency queue. It is gate #4 of
  `python urduofdani.py audit`, so junk cannot come back unnoticed.
* **`urduofdani_engine.py`** — a stdlib-only, drop-in engine artifact
  (`UrduEngine`, `find_database`, `read_database`, `canonical`, `FALLBACK_WORDS`)
  with a CLI (`--info/--bench/--check/--suggest/--spell`). It auto-detects the
  compact tier and never lags: ~9 ms cold load on the 15,848-word compact build.
* **Compact front-coded tier** — `--format compact` writes
  `urdu_database.compact.gz` (15,848 words in **16.8 KB** vs 43.9 KB plain, ~6.5 ms
  load) and `urdu_database.full.compact.gz` (17,539 words / 18.0 KB). The codec is
  `URDUFC1 <count> <sha16>` + base-36 shared-prefix entries, checksum-enforced.
* Compiled-in curated tables with their reasons written down: `HEAD_HOSTS`,
  `AGENTIVE_SUFFIX_HOSTS`, `LOAN_PLURAL_HOSTS`, `KEEP_FORMS`, `NON_VERB_ROOTS`.
* `tests` grew to 63: word-audit regression tests (junk classes, real-word
  survival, sacred-name invariant, loan plurals) plus the earlier suites.

### Changed

* **Honest counts.** The audit proved that a large share of the old builds was
  generated glue, so the numbers moved: default **25,320 → 15,848** audited words
  (43.9 KB, 2.0 ms), full **116,184 → 17,539** (48.1 KB), recall 2,592,831.
  Nothing was removed for being rare — only for being unbuildable as a real word.
* **Structural rules are morpheme-aware.** Long consonant runs and medial `آ` are
  judged after checking the token is a curated seed or a real morpheme chain, so
  `آرکسٹرا`, `ابنمسعود`, `برکتمندوں`, `قرآن` pass while generator glue still fails.
* `--mode` blurbs, README, badges and the regenerated raster assets all report the
  measured numbers.

### Fixed

* **Blind head attachment** — `خانہ/گاہ/دکان/منڈی/بازار/گودام/میدان/اڈہ/کھیت` were
  glued onto whole sections (`آلوخانہ`, `آنکھگاہ`, `آلودگیگودام`, `اجرتمنڈی`,
  `آرڈرمنڈی`). Each head now has a curated host list (89 real compounds).
* **Blind agentive cross product** — 226 stems × 10 suffixes produced
  `اسٹیڈیمفروش`, `آبپاشیدان`, `اخبارساز`, `انجندان`, `بلبفروش`. Curated per-suffix
  host tables replace the product.
* **Silent phrase fusion** — `_add()` fused any spaced input (`"اٹھائی والا"` →
  `اٹھائیوالا`, `صافکرنےوالا`). Fusion is now allowed only inside hand-written
  banks; generators can never fuse.
* **Verb banks that were not verbs** — infinitives and nouns listed as roots minted
  `آرامنےوالا`, `آرامنا`, `کامنا`, `یادنا`, `سپردتا`, `مستردتا`. Roots are repaired
  (`ابھرنا → ابھر`, `بڑبڑ → بڑبڑا`) or refused.
* **Noun sections wearing adjective suffixes** — `گردنپن`, `ہڑتالگی`, `کمانڈرپن`,
  `کمانڈرناک` are gone; a section may only use its own rule's morphology.
* **`ہ`-final plurals** — `بندرگاہ` gave `بندرگاے`/`بندرگاوں`; vowel-`ہ` stems now
  keep the `ہ` (`بندرگاہیں`, `بندرگاہوں`) while consonant-`ہ` stems still elide it
  (`کمرے`, `کمروں`).
* **Real words restored** after the guards got strict: `کتابدار`, `گنگنانا`,
  `دربان`, `گلدان`, `عجائبگھر`, `اسٹیشنز`, `کمپیوٹرز`, `موبائلز`, `ٹکٹس`, `پنکھا`
  family derivations and the place compounds (`مہمانخانہ`, `ورزشگاہ`, `تفریحگاہ`,
  `عبادتگاہ`, `شکارگاہ`, `زیارتگاہ`, `سبزیمنڈی`, `مچھلیمنڈی`, `اناجگودام`).
* **Sacred-name guarantee completed** — the Anbiya bank itself listed the inflected
  `نبیوں` / `پیغمبروں`, which the never-inflect guard then protected. Inflected
  entries removed (387 entries → 373 unique canonical names) and the invariant is
  tested for every name × 8 markers.
* **`--mode exhaustive/wide/full`** no longer stack two compound heads
  (`انجینئرگھرگر`, `ریتسازفروش`) or stack suffixes on loanwords.

## [3.0.0] — 2026-10-04

### Added

* **Front door CLI** — `python urduofdani.py {info,build,verify,bench,search,check,suggest,export,random,test,modes}` with script-friendly exit codes (0 ok, 1 check failed, 2 database missing) and a single `--mode` ladder
  (`mini` 3,000 · `default` 25,320 · `exhaustive` 43,043 · `wide` 57,806 · `full` 116,184 · `recall` 2,636,229).
* **Test suite** — `tests/test_urduofdani.py` (60 tests) plus `run_tests.py`, covering orthography folding, morphology, the sacred-name guarantee, build determinism, gzip format, multibyte stream boundaries, the engine, the CLI and the shipped artifacts.
* **Examples** — `examples/quickstart.py` (guided tour) and `examples/autocomplete_app.py` (complete Tkinter autocomplete app with a headless `--list` mode and a PyInstaller recipe).
* **Tools** — `tools/measure_tiers.py` (regenerates the README benchmark table, `--check README.md` fails on drift) and `tools/audit_docs.py` (anchor/link/number/CLI documentation audit).
* **CI** — `.github/workflows/ci.yml`: tests on Linux (3.9/3.11/3.13) **and Windows**, an artifact determinism job (rebuild must be byte-identical), and a docs job.
* Library entry points now accept `quiet=True` (`verify_database`, `benchmark`) so programmatic callers get results without console output.
* `SACRED_HOMOGRAPH_STEMS`, `EXTRA_TIER_SEEDS`, `__all__` exports.

### Fixed

* **Sacred pool could contain inflected forms** — `نبیوں` and `پیغمبروں` sat in `NABI_NAMES`, so the guard treated them as canonical and shipped them. The pool is now canonical-only (373 unique names), and a test asserts the invariant.
* **The never-inflect guard deleted real words** — 54 legitimate tokens (`ملکوں`, `شہیدوں`, `مقدمے`, `حکموں`, `برے`, …) were rejected because divine names are also ordinary nouns. The documented homograph exception restores them; proper names stay fully protected.
* **`iter_urdu_words` corrupted multibyte tokens** when a character straddled a block boundary (`errors="ignore"` → incremental UTF-8 decoder, regression-tested at block sizes 7/13/64/1024).
* **`--mode` build crashed** (`TypeError: unexpected keyword argument 'blurb'`) — mode tables are now split into builder kwargs and display text, with a test that every mode maps onto real builder parameters.
* Recovered seed banks that a refactor had orphaned (`FOOD_EXTRA_WORDS`, `HOUSE_EXTRA_WORDS` → `EXTRA_TIER_SEEDS`), +261 words.
* `attach_suffix` orthography (`دریا` + `ی` → `دریائی`) and loan-word plurals (`لنکس`).
* Missing/unreadable database now exits **2** with `database not found: …` instead of a traceback.
* A corrupt or non-gzip file passed to `verify` is reported as a failed check (exit 1) instead of raising `BadGzipFile`.
* `build` only writes the shipped `urdu_database.txt.gz` for `--mode default`; other tiers get their own default file name, so a test build can never clobber the release artifact.
* Dead code removed: `LOAN_SECTIONS`, `VERB_NOUN_SUFFIXES`, `CONCRETE_SECTIONS`; `verify_database` grew from 6 to 8 checks (non-empty database, sacred-name integrity).

### Changed

* Committed artifacts rebuilt with the current engine: `urdu_database.txt.gz` (25,320 words / 73.0 KB) and `urdu_database.full.txt.gz` (116,184 words / 323.2 KB). Both are byte-reproducible.
* README rewritten around the measured numbers (regenerated by `tools/measure_tiers.py`), broken anchor and stale-count drift fixed.
* Repository layout cleaned: engine + front door + runner at the root, everything else under `tests/`, `examples/`, `tools/`, `assets/`.

## [2.0.0] — 2026-10-04

### Added

* **Sacred names** — 373 protected names across four dedicated sections: `allah` (213 entries), `nabi` (51), `ahlbayt` (82) and `sahaba` (41); never pluralised, suffixed, prefixed or compounded in any mode.
* A never-inflect compiler guard (`is_sacred_derivative`) enforced on top of the section rules, verified on every shipped artifact.

## [1.1.0] — 2026-10-04

### Added

* **Unlimited mode** — `--unlimited`, `--depth 1-4` and the machine-tier `--recall`; the shipped `.full` build (113k words at the time) and a 2.6M-token recall tier.
* 2.3× larger default lexicon (24,589 words) with curated agentive hosts, market heads and two-head compounds.

## [1.0.0] — 2026-10-04

### Added

* First release: `build_urdu_database.py` compiles a curated Urdu lexicon into a single-space-tokenized, gzip-compressed database (`urdu_database.txt.gz`), plus the `UrduEngine` runtime (O(1) membership, O(log n) autocomplete), the integrity verifier, the built-in benchmark and the Windows-first documentation.

[3.0.0]: https://github.com/forest1fire/urduofdani-dictionary/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/forest1fire/urduofdani-dictionary/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/forest1fire/urduofdani-dictionary/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/forest1fire/urduofdani-dictionary/releases/tag/v1.0.0
