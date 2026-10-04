# Roadmap & Audit Protocol

Two things live here: **how we keep the project honest** (the audit protocol, run
every round) and **what comes next**.

## The audit protocol

Every change is checked by independent gates. All of them are stdlib-only and run
in seconds, so they belong in every local session — not just in CI. One command
runs the lot:

```bash
python urduofdani.py audit      # tests · verify · verify --full · docs · tier table · examples
```

| # | Gate | Command | Passes when |
|---|---|---|---|
| 1 | Test suite | `python run_tests.py` | 63 tests, 0 failures (≈2 s) |
| 2 | Artifact integrity | `python urduofdani.py verify` / `--full` | 8/8 checks, exit 0 |
| 3 | Documentation | `python tools/audit_docs.py` | anchors, links, counts and CLI surface all match |
| 4 | Word audit | `python tools/audit_words.py` / `--full` | 0 structural violations, 0 junk, 0 missing regression words |
| 5 | Reproducibility | `python urduofdani.py build --mode default -o /tmp/x.gz && cmp /tmp/x.gz urdu_database.txt.gz` | byte-identical artifact |
| 6 | Examples | `python examples/quickstart.py` · `…/autocomplete_app.py --list` | both run headless |

Additional round-level checks:

```bash
python tools/measure_tiers.py                 # every tier still builds and measures
python tools/measure_tiers.py --check README.md   # README table is not stale
python examples/quickstart.py                 # the documented tour actually runs
python examples/autocomplete_app.py --list    # the GUI example starts headless
```

### Audit log

| Round | Found | Fixed |
|---|---|---|
| 1 — engine & API | 1 FAIL + 9 WARN: `iter_urdu_words` dropped bytes split across block boundaries; five dead constants (two of them orphaned seed banks); `verify` accepted an empty database; `extend()` silently fused multi-word input | incremental UTF-8 decoder + boundary regression test; dead code deleted, orphaned seeds recovered (+261 words); 8-check verifier; `extend(strict=True)` + `last_extend_skipped` |
| 2 — interface & docs | `--mode` build crashed on `blurb`; docs claimed 24,809/113,793/375; three badge/TOC anchors dead; `verify`/`benchmark` spammed stdout for library callers | `build_kwargs()` + mode-mapping test; README/CONTRIBUTING regenerated from measurement; anchors fixed and enforced by `audit_docs.py`; `quiet=True` |
| 3 — sacred-name data | the pool contained inflected forms (`نبیوں`, `پیغمبروں`) which therefore shipped; the guard deleted 54 real words (`ملکوں`, `شہیدوں`, `مقدمے`, `برے`, …) | canonical-only pool (373 names) + pool invariant test; documented homograph exception (`SACRED_HOMOGRAPH_STEMS`) |
| 4 — new code paths | `verify` crashed with a traceback on a non-gzip file; `build --mode mini` silently overwrote the shipped `urdu_database.txt.gz` | non-gzip input is now a failed check (exit 1, no traceback); per-mode default output names keep the release artifact safe |
| 5 — all words | 1,125 structural violations + thousands of junk tokens: blind head attachment (`آلوخانہ`, `آنکھگاہ`, `آلودگیگودام`), blind agentive cross product (`اسٹیڈیمفروش`, `آبپاشیدان`), silent phrase fusion (`اٹھائی والا` → `اٹھائیوالا`), infinitive/noun "verb roots" (`آرامنےوالا`, `کامنا`), noun sections wearing adjective suffixes (`گردنپن`, `ہڑتالگی`), and one real-word loss (`کتابدار`, `گنگنانا`) | curated host tables for every head/suffix (`HEAD_HOSTS`, `AGENTIVE_SUFFIX_HOSTS`, `LOAN_PLURAL_HOSTS`), fusion allowed only in hand-written banks, roots repaired or refused, per-section suffix rules, compound-aware structural rules; `tools/audit_words.py` (3 layers) now gates every round and the counts became honest: default 25,320 → **15,848** all-audited words, full 116,184 → **17,539** |

## Now / next

### Next round (audit 6)

* **Wildcard & fuzzy lookup** (`search --fuzzy`, edit distance on the prefix index) for the spell-correction use case.
* **Domain packs** — ship optional `.gz` overlays (medical, legal, engineering) instead of growing the default build.
* **Benchmark harness** — record `measure_tiers` output per commit and chart regressions.
* **Packaging** — ✅ `pyproject.toml` + console scripts (`urduofdani`, `urduofdani-engine`) with `pipx install .`; a pre-built release asset for non-Python users is still open.
* **Over-generation watch-list** — the audit keeps `-یں` plurals broad so real feminine plurals (`دکانیں`, `زمینیں`) survive; tokens such as `شہیدیں` / `انگوریں` are legal-shaped but rare, and a per-word gender table is the honest way to tighten them.

### Later / ideas

* Transliteration-aware suggestions (`kmpyutr` → `کمپیوٹر`).
* Frequency-ranked autocomplete (word-frequency list layered on the existing index).
* Additional orthography normalisations for Pashto/Sindhi loan spellings.
* Optional `mmap`-friendly uncompressed tier for very small embedded targets.

### Explicitly not planned

* **Third-party dependencies.** Stdlib only — that *is* the pitch.
* **Junk tolerance for the sake of a bigger number.** Generic affix stacking was tried and retired: it produces `سکریندکان`, `آلودگر`, `نیلامند`. Any future growth stays section-gated and curated.
* **Shipping the recall tier.** 2.6M tokens are available on demand (`--mode recall`) but never presented as a quality claim.
