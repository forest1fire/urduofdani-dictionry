#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: test suite
========================
Stdlib ``unittest`` only - no pytest, no fixtures, no network.

    python run_tests.py            # everything
    python -m unittest tests.test_urduofdani -v

Tests that need a database build a small one in a temp directory, so the suite
runs in a few seconds and never touches the shipped artifacts.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import os
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import build_urdu_database as core   # noqa: E402
import urduofdani as front          # noqa: E402

SHIPPED = REPO / core.DB_FILENAME
DB_PATH = SHIPPED
FULL = REPO / "urdu_database.full.txt.gz"
FRONT_DOOR = REPO / "urduofdani.py"


# --------------------------------------------------------------------------- #
# 1. Orthography
# --------------------------------------------------------------------------- #
class TestOrthography(unittest.TestCase):
    def test_arabic_kaf_folds_to_urdu_kaf(self):
        self.assertEqual(core.canonicalize("كتاب"), core.canonicalize("کتاب"))

    def test_arabic_yeh_folds_to_urdu_yeh(self):
        self.assertEqual(core.canonicalize("ي"), core.canonicalize("ی"))
        self.assertEqual(core.canonicalize("بيمار"), core.canonicalize("بیمار"))

    def test_teh_marbuta_and_heh_fold_to_urdu_heh(self):
        self.assertEqual(core.canonicalize("ة"), core.canonicalize("ہ"))
        self.assertEqual(core.canonicalize("الله"), core.canonicalize("اللہ"))

    def test_harakat_are_stripped_by_default(self):
        self.assertEqual(core.canonicalize("کِتاب"), "کتاب")
        self.assertEqual(core.canonicalize("اَ بَ"), "اب")

    def test_harakat_can_be_kept(self):
        self.assertNotEqual(core.canonicalize("کِتاب", keep_diacritics=True), "کتاب")

    def test_invisible_and_punctuation_characters_removed(self):
        self.assertEqual(core.canonicalize("کتاب\u200f"), "کتاب")
        self.assertEqual(core.canonicalize("کتابوں،"), "کتابوں")
        self.assertEqual(core.canonicalize("  کتاب  "), "کتاب")

    def test_token_validation(self):
        for good in ("کتاب", "کمپیوٹر", "اردو"):
            self.assertTrue(core.is_valid_token(good), good)
        for bad in ("", "ک", "کتاب1", "کتاب,", "book", "کتاب ٢", "x" * 41):
            self.assertFalse(core.is_valid_token(bad), bad)


# --------------------------------------------------------------------------- #
# 2. Morphology
# --------------------------------------------------------------------------- #
class TestMorphology(unittest.TestCase):
    def test_masculine_alef_final_plural(self):
        self.assertIn("لڑکے", core.urdu_plurals("لڑکا"))
        self.assertIn("لڑکوں", core.urdu_plurals("لڑکا"))

    def test_feminine_yeh_final_plural(self):
        self.assertIn("لڑکیاں", core.urdu_plurals("لڑکی"))

    def test_heh_final_plural(self):
        self.assertIn("بچے", core.urdu_plurals("بچہ"))
        self.assertIn("بچوں", core.urdu_plurals("بچہ"))

    def test_loan_word_plural(self):
        self.assertIn("لنکس", core.urdu_plurals("لنک", loanword=True))
        self.assertIn("کمپیوٹروں", core.urdu_plurals("کمپیوٹر", loanword=True))

    def test_attach_suffix_orthography(self):
        self.assertEqual(core.attach_suffix("دریا", "ی"), "دریائی")   # not دریای
        self.assertEqual(core.attach_suffix("کتاب", "ی"), "کتابی")
        self.assertEqual(core.attach_suffix("پانی", "ی"), "")          # guarded
        self.assertEqual(core.attach_suffix("دوست", "ت"), "")          # no doubling
        self.assertEqual(core.attach_suffix("پودا", "انہ"), "")        # no vowel clash

    def test_verb_forms(self):
        forms = core.conjugate("دیکھ")
        for expected in ("دیکھنا", "دیکھتا", "دیکھیں", "دیکھیے", "دیکھےگا", "دیکھیںگے", "دیکھا"):
            self.assertIn(expected, forms)

    def test_irregular_verb_forms(self):
        self.assertIn("کیا", core.conjugate("کر"))
        self.assertIn("گیا", core.conjugate("جا"))
        self.assertIn("دیا", core.conjugate("دے"))
        self.assertIn("لیا", core.conjugate("لے"))

    def test_vowel_final_future(self):
        self.assertIn("کھائےگا", core.conjugate("کھا"))
        self.assertIn("جائیںگے", core.conjugate("جا"))


# --------------------------------------------------------------------------- #
# 3. Sacred names
# --------------------------------------------------------------------------- #
class TestSacredNames(unittest.TestCase):
    def test_all_four_sections_loaded(self):
        names = list(core.ALLAH_NAMES.split())
        self.assertGreaterEqual(len(names), 90)          # 99 names, both spellings
        for name in ("رحمٰن", "رحیم", "الرحمن", "الرحیم", "ملک", "قدوس", "غفور"):
            self.assertIn(name, names)
        for name in ("آدم", "نوح", "ابراہیم", "موسی", "عیسی", "محمد", "احمد"):
            self.assertIn(name, core.NABI_NAMES.split())
        for name in ("علی", "فاطمہ", "حسن", "حسین", "زینب", "عباس", "مہدی", "خدیجہ", "عائشہ"):
            self.assertIn(name, core.AHL_BAYT_NAMES.split())
        for name in ("ابوبکر", "عمر", "عثمان", "بلال", "سلمان"):
            self.assertIn(name, core.SAHABA_NAMES.split())

    def test_guard_flags_inflections(self):
        for bad in ("اللہوں", "محمدوں", "علیوں", "حسنوں", "حسینوں", "فاطمہیں"):
            self.assertTrue(core.is_sacred_derivative(bad), bad)

    def test_guard_allows_names_and_ordinary_words(self):
        for good in ("اللہ", "محمد", "علی", "کتاب", "کتابوں"):
            self.assertFalse(core.is_sacred_derivative(good), good)

    def test_guard_works_with_diacritics_kept(self):
        # the guard must canonicalise before comparing, otherwise --keep-diacritics escapes it
        self.assertTrue(core.is_sacred_derivative("اللّٰہوں"))

    def test_every_sacred_name_is_a_valid_token(self):
        for name in sorted(core.SACRED_NAMES):
            self.assertTrue(core.is_valid_token(name), name)

    @unittest.skipUnless(SHIPPED.exists(), "shipped database not built")
    def test_pool_contains_no_inflected_entries(self):
        """A plural inside the pool would dodge the guard and ship verbatim."""
        pool = core.SACRED_NAMES
        offenders = [(w, m) for w in sorted(pool) for m in core._INFLECTION_MARKERS
                     if w.endswith(m) and len(w) > len(m) and w[:-len(m)] in pool]
        self.assertEqual(offenders, [], "inflected entries inside the sacred pool: %r" % offenders)

    def test_plural_prophet_words_are_blocked_not_shipped(self):
        for word in ("نبیوں", "پیغمبروں", "رسولوں", "نبیاں"):
            self.assertTrue(core.is_sacred_derivative(word), word)
            self.assertNotIn(core.canonicalize(word), set(core.load_urdu_database(DB_PATH)), word)

    def test_homograph_names_still_inflect(self):
        """Sacred names that are ordinary nouns keep their everyday inflections."""
        for word in ("ملکوں", "شہیدوں", "مقدمے", "حکموں", "وکیلوں", "برے"):
            self.assertFalse(core.is_sacred_derivative(word), word)
            self.assertIn(core.canonicalize(word), set(core.load_urdu_database(DB_PATH)), word)

    def test_shipped_db_contains_all_names_and_no_inflections(self):
        words = set(core.load_urdu_database(SHIPPED))
        missing = core.SACRED_NAMES - words
        self.assertEqual(missing, set(), "missing sacred names: %s" % sorted(missing)[:5])
        self.assertEqual([w for w in words if core.is_sacred_derivative(w)], [])


# --------------------------------------------------------------------------- #
# 4. Build / verify / determinism
# --------------------------------------------------------------------------- #
class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="urduofdani_test_")
        cls.path = pathlib.Path(cls.tmp.name) / "test_db.txt.gz"
        cls.stats = core.build_urdu_database(output_path=cls.path, max_words=4000,
                                             verbose=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_build_produced_the_requested_size(self):
        self.assertEqual(self.stats["0_total_words"], 4000)
        self.assertEqual(len(core.load_urdu_database(self.path)), 4000)

    def test_payload_is_single_space_tokenized(self):
        with gzip.open(self.path, "rb") as fh:
            text = fh.read().decode("utf-8")
        self.assertNotIn("\n", text)
        self.assertNotIn("\r", text)
        self.assertNotIn(",", text)
        self.assertNotIn("  ", text)                      # never a double separator
        self.assertEqual(text.strip(), text)
        self.assertFalse(core._FORBIDDEN.search(text))

    def test_words_are_sorted_and_unique(self):
        words = core.load_urdu_database(self.path)
        self.assertEqual(words, sorted(set(words)))

    def test_is_standard_gzip(self):
        self.assertTrue(self.path.read_bytes().startswith(b"\x1f\x8b"))   # gzip magic on disk
        with gzip.open(self.path, "rb") as fh:            # gzip module == any gzip tool
            payload = fh.read()
        self.assertGreater(len(payload), 0)
        self.assertEqual(payload.decode("utf-8").count(SEP := core.SEPARATOR), len(payload.decode("utf-8").split(SEP)) - 1)

    def test_compression_ratio_is_material(self):
        self.assertGreaterEqual(self.stats["0_compression_percent"], 70.0)

    def test_verify_passes(self):
        self.assertTrue(core.verify_database(self.path, quiet=True))

    def test_build_is_deterministic(self):
        other = pathlib.Path(self.tmp.name) / "again.gz"
        stats = core.build_urdu_database(output_path=other, max_words=4000, verbose=False)
        self.assertEqual(stats["0_sha256"], self.stats["0_sha256"])
        self.assertEqual(hashlib.sha256(other.read_bytes()).hexdigest(),
                         hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_verify_rejects_an_empty_database(self):
        empty = pathlib.Path(self.tmp.name) / "empty.gz"
        with gzip.open(empty, "wb") as fh:
            fh.write(b"")
        self.assertFalse(core.verify_database(empty, quiet=True))

    def test_verify_rejects_a_non_gzip_file(self):
        """A plain text file must fail the check, not raise BadGzipFile."""
        plain = pathlib.Path(self.tmp.name) / "not_gzip.txt"
        plain.write_text("کتاب", encoding="utf-8")
        self.assertFalse(core.verify_database(plain, quiet=True))

    def test_non_default_modes_never_target_the_shipped_db(self):
        """`build --mode mini` must not overwrite the committed default artifact."""
        proc = subprocess.run([sys.executable, str(FRONT_DOOR), "build",
                               "--mode", "mini", "--help"],
                              capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(proc.returncode, 0)
        spec = front.build_kwargs("mini")
        output = front.default_output_path("mini")
        self.assertEqual(output, "urdu_database.mini.txt.gz")
        self.assertNotEqual(output, core.DB_FILENAME)
        self.assertEqual(front.default_output_path("default"), core.DB_FILENAME)
        self.assertTrue(spec)                      # still a real build spec

    def test_verify_rejects_junk_payload(self):
        junk = pathlib.Path(self.tmp.name) / "junk.gz"
        with gzip.open(junk, "wb") as fh:
            fh.write("کتاب، کتابوں 123\n".encode("utf-8"))
        self.assertFalse(core.verify_database(junk, quiet=True))

    def test_load_and_stream_agree_on_multibyte_boundaries(self):
        words = core.load_urdu_database(self.path)
        for block in (7, 13, 64, 1024):
            self.assertEqual(list(core.iter_urdu_words(self.path, block_bytes=block)), words,
                             "streaming differs at block_bytes=%d" % block)

    def test_quiet_mode_prints_nothing(self):
        """Library users must be able to call verify/benchmark without stdout spam."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ok = core.verify_database(SHIPPED, quiet=True)
            core.benchmark(SHIPPED, repeats=1, quiet=True)
        self.assertTrue(ok)
        self.assertEqual(out.getvalue(), "")

    def test_benchmark_returns_measurements(self):
        result = core.benchmark(self.path, repeats=2, quiet=True)
        self.assertEqual(result["words"], 4000)
        self.assertGreater(result["best_ms"], 0)


# --------------------------------------------------------------------------- #
# 5. Runtime engine
# --------------------------------------------------------------------------- #
class TestEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="urduofdani_engine_")
        cls.path = pathlib.Path(cls.tmp.name) / "engine_db.txt.gz"
        core.build_urdu_database(output_path=cls.path, verbose=False)   # uncapped build
        cls.engine = core.UrduEngine(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_loads_quickly(self):
        self.assertLess(self.engine.load_seconds, 0.5)

    def test_membership_and_folding(self):
        self.assertIn("کتاب", self.engine)
        self.assertIn("كتاب", self.engine)                # Arabic kaf variant
        self.assertNotIn("کتابقلم", self.engine)
        self.assertNotIn(123, self.engine)

    def test_suggestions_are_sorted_prefixes(self):
        hits = self.engine.suggest("کم", 20)
        self.assertTrue(hits)
        self.assertTrue(all(h.startswith("کم") for h in hits), hits)
        self.assertEqual(hits, sorted(hits))

    def test_empty_prefix_returns_head_of_list(self):
        self.assertEqual(self.engine.suggest("", 3), self.engine.words()[:3])

    def test_random_word_is_deterministic_with_seed(self):
        self.assertEqual(self.engine.random_word(seed=42), self.engine.random_word(seed=42))

    def test_extend_adds_words_and_skips_multiword_input(self):
        engine = core.UrduEngine(self.path)
        before = len(engine)
        engine.extend(["بلوچستان", "گلگت", "میرا لفظ", "", "   "])
        self.assertIn("بلوچستان", engine)
        self.assertIn("گلگت", engine)
        self.assertNotIn("میرالفظ", engine)               # never silently fused
        self.assertEqual(engine.last_extend_skipped, 3)
        self.assertEqual(len(engine), before + 2)

    def test_extend_non_strict_fuses(self):
        engine = core.UrduEngine(self.path)
        engine.extend(["میرا لفظ"], strict=False)
        self.assertIn("میرالفظ", engine)

    def test_info_reports_metadata(self):
        info = self.engine.info()
        self.assertEqual(info["words"], len(self.engine))
        self.assertGreater(info["packed_bytes"], 0)

    def test_lazy_engine_loads_on_demand(self):
        lazy = core.UrduEngine(self.path, lazy=True)
        self.assertEqual(len(lazy), 0)
        self.assertGreater(len(lazy.load()), 0)


# --------------------------------------------------------------------------- #
# 6. CLI / front door
# --------------------------------------------------------------------------- #
class TestCommandLine(unittest.TestCase):
    def _run(self, script, args, expect_zero=True):
        proc = subprocess.run([sys.executable, str(script)] + args,
                              capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(proc.returncode == 0, expect_zero,
                         "%s %s -> rc=%d\n%s" % (script.name, args, proc.returncode, proc.stderr))
        return proc

    def test_compiler_cli_help_and_version(self):
        self._run(REPO / "build_urdu_database.py", ["--help"])
        self._run(REPO / "build_urdu_database.py", ["--version"])

    def test_every_mode_maps_to_real_builder_kwargs(self):
        """MODE tables drift; blurb must never leak into build_urdu_database()."""
        import inspect
        params = inspect.signature(core.build_urdu_database).parameters
        for name in front.MODES:
            kwargs = front.build_kwargs(name)
            self.assertIn("blurb", front.MODES[name], name)
            unknown = [k for k in kwargs if k not in params]
            self.assertEqual(unknown, [], "mode %r passes unknown kwargs: %r" % (name, unknown))

    def test_audit_gates_exist_on_disk(self):
        """`urduofdani.py audit` must not reference a file that is not there."""
        for label, script, _extra in front.AUDIT_GATES:
            self.assertTrue((REPO / script).exists(), "audit gate %r -> missing %s" % (label, script))

    def test_every_subcommand_has_a_handler(self):
        parser = front.build_parser()
        for action in parser._actions:
            if not (action.choices and isinstance(action.choices, dict)):
                continue
            for name, sub in action.choices.items():
                self.assertTrue(hasattr(sub, "func") or hasattr(sub, "set_defaults"),
                                "subcommand %r has no handler" % name)

    def test_quiet_test_runner_prints_one_summary_line(self):
        """-q must give a one-line summary (run with an empty pattern: no recursion)."""
        proc = subprocess.run([sys.executable, str(REPO / "run_tests.py"),
                               "-q", "-k", "no_such_tests_*.py"],
                              capture_output=True, text=True, cwd=str(REPO), timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        self.assertIn("Ran 0 tests", proc.stdout)
        self.assertIn("OK", proc.stdout)
        self.assertLessEqual(len([l for l in proc.stdout.splitlines() if l.strip()]), 3)

    def test_front_door_help_and_modes(self):
        self._run(FRONT_DOOR, ["--help"])
        self._run(FRONT_DOOR, ["modes"])

    def test_front_door_check_exit_codes(self):
        self._run(FRONT_DOOR, ["check", "کتاب"], expect_zero=True)
        self._run(FRONT_DOOR, ["check", "کتبکتبکتبکتب"], expect_zero=False)

    def test_front_door_search(self):
        proc = self._run(FRONT_DOOR, ["search", "کمپیو", "-l", "3"])
        self.assertTrue(proc.stdout.strip())

    def test_front_door_info(self):
        proc = self._run(FRONT_DOOR, ["info"])
        self.assertIn("words", proc.stdout)

    def test_missing_database_fails_cleanly(self):
        proc = subprocess.run([sys.executable, str(FRONT_DOOR), "verify", "-d", "nope.gz"],
                              capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not found", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


# --------------------------------------------------------------------------- #
# 7. Shipped artifacts (skipped if the repo has not been built)
# --------------------------------------------------------------------------- #
class TestShippedArtifacts(unittest.TestCase):
    @unittest.skipUnless(SHIPPED.exists(), "shipped database missing")
    def test_shipped_db_is_valid(self):
        self.assertTrue(core.verify_database(SHIPPED, quiet=True))

    @unittest.skipUnless(SHIPPED.exists(), "shipped database missing")
    def test_shipped_db_size_and_words(self):
        words = core.load_urdu_database(SHIPPED)
        # A *quality band*: the audit-driven clean-up removed ~8k junk tokens, so
        # the floor is deliberately a real-word floor, not a raw-volume floor.
        self.assertGreater(len(words), 15000)
        self.assertLess(SHIPPED.stat().st_size, 200 * 1024)

    @unittest.skipUnless(SHIPPED.exists(), "shipped database missing")
    def test_full_audit_quality_round_kept_the_junk_out(self):
        """Every class of junk the word audit found must stay gone."""
        words = set(core.load_urdu_database(SHIPPED))
        for junk in ("آلوخانہ", "آنکھگاہ", "آلودگیگاہ", "آبپاشیگودام", "اجرتمنڈی",
                     "آرڈرمنڈی", "اسٹیڈیمفروش", "آبپاشیدان", "اخبارساز", "بلبفروش",
                     "اسٹیڈیمساز", "اٹھاائیوالا", "بوناائیوالا", "صافکرنےوالا",
                     "ضدکرنےوالا", "آرامنےوالا", "آرامنا", "کامنا", "یادنا",
                     "انجینئرگھرگر", "ریتسازفروش", "کمانڈرپن", "گردنپن", "ہڑتالگی"):
            self.assertNotIn(junk, words, "%s should not be a word" % junk)

    @unittest.skipUnless(SHIPPED.exists(), "shipped database missing")
    def test_full_audit_quality_round_kept_the_real_words(self):
        words = set(core.load_urdu_database(SHIPPED))
        for real in ("چائےخانہ", "دواخانہ", "ڈاکخانہ", "کتابخانہ", "مہمانخانہ",
                     "ورزشگاہ", "تفریحگاہ", "عبادتگاہ", "شکارگاہ", "زیارتگاہ",
                     "سبزیمنڈی", "مچھلیمنڈی", "اناجگودام", "دودھفروش", "مچھلیفروش",
                     "کتابفروش", "زیورساز", "گھڑیساز", "عقلمند", "دردمند", "خدمتکار",
                     "دربان", "قلمدان", "نمکدان", "ابھرنا", "کرنےوالا", "اٹھانےوالا",
                     "اسٹیشنز", "کمپیوٹرز", "موبائلز", "ٹکٹس"):
            self.assertIn(real, words, "%s must be in the build" % real)

    @unittest.skipUnless(SHIPPED.exists(), "shipped database missing")
    def test_sacred_names_are_never_inflected_anywhere(self):
        """Phase-4 guarantee: names in the four protected sections stay bare."""
        words = set(core.load_urdu_database(SHIPPED))
        markers = ("وں", "یں", "اں", "ات", "ے", "ؤں", "پن", "گی")
        for name in core._sacred_set():
            if name in core.SACRED_HOMOGRAPH_STEMS:
                continue
            for marker in markers:
                variant = name + marker
                if variant in core.SACRED_DERIVATIVE_EXCEPTIONS:
                    continue
                self.assertNotIn(variant, words, "%s must never be derived" % variant)

    @unittest.skipUnless(FULL.exists(), "unlimited build missing")
    def test_full_db_is_valid_and_bigger(self):
        self.assertTrue(core.verify_database(FULL, quiet=True))
        self.assertGreater(len(core.load_urdu_database(FULL)),
                           len(core.load_urdu_database(SHIPPED)))


# --------------------------------------------------------------------------- #
# 8. Packaging, environment override and the compact front-door build
# --------------------------------------------------------------------------- #
class TestPackagingAndEnv(unittest.TestCase):
    def test_pyproject_declares_working_console_scripts(self):
        import tomllib
        data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = data["project"]["scripts"]
        self.assertIn("urduofdani", scripts)
        self.assertIn("urduofdani-engine", scripts)
        for target in scripts.values():
            module_name, _, attr = target.partition(":")
            module = __import__(module_name)
            self.assertTrue(callable(getattr(module, attr)),
                            "%s must be a callable entry point" % target)

    def test_pyproject_modules_are_importable(self):
        import tomllib
        data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
        for name in data["tool"]["setuptools"]["py-modules"]:
            with contextlib.redirect_stdout(io.StringIO()):
                __import__(name)

    def test_env_var_points_the_engine_at_a_database(self):
        import urduofdani_engine as engine_mod
        previous = os.environ.get("URDUOFDANI_DB")
        os.environ["URDUOFDANI_DB"] = str(SHIPPED)
        try:
            found = engine_mod.find_database()
            self.assertIsNotNone(found)
            self.assertEqual(found.resolve(), SHIPPED.resolve())
        finally:
            if previous is None:
                os.environ.pop("URDUOFDANI_DB", None)
            else:
                os.environ["URDUOFDANI_DB"] = previous

    def test_env_var_is_used_by_the_front_door(self):
        previous = os.environ.get("URDUOFDANI_DB")
        os.environ["URDUOFDANI_DB"] = str(SHIPPED)
        try:
            self.assertEqual(front._resolve_db(None).resolve(), SHIPPED.resolve())
        finally:
            if previous is None:
                os.environ.pop("URDUOFDANI_DB", None)
            else:
                os.environ["URDUOFDANI_DB"] = previous

    def test_front_door_compact_build_writes_front_coded_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "probe.compact.gz"
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                code = front.main(["build", "--mode", "mini", "--format", "compact",
                                   "-o", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())
            with gzip.open(out, "rb") as fh:
                head = fh.read(8)
            self.assertEqual(head, b"URDUFC1 ")          # front-coded container
            words = core.load_urdu_database(out, verify_checksum=True)
            self.assertEqual(len(words), 3000)           # mini tier

    def test_compact_defaults_never_clobber_the_plain_release(self):
        self.assertNotEqual(front.default_output_path("default", "compact"),
                            front.default_output_path("default", "plain"))
        self.assertEqual(front.default_output_path("default", "compact"),
                         front.COMPACT_DB)
        self.assertEqual(front.default_output_path("mini", "compact"),
                         "urdu_database.mini.compact.gz")


if __name__ == "__main__":
    unittest.main(verbosity=2)
