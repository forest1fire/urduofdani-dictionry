# Contributing to urduofdani

Thanks for helping make the fastest little Urdu dictionary on Windows even better.
Everything here is stdlib-only Python — no virtualenv gymnastics, no build system.

```bash
git clone https://github.com/forest1fire/urduofdani-dictionary.git
cd urduofdani-dictionary
python run_tests.py                 # 58 tests, ~3 s, stdlib only
python urduofdani.py verify         # 8 integrity checks on the shipped artifact
python urduofdani.py info           # words, size, RAM, load time
```

One front door covers the everyday work: `info`, `build`, `verify`, `bench`,
`search`, `check`, `suggest`, `export`, `random`, `test` and `modes`
(`python urduofdani.py --help`), plus `audit` — which runs the whole protocol
(tests · artifact verification · docs audit · tier table · examples) in one shot.
`build_urdu_database.py` remains the engine and keeps its own long-standing flags.

## The one rule that must never break

`urdu_database.txt.gz` has a hard **format contract**. Any change must keep it:

| Property | Guarantee |
|---|---|
| Encoding | UTF-8, NFC |
| Lines | exactly one (no `\n`, no `\r`) |
| Separator | exactly one ASCII space |
| Characters | Urdu/Arabic-script letters only — no digits, no Latin, no punctuation |
| Duplicates | none |
| Container | standard gzip (`gzip -t` must pass) |
| Determinism | same seeds ⇒ same SHA-256 (CI rebuilds and compares) |
| Sacred names | all 373 canonical names present, 0 inflected |

`python urduofdani.py verify` proves all of the above and exits non-zero on
failure. **Run it, plus `python run_tests.py`, in every PR** — CI does the same on
Linux and Windows.

## Adding words (the most valuable contribution)

1. Open `build_urdu_database.py`.
2. Add your words to the section constants near the top:
   `CORE_*` / `ADDITIONAL_SEEDS` — e.g. `TECH_WORDS`, `SOCIETY_WORDS`, `ABSTRACT_WORDS`.
3. Keep them **plain, space-separated, digit-free** — the compiler normalises
   Arabic/Persian look-alikes (`ك`→`ک`, `ي`→`ی`, `ة`→`ہ`) and strips harakat for you.
4. Rebuild and verify:

```bash
python build_urdu_database.py --verify --benchmark 5
git diff --stat          # urdu_database.txt.gz should change
```

### Sacred names - read before touching

`ALLAH_NAMES`, `NABI_NAMES`, `AHL_BAYT_NAMES` and `SAHABA_NAMES` are **protected**:

* their sections use `Rule()` and are listed in `SACRED_SECTIONS`, so no plural,
  suffix, prefix or compound is ever generated from them;
* `is_sacred_derivative()` inside `_add()` rejects any token built by adding an
  inflection marker (`وں، یں، اں، ات، ے، ؤں`) to a sacred name;
* `--verify` asserts `sacred names intact: N present, 0 inflected`;
* the pool itself is checked: an inflected form must never be *added* to a sacred
  block, because the guard treats pool members as canonical
  (`tests/test_urduofdani.py::test_pool_contains_no_inflected_entries`);
* `SACRED_HOMOGRAPH_STEMS` lists divine names that are also ordinary nouns
  (`ملک`, `حق`, `حکم`, `شہید`, `مقدم`, …) — their everyday inflections
  (`ملکوں`, `شہیدوں`, `مقدمے`) stay in the dictionary. Add a stem there only when
  the ordinary reading is the dominant one.

When adding a name, keep it as **one token, correct Urdu orthography, no
honorific phrases** (`محمد` ✅, `محمد صلی اللہ علیہ وسلم` ❌ — that is three tokens).
If you add a title, add the fused single-token form used in Urdu text
(`امیرالمومنین`, `خاتمالنبیین`). Never add a separate inflection of a sacred name.

### Where extra words come from (the mode ladder)

| Mode | Words | Runs in |
|---|---|---|
| `mini` | 3,000 | embedded / low-RAM targets |
| `default` | 25,320 | every build — seeds, plurals, gender, verbs, compounds, curated agentives, 373 sacred names |
| `exhaustive` | 43,043 | section-gated affix families |
| `wide` | 57,806 | relational forms, `والا` family, market heads |
| `full` | 116,184 | deep combinatorics, no cap (the shipped `.full`) |
| `recall` | 2,636,229 | raw cross product (machine tier, never a quality claim) |

Regenerate the numbers with `python tools/measure_tiers.py --table`, and prove the
README still matches with `python tools/measure_tiers.py --check README.md`.

Curated seeds are the *quality* dial: every word you add to `ADDITIONAL_SEEDS`,
`NAME_WORDS`, `MEDICAL_WORDS`, `AGRI_WORDS`, `LAW_WORDS`, `MILITARY_WORDS`,
`TRANSPORT_WORDS`, `TOOL_WORDS`, `BUSINESS_WORDS`, `RELIGION_WORDS`,
`SCIENCE_WORDS` or the four sacred-name blocks multiplies through the plural, gender, verb, compound and
agentive stages automatically.

### Reporting a wrong or missing word

Open an issue with `word`, `expected form`, and `section` — for example:

```text
missing: موبائل  (tech)
wrong:   گای  -> should generate  گایا  (verb: گا)
```

## Adding a full section

```python
LEGAL_WORDS = "دعویٰ مدعا گواہ حلف نامہ ضمانت نامہ"
RULES["legal"] = Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",))
# then register "legal": LEGAL_WORDS in LexiconForge._base_sections()
```

Prefer a **new `Rule`** over loosening an existing one: gated morphology is what keeps
the default build free of junk like `کمآسان`.

## Code style

* Python 3.8+ compatible syntax only (no walrus in hot paths, no 3.9+ builtins).
* Stdlib only. `pip install` is not an option — that is a feature.
* Keep docstrings 4-space indented, type-hinted, and Windows-safe (UTF-8 console).
* No `print()` in library code paths that run at import time.

## Tests before you push

```bash
python urduofdani.py audit                             # EVERY gate in one command
python run_tests.py                                    # the suite (must be green)
python urduofdani.py verify                            # 8 format checks
python urduofdani.py bench -r 10                       # speed
python tools/measure_tiers.py                          # every tier still builds
python tools/audit_docs.py                             # docs still match reality
python urduofdani.py build --mode exhaustive -o /tmp/x.gz
python urduofdani.py build --mode wide -o /tmp/w.gz
```

Rebuild the committed artifacts whenever you change seeds:

```bash
python urduofdani.py build --mode default -o urdu_database.txt.gz
python urduofdani.py build --mode full    -o urdu_database.full.txt.gz
python urduofdani.py verify && python urduofdani.py verify -F
```

Both artifacts are byte-reproducible: a clean rebuild must produce the same
SHA-256, and CI fails if it does not.

## Assets

Branding lives in `assets/` and is regenerated with:

```bash
bash assets/build_assets.sh     # needs ImageMagick + DejaVu fonts
```

`assets/logo.svg` is hand-authored — edit the SVG directly, not the PNG.

## Repository hygiene

* Keep the root tidy: engine + front door + runner + databases + docs; everything
  else belongs in `tests/`, `examples/`, `tools/` or `assets/`.
* Generated files (`*.gz` tiers other than the two shipped ones, plain-text
  exports, `__pycache__`) stay out of Git — `.gitignore` already covers them.
* `tools/audit_docs.py` and `tools/measure_tiers.py --check README.md` are the
  anti-drift gate: if you change a number, change it everywhere.

## Commit messages

`type: short imperative summary` — e.g. `words: add 120 medical terms`,
`fix: correct ے-final verb conjugation`, `docs: clarify gzip ratio`.

## License

By contributing you agree your work is released under the [MIT License](LICENSE).
