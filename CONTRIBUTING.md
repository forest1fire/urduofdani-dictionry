# Contributing to urduofdani

Thanks for helping make the fastest little Urdu dictionary on Windows even better.
Everything here is stdlib-only Python — no virtualenv gymnastics, no build system.

```bash
git clone https://github.com/forest1fire/urduofdani-dictionary.git
cd urduofdani-dictionary
python build_urdu_database.py --verify --benchmark 10
```

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
| Determinism | same seeds ⇒ same SHA-256 |

`python build_urdu_database.py --verify` proves all of the above. **Run it in every PR.**

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
* `--verify` asserts `sacred names intact: N present, 0 inflected`.

When adding a name, keep it as **one token, correct Urdu orthography, no
honorific phrases** (`محمد` ✅, `محمد صلی اللہ علیہ وسلم` ❌ — that is three tokens).
If you add a title, add the fused single-token form used in Urdu text
(`امیرالمومنین`, `خاتمالنبیین`). Never add a separate inflection of a sacred name.

### Where extra words come from (the mode ladder)

| Mode | Words | Runs in |
|---|---|---|
| *(default)* | 24,809 | every build — seeds, plurals, gender, verbs, compounds, curated agentives, 375 sacred names |
| `--exhaustive` | 42,358 | section-gated affix families |
| `--unlimited --depth 1-4` | 47k → 114k | no cap; deeper combinatorics per level |
| `--recall` | 2,596,675 | raw cross product (machine tier, never a quality claim) |

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
python build_urdu_database.py --verify --benchmark 10        # format + speed
python build_urdu_database.py --exhaustive -o /tmp/x.gz      # gated expansion
python build_urdu_database.py --unlimited --depth 2 -o /tmp/u.gz
python -c "from build_urdu_database import UrduEngine; e=UrduEngine(); print(len(e), 'کمپیوٹر' in e)"
```

Rebuild the committed artifacts whenever you change seeds:

```bash
python build_urdu_database.py --verify --benchmark 5                       # default
python build_urdu_database.py --unlimited --depth 4 -o urdu_database.full.txt.gz
```

## Assets

Branding lives in `assets/` and is regenerated with:

```bash
bash assets/build_assets.sh     # needs ImageMagick + DejaVu fonts
```

`assets/logo.svg` is hand-authored — edit the SVG directly, not the PNG.

## Commit messages

`type: short imperative summary` — e.g. `words: add 120 medical terms`,
`fix: correct ے-final verb conjugation`, `docs: clarify gzip ratio`.

## License

By contributing you agree your work is released under the [MIT License](LICENSE).
