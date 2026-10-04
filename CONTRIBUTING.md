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
python build_urdu_database.py --verify --benchmark 10     # format + speed
python build_urdu_database.py --exhaustive -o /tmp/x.gz  # large-lexicon path
python -c "from build_urdu_database import UrduEngine; e=UrduEngine(); print(len(e), 'کمپیوٹر' in e)"
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
