#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
urduofdani :: build_urdu_database.py
====================================
Modern High-Speed Urdu Text Engine -- Dictionary Compiler.

Compiles a large, de-duplicated Urdu lexicon and serialises it using
*Single-Space Tokenization* into ONE continuous line, then compresses that line
into a tiny gzip binary named ``urdu_database.txt.gz``.

Design goals
------------
* Zero third-party dependencies -> stdlib only (gzip / zlib / re / unicodedata).
* Windows-first                 -> UTF-8 everywhere, atomic writes, no console crash.
* Deterministic                 -> identical seeds always produce byte-identical
                                   output (gzip MTIME is forced to 0).
* Unlimited scaling             -> ``--max-words 0`` (default) = no cap, and
                                   ``--exhaustive`` = maximum combinatorial recall.
* Runtime friendly              -> :class:`UrduEngine` loads + indexes the DB in ms.

Payload layout of the compressed database
-----------------------------------------
::

    "اردو ہندوستان پاکستان ..."      <- ONE single line, tokens split by ONE space

Rules enforced by the compiler:
    * no newlines   * no commas   * no digits   * no punctuation   * no duplicates

CLI
---
::

    python build_urdu_database.py                      # balanced build (default)
    python build_urdu_database.py --exhaustive         # maximum-recall build
    python build_urdu_database.py --max-words 0        # explicitly unlimited
    python build_urdu_database.py --verify --export urdu_database.txt
    python build_urdu_database.py --benchmark 10       # benchmark an existing .gz
    python build_urdu_database.py --no-build --benchmark 5

Author: urduofdani maintainers -- MIT License.
"""

from __future__ import annotations

import argparse
import bisect
import gzip
import hashlib
import os
import random
import re
import sys
import tempfile
import time
import tracemalloc
import unicodedata
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence, Set, Tuple

__all__ = [
    "UrduEngine",
    "build_urdu_database",
    "load_urdu_database",
    "iter_urdu_words",
    "verify_database",
    "benchmark",
    "canonicalize",
    "urdu_plurals",
    "compile_lexicon",
]

SCRIPT_VERSION = "2.0.0"
DB_FILENAME = "urdu_database.txt.gz"
SEPARATOR = " "
GZIP_LEVEL = 9            # maximum deflate ratio: this is what collapses MB -> KB
GZIP_WBITS = 31           # 31 = raw DEFLATE wrapped in a standard gzip container
GZIP_MEMLEVEL = 9
CHUNK_TOKENS = 25_000     # streaming join size -> flat memory even on huge builds

# ---------------------------------------------------------------------------
# 1. ORTHOGRAPHY LAYER   (canonical Urdu normalisation + phonology helpers)
# ---------------------------------------------------------------------------
# Arabic / Persian codepoints that Windows keyboards, PDFs and legacy databases
# insert by accident. Folding them onto the Urdu codepoint is what keeps the
# dictionary de-duplicated: "كتاب", "کتاب" and "كِتاب" must collapse to ONE token.
_FOLD_MAP: Dict[int, str] = {
    0x0622: "\u0622",   # آ  alef madda  (kept - a distinct Urdu letter)
    0x0623: "\u0627",   # أ  -> ا
    0x0625: "\u0627",   # إ  -> ا
    0x0629: "\u06C1",   # ة  -> ہ
    0x0643: "\u06A9",   # ك  -> ک
    0x0649: "\u06CC",   # ى  -> ی
    0x064A: "\u06CC",   # ي  -> ی
    0x06C0: "\u06C1",   # ۀ  -> ہ
    0x06C2: "\u06C1",   # ۂ  -> ہ
    0x06D3: "\u06D2",   # ۓ  -> ے
    0x200B: "",         # zero width space      -> drop
    0x200E: "",         # LRM                   -> drop
    0x200F: "",         # RLM                   -> drop
    0x0640: "",         # tatweel / kashida     -> drop
    0x0651: "",         # shadda                -> drop
    0x0654: "",         # hamza above           -> drop
    0x0655: "",         # hamza below           -> drop
    0x0670: "",         # superscript alef      -> drop
}
_FOLD_TABLE = str.maketrans({chr(k): v for k, v in _FOLD_MAP.items()})

# Optional Arabic diacritics (harakat). Stripped by default so that
# "کِتاب" and "کتاب" become the same token.
_HARAKAT = re.compile(r"[\u064B-\u0650\u0652-\u0653\u0656-\u065F\u0670\u06D6-\u06ED]")

# A token that is legal AFTER cleaning. Rejects digits and punctuation.
_LEGAL_TOKEN = re.compile(
    r"^[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\u200C\u200D]+$"
)
_FORBIDDEN = re.compile(r"[0-9\u0660-\u0669\u06F0-\u06F9]")
_PUNCT = re.compile(
    r"[\s,.;:!?،؛؟٪%\-_/\\|@#$^&*+=~`'\"()\[\]{}<>«»…\u2009\u2026\u060C\u061B\u061F]"
)

# Urdu letters that behave like vowels when an affix is attached.
_VOWEL_FINALS = "اآہیےوؤ"


def canonicalize(word: str, keep_diacritics: bool = False) -> str:
    """Return the canonical Urdu form of *word* (one folded word, no junk).

    Used by BOTH the compiler and the runtime loader, so a lookup performed at
    runtime matches exactly the token that was stored at build time.
    """
    if not word:
        return ""
    word = unicodedata.normalize("NFC", word).translate(_FOLD_TABLE)
    if not keep_diacritics:
        word = _HARAKAT.sub("", word)
    word = _PUNCT.sub("", word)
    return unicodedata.normalize("NFC", word).strip()


def is_valid_token(token: str, min_len: int = 2, max_len: int = 40) -> bool:
    """True when *token* is a clean, digit-free, punctuation-free Urdu word."""
    if not (min_len <= len(token) <= max_len):
        return False
    if _FORBIDDEN.search(token) or _PUNCT.search(token):
        return False
    return bool(_LEGAL_TOKEN.match(token))


def urdu_plurals(word: str, loanword: bool = False) -> List[str]:
    """Generate the *grammatically produced* Urdu plural / oblique forms.

    Implements the real phonological rules instead of blind suffixing:

        لڑکا  -> لڑکے،  لڑکوں            (alef final: ے / وں)
        لڑکی  -> لڑکیاں، لڑکیوں          (ye final: اں / یوں)
        بچہ   -> بچے،   بچوں             (he final: ے / وں)
        عورت  -> عورتیں، عورتوں          (feminine consonant: یں / وں)
        کتاب  -> کتابیں، کتابوں          (masculine consonant: یں / وں)
        فائل  -> فائلیں، فائلوں          (loanword, feminine reading)
        لنک   -> لنکس،  لنکوں            (loanword: ز is the modern Urdu plural)
    """
    if len(word) < 2:
        return []
    out: List[str] = []

    if loanword:
        if not word.endswith(("ی", "ہ", "ا")):
            out.append(word + "ز")                   # لنکس، کمپیوٹرز، سرورز
        out.append(word + "وں")                      # موبائلوں، فائلوں
        if word[-1] in "فلہنمیے":
            out.append(word + "یں")                  # فائلیں، ایپس -> ایپیں (rare)
        return _dedupe(out)

    last = word[-1]
    if last == "ا" and word.endswith("یا"):
        out += [word + "ں", word[:-1] + "یوں", word[:-1] + "ؤں"]   # چڑیاں، چڑیوں، دنیاؤں
    elif last == "ا":
        out += [word[:-1] + "ے", word[:-1] + "وں"]    # لڑکا -> لڑکے، لڑکوں
    elif last in "یے":
        out += [word + "اں", word[:-1] + "یوں"]       # لڑکی -> لڑکیاں، لڑکیوں
    elif last == "ہ":
        out += [word[:-1] + "ے", word[:-1] + "وں"]    # کمرہ -> کمرے، کمروں
    elif last == "ں":
        out += [word[:-1] + "نوں"]
    elif last == "و":
        out += [word + "ں"]
    elif last in "تٹ":
        out += [word + "یں", word + "وں"]             # عورت، چوٹ (feminine)
    else:
        out += [word + "وں"]
        if last in "نمرکلبشف":                        # producible -یں family
            out.append(word + "یں")
        else:
            out.append(word + "یں")
    return _dedupe(out)


def _pluralizable(word: str) -> bool:
    """False for seeds that are already plural / oblique forms.

    "جوتے", "دکانوں" and "بکریاں" are stored as dictionary entries, but the
    plural stage must not run on them again (otherwise the forge invents
    "جوتےاں" or "بکریاںی").
    """
    return not (len(word) > 3 and word.endswith(("وں", "یں", "اں", "ے", "ات")))


def _dedupe(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def attach_suffix(word: str, suffix: str) -> str:
    """Attach a derivational suffix using Urdu orthographic rules.

    Handles the cases where a naive ``word + suffix`` would be misspelled:

        دریا + ی  -> دریائی      (not دریای)
        ہوا  + ی  -> ہوائی
        بڑا  + پن -> بڑاپن
        پانی + ی  -> (skipped, would create "پانیی")
    """
    if not suffix or len(word) < 2:
        return ""
    if word.endswith(suffix):                 # avoid "دوستتی" / "کتابب"
        return ""
    last = word[-1]
    if suffix == "ی":
        if last in "یے":
            return ""
        if last == "ا":
            return word[:-1] + ("ئی" if word.endswith("یا") else "ائی")
        if last in "ہۂ":
            return ""
    if suffix[0] == last and last not in "او":  # double-letter guard
        return ""
    return word + suffix


# ---------------------------------------------------------------------------
# 2. CURATED LEXICON   (hand-written seed vocabulary, grouped by category)
# ---------------------------------------------------------------------------
# Each section is a space-delimited blob of real Urdu words. The section name
# decides which morphology the forge is allowed to apply (see RULES below).

FUNCTION_WORDS: str = (
    # pronouns, postpositions, conjunctions, question words, emphatics
    "میں ہم تم آپ وہ یہ ہمارا ہمارے ہماری میرا میرے میری تیرا تیرے تیری "
    "آپکا آپکے آپکی اپنا اپنے اپنی خود خودی کون کیا کیوں کب کہاں کیسے کیسا کیسی "
    "کتنا کتنی کتنے اور یا لیکن مگر اگر تو پھر بھی نہ نہیں ہاں جی ٹھیک ٹھاک "
    "اچھا اچھی اچھے برا بری برے بہت زیادہ کم تھوڑا تھوڑی تھوڑے سارا ساری سارے سب "
    "کوئی کچھ ہر کبھی ہمیشہ اکثر شاید ضرور بالکل واقعی سچ جھوٹ مطلب یعنی "
    "کیونکہ تاکہ جیسا جیسی جیسے ویسا ویسی ویسے اتنا اتنی اتنے "
    "جہاں وہاں یہاں ادھر ادھر جدھر کدھر جب تک بغیر ساتھ لیے بنا "
    "کے کی کا کو سے نے پر تلک تک ہی بھی تو نا ناں ذرا ذرہ صرف محض بھر "
    "کاش افسوس خیر بھلا چلو آؤ چلئے دیکھیں سنیں جی ہاں نہیں ٹھیک ہے "
)

NUMBER_WORDS: str = (
    # digits are illegal in the DB -> numbers live here as WORDS
    "ایک دو تین چار پانچ چھ سات آٹھ نو دس گیارہ بارہ تیرہ چودہ پندرہ سولہ سترہ "
    "اٹھارہ انیس بیس اکیس بائیس تئیس چوبیس پچیس چھبیس ستائیس اٹھائیس انتیس تیس "
    "اکتیس بتیس تینتیس چونتیس پینتیس چھتیس سینتیس اڑتیس انتالیس چالیس اکتالیس "
    "بیالیس تینتالیس چوالیس پینتالیس چھیالیس سینتالیس اڑتالیس انچاس پچاس اکاون "
    "باون ترپن چون پچپن چھپن ستاون اٹھاون انسٹھ ساٹھ اکسٹھ باسٹھ ترسٹھ چونسٹھ "
    "پینسٹھ چھیاسٹھ سڑسٹھ اڑسٹھ انہتر ستر اکہتر بہتر تہتر چوہتر پچہتر چھہتر ستتر "
    "اٹھہتر اناسی اسی اکیاسی بیاسی تراسی چوراسی پچاسی چھیاسی ستاسی اٹھاسی نواسی "
    "نوے اکانوے بانوے ترانوے چورانوے پچانوے چھیانوے ستانوے اٹھانوے ننانوے سو "
    "ہزار لاکھ کروڑ ارب کھرب پہلا دوسرا تیسرا چوتھا پانچواں چھٹا ساتواں آٹھواں "
    "نواں دسواں آدھا پاؤ چوتھائی تہائی دوگنا تگنا چوگنا نصف فیصد "
)

TIME_WORDS: str = (
    "آج کل پرسوں ابھی پہلے بعد جلد دیر صبح سویرے دوپہر شام رات راتوں دن دنوں "
    "ہفتہ ہفتے مہینہ مہینے سال سالوں گھنٹہ گھنٹے منٹ سیکنڈ لمحہ لمحے وقت وقتی "
    "وقتاً تاریخ تاریخی صدی عرصہ مدت مرحلہ موقع موقعہ موقعوں آغاز اختتام "
    "پیر منگل بدھ جمعرات جمعہ ہفتوار اتوار جنوری فروری مارچ اپریل مئی جون جولائی "
    "اگست ستمبر اکتوبر نومبر دسمبر موسم بہار گرمی خزاں سردی برسات شادی عید رمضان "
    "محرم شب قدر چاند رات سالگرہ یوم تہوار تعطیل چھٹی"
)

NATURE_WORDS: str = (
    "پانی ہوا آگ مٹی زمین آسمان ستارہ ستارے چاند سورج کہکشاں بادل باد بارش برف "
    "اولے طوفان زلزلہ سیلاب روشنی چراغ اندھیرا سایہ دریا سمندر جھیل ندی چشمہ "
    "کنواں پہاڑ پہاڑی وادی صحرا جنگل درخت پتہ پتے جڑ پھول پھل بیج گھاس باغ "
    "باغیچہ کھیت فصل پتھر چٹان ریت سونا چاندی لوہا تانبا پیتل جست کوئلہ تیل گیس "
    "بجلی توانائی دھوپ چھاؤں کہر دھند نمی خشکی سیل ریتلا مٹیالا بادلوں بادل "
    "شبنم اولہ ژالہ باری تودہ لاوہ راکھ چنگاری شعلہ شعلے دھواں بھاپ کائی "
    "پرندہ پرندے جانور جانوروں کیڑا مکھی مچھر مکڑی چیونٹی شہد مکھی تتلی بھونرا "
    "شیر شیروں بھیڑیا لومڑی خرگوش ہرن چیتا ریچھ بندر گدھا گھوڑا اونٹ ہاتھی "
    "گائے بیل بکری بھینس کتا بلی چوہا چوہے بطخ مرغی مرغا کبوتر کوے طوطا مینا "
    "چڑیا عقاب باز الو مچھلی کچھوا سانپ مگرمچھ شیر کیکڑا جھینگا سیپ موتی "
)

PLACE_WORDS: str = (
    "گھر گھروں مکان دالان چھت صحن کمرہ کمرے دروازہ دروازے کھڑکی دیوار فرش "
    "زینہ سیڑھی چابی تالا بازار دکان دفتر مدرسہ اسکول کالج یونیورسٹی ہسپتال "
    "کلینک دواخانہ مسجد مندر گرجا گوردوارہ قبرستان پارک میدان سڑک گلی شاہراہ "
    "پل چوک اسٹیشن اڈہ بندرگاہ ریلوے بس ٹرین ٹیکسی رکشہ سائیکل موٹرسائیکل گاڑی "
    "کار جہاز کشتی گاؤں شہر ملک سرحد صوبہ ضلع تحصیل ریاست دارالحکومت "
)

PROPER_NOUNS: str = (
    # names are stored as-is: they are never pluralised or suffixed
    "پاکستان ہندوستان ایران افغانستان ترکی چین عرب امریکہ انگلستان لندن دہلی "
    "لاہور کراچی اسلام آباد پشاور کوئٹہ ملتان فیصل آباد حیدرآباد راولپنڈی "
    "گوجرانوالہ سیالکوٹ بہاولپور سکھر جھنگ مظفرآباد ایبٹ آباد ڈیرہ اسماعیل خان "
    "مکہ مدینہ بغداد قاہرہ دمشق استنبول تہران کابل ٹوکیو بیجنگ ماسکو پیرس "
    "نیویارک واشنگٹن ٹورنٹو سڈنی دبئی ابوظبی دوحہ ریاض جدہ کویت مسقط "
    "اردو پنجابی سندھی پشتو بلوچی سرائیکی کشمیری ہندکو "
)

PERSON_WORDS: str = (
    "ماں باپ والد والدہ والدین بیٹا بیٹی بیٹے اولاد بچہ بچی بچے بھائی بہن دادا "
    "دادی نانا نانی پوتا پوتی نواسہ نواسی چچا چچی تایا تائی ماموں مامی خالہ خالو "
    "سسر ساس سالا سالی بھتیجا بھتیجی بھانجا بھانجی شوہر بیوی میاں بیگم زوجین "
    "خاندان رشتہ رشتے دوست دوستی دوستوں دشمن پڑوسی اجنبی مہمان انسان آدمی عورت "
    "مرد بچپن جوانی بڑھاپا بزرگ نوجوان لڑکا لڑکی لڑکے ٹیچر استاد شاگرد طالب "
    "انجینئر ڈاکٹر نرس وکیل جج صحافی مصنف شاعر ادیب پروفیسر پرنسپل منیجر "
    "اکاؤنٹنٹ کلرک درزی موچی بڑھئی لوہار سنار کمہار کسان مزدور ملازم کاریگر "
    "ہنرمند ماہر مشیر ناظم ڈائریکٹر افسر سپاہی جرنیل سیاستدان وزیر صدر گورنر "
    "شہری دیہاتی پنڈت مولوی قاری حافظ خطیب امام مبلغ کارکن رہنما لیڈر "
)

BODY_WORDS: str = (
    "سر آنکھ آنکھیں کان ناک منہ ہونٹ دانت زبان گلا گردن کندھا بازو ہاتھ ہتھیلی "
    "انگلی انگلیاں ناخن سینہ دل جگر معدہ پیٹ کمر ران گھٹنا ٹخنہ پاؤں پیر خون "
    "گوشت ہڈی ہڈیاں جلد بال رگ دماغ یاد حافظہ نیند خواب تھکن درد بخار زکام "
    "کھانسی نزلہ پھیپھڑے صحت تندرستی بیماری مرض علاج دوا دوائیں دوادارو ٹیکہ "
    "ویکسن آپریشن سرجری مریض طبیب حکیم جراح تشخیص نسخہ پرچہ شفاخانہ "
    "دھڑکن سانس آنکھوں ہاتھوں پاؤں پیروں کانوں دانتوں "
)

FOOD_WORDS: str = (
    "روٹی روٹیاں نان چاول سالن گوشت مرغی مچھلی انڈا انڈے سبزی سبزیاں پھل پھلوں "
    "سیب آم کیلا انگور انار تربوز خربوزہ مالٹا سنگترہ لیموں امرود آلو پیاز ٹماٹر "
    "بھنڈی بینگن کدو گاجر مولی شلجم پالک میتھی دھنیا پودینہ ادرک لہسن مرچ نمک "
    "ہلدی زیرہ دار چینی الائچی لونگ سویا تیل گھی مکھن دہی لسی چھاچھ دودھ چائے "
    "کافی قہوہ شربت جوس ناشتہ کھانا میٹھا نمکین ترش کڑوا کھٹا مزہ ذائقہ بھوک "
    "پیاس پیالہ پلیٹ چمچ چاقو کٹورا برتن توا کڑاہی پتیلی چولھا اوون فرج "
    "بسکٹ کیک پیسٹری بریانی قورمہ کباب سموسہ پکوڑا حلوا کھیر فالودہ ریتھا "
    "چٹنی اچار مربہ شہد چینی گڑ کھویا پنیر دہی مکئی جوار باجرہ چنا مسور ماش "
)

HOUSEHOLD_WORDS: str = (
    "کرسی میز صوفہ پلنگ بستر تکیہ چادر رضائی کمبل قالین پردہ شیشہ بلب پنکھا "
    "کولر ہیٹر استری ویکیوم جھاڑو پوچا صابن شیمپو تولیہ کنگھی آئینہ قینچی "
    "سوئی دھاگہ کپڑا رسی تار کیل ہتھوڑا کلہاڑی آری رندھ پیچکاسہ چابیاں ڈبہ "
    "تھیلا بوری ٹوکری بوتل گلاس جھاگ کچرا کوڑا دان ٹوٹی گملہ چمنی شمع "
)

CLOTHING_WORDS: str = (
    "لباس کپڑے قمیض شلوار پاجامہ کرتا دوپٹہ چادر شال سوٹ کوٹ پتلون شرٹ ٹائی "
    "جیکٹ سویٹر ٹوپی ٹوپیاں پگڑی جوتا جوتے چپل سینڈل موزہ دستانے رومال بیگ "
    "بٹوہ چوڑی کنگن انگوٹھی ہار زیور جھمکے ٹوپی والا ریشم اون کپاس لینن "
)

ABSTRACT_WORDS: str = (
    "خوشی غمی غم دکھ تکلیف آرام سکون سکون پریشانی فکر تشویش امید ناامیدی مایوسی "
    "محبت پیار عشق نفرت حسد رحم غصہ ہنسی مسکراہٹ آنسو دعا شکر صبر ایمان عقیدہ "
    "عبادت نماز روزہ زکات حج قربانی قرآن حدیث سنت نبی رسول اللہ خدا رب بندگی "
    "تقوی نیکی بدی ثواب گناہ توبہ جنت دوزخ فرشتہ شیطان روح نفس شعور لاشعور "
    "ہنر فن ادب شاعری شعر غزل نظم کہانی افسانہ ناول ڈراما تصویر رنگ موسیقی راگ "
    "نغمہ گیت آواز خاموشی زبان لہجہ لفظ جملہ عبارت مضمون مطلب ترجمہ لغت قاموس "
    "قواعد املا خط کتاب رسالہ حروف تہجی محاورہ کہاوت ضرب مثل خیال تصور خواب "
    "حقیقت حیرت تعجب خوف ڈر ہمت بزدلی غرور انکساری تواضع اخلاق کردار دیانت "
    "ایمانداری خودی غیرت حمیت عزت ذلت شان وقار احترام تعظیم الفت چاہت لگن جنون "
    "فراق وصال ہجر جدائی ملاپ یاس توقع یقین بھروسہ اعتماد شک گمان وسوسہ ظن "
    "سچائی جھوٹائی صداقت وفا بےوفائی ہمدردی غمخواری خیر خیرات نیکی ثواب "
    "دوزخی جنت والا علم دانش بینش بصیرت فراست ذہانت حافظہ یادداشت توجہ "
    "یکسوئی محنت کوشش جدوجہد لگن مستقل مزاجی عادت خصلت فطرت مزاج طبیعت "
    "جذبہ احساس کیفیت کیف مستی نشہ سرشاری وجدان الہام وحی کرامت معجزہ "
)

ADJECTIVE_WORDS: str = (
    "بڑا چھوٹا لمبا چوڑا گہرا اونچا نیچا نیا پرانا نوجوان بوڑھا تازہ سست تیز "
    "آہستہ نرم سخت کھردرا گرم ٹھنڈا سوکھا گیلا صاف گندا خالص کھلا بند خالی بھرا "
    "ہلکا بھاری سستا مہنگا خوبصورت بدصورت پیارا معصوم شریف بدتمیز عقلمند دانا "
    "بیوقوف سمجھدار ہوشیار چالاک بہادر ڈرپوک سچا جھوٹا وفادار بے وفا مہربان "
    "سنگدل خوش مزاج بدمزاج محنتی کمزور طاقتور صحت مند بیمار زندہ مردہ تھکا "
    "بھوکا پیاسا امیر غریب تنگ دست خوش حال دل کش دلچسپ بور اچھا برا بہترین "
    "بہتر اعلیٰ ادنیٰ خاص عام آسان مشکل ممکن ناممکن ضروری اہم معمولی مفید مضر "
    "جائز ناجائز حلال حرام پاک نجس ادھورا پورا ادھیڑ پکا کچا میٹھا تلخ شیریں "
    "چمکدار رنگین بے رنگ بے نام بے کار بے بس بے حال بے خبر بے شمار بے شمار "
    "لاپرواہ لاچار بے چارہ کامیاب ناکام مشہور نامعلوم معلوم واضح مبہم گہرا "
)

COLOR_WORDS: str = (
    "رنگ رنگوں سفید کالا سرخ لال نیلا سبز پیلا نارنجی بھورا خاکی گلابی جامنی "
    "سنہری چاندی سرمئی فیروزی زیتونی آسمانی گہرا ہلکا چمکیلا شفاف دھندلا "
    "دائرہ گول چوکور مستطیل مثلث کونہ لکیر نقطہ شکل صورت ہیئت "
)

SOCIETY_WORDS: str = (
    "حکومت سرکار وزیراعظم صدر گورنر پارلیمنٹ اسمبلی عدالت جج وکیل مقدمہ قانون "
    "آئین حقوق فرض شہریت قومی بین الاقوامی انتخابات ووٹ جماعت تحریک احتجاج "
    "ہڑتال انصاف ظلم جیل پولیس فوج دفاع حملہ جنگ امن معاہدہ تجارت کاروبار "
    "کمپنی فرم ملازم تنخواہ اجرت منافع نقصان سرمایہ بینک رقم پیسہ پیسے کرنسی "
    "ڈالر روپیہ ادھار قرض سود منڈی قیمت خریداری فروخت سودا بچت بجٹ حساب "
    "محصول ٹیکس شہرت کامیابی ناکامی ترقی زوال اخبار رسالہ چینل ریڈیو نشریات "
    "اشتہار تشہیر خبر خبریں واقعہ حادثہ جرم سزا قیدی عدالتی فیصلہ اپیل پٹیشن "
)

EDUCATION_WORDS: str = (
    "تعلیم استاد شاگرد سبق امتحان نمبر رزلٹ ڈگری سند داخلہ فارم فیس کلاس "
    "جماعت نصاب لائبریری مطالعہ تحقیق مقالہ پی ایچ ڈی علم ہنر فن ادب شاعری "
    "شعر غزل نظم کہانی افسانہ ناول ڈراما فلم تصویر تصاویر موسیقی راگ نغمہ گیت "
    "آواز خاموشی زبان لہجہ لفظ جملہ عبارت مضمون مطلب ترجمہ لغت قاموس قواعد "
    "املا خط کتاب کتابیں رسالہ اخبار حروف تہجی محاورہ کہاوت ضرب مثل تاریخ "
    "جغرافیہ ریاضی سائنس طبیعیات کیمیا حیاتیات معاشیات نفسیات فلسفہ منطق "
    "انگریزی اردو عربی فارسی ہندی سنسکرت "
)

TECH_WORDS: str = (
    "کمپیوٹر موبائل فون ٹیبلٹ اسمارٹ اسکرین مانیٹر کیبورڈ ماؤس پرنٹر "
    "اسکینر اسپیکر ہیڈفون مائیک ویبکیم کیمرہ چارجر بیٹری پاور کیبل کنیکشن "
    "سگنل نیٹ ورک انٹرنیٹ وائی فائی بلوٹوتھ ہاٹ اسپاٹ ڈیٹا سرور کلائنٹ ہوسٹنگ "
    "ڈومین ویب سائٹ براؤزر صفحہ سرچ انجن کوکی کیش میموری اسٹوریج ڈرائیو "
    "فلیش یو ایس بی فائل فولڈر ڈاکومنٹ پی ڈی ایف ورڈ ایکسل پریزنٹیشن سافٹ ویئر "
    "ہارڈ ویئر پروگرام پروگرامر پروگرامنگ کوڈ کوڈنگ اسکرپٹ لائبریری فریم ورک "
    "ورژن اپڈیٹ اپگریڈ بگ ایرر لاگ ان اکاؤنٹ یوزرنیم پاس ورڈ پروفائل "
    "سیٹنگ سیٹنگز آپشن مینو بٹن آئیکن ٹیب ونڈو نوٹیفکیشن الرٹ ڈاؤن لوڈ اپ لوڈ "
    "اسٹریم اسٹریمنگ ویڈیو آڈیو پوڈکاسٹ پلے لسٹ ای میل پیغام پیغامات چیٹ "
    "چیٹنگ چیٹبوٹ واٹس ایپ فیس بک ٹویٹر انسٹاگرام یوٹیوب گوگل مائیکروسافٹ "
    "ایپل اینڈرائیڈ ونڈوز لینکس ایپلیکیشن انسٹال انسٹالر پیکج زپ "
    "کلاؤڈ کمپیوٹنگ ورچوئل ڈیجیٹل مشین لرننگ ڈیپ لرننگ نیورل الگورتھم ماڈل "
    "ٹریننگ مصنوعی ذہانت روبوٹ روبوٹکس آٹومیشن خودکار سینسر پروسیسر چپ سرکٹ "
    "ٹیکنالوجی ٹیک سائبر سیکیورٹی ہیکر وائرس اینٹی وائرس فائر وال انکرپشن "
    "توثیق بلاکچین کرپٹو کرنسی ٹوکن والٹ ٹرانزیکشن ادائیگی آن لائن "
    "لائیو ایمپلیفائر سیٹلائٹ نیویگیشن نقشہ مقام پلیٹ فارم "
    "مارکیٹ پلیس ڈلیوری ٹریکنگ رسید بل پرچی ڈسکاؤنٹ آفر کیش بیک "
    "موبائل بینکنگ بیکاپ ری اسٹارٹ ٹول بار اسکرین شاٹ "
)

SPORT_WORDS: str = (
    "کھیل کھلاڑی ٹیم میچ مقابلہ اننگز رن وکٹ گیند بلا بیٹ بولر بلے باز کرکٹ "
    "ہاکی فٹبال ٹینس بیڈمنٹن شطرنج تیراکی کشتی دوڑ میراتھن اولمپک تمغہ انعام "
    "جیت شکست ٹرافی کوچ ریفری اسٹیڈیم گراؤنڈ پچ میدان کپتان ریاضیات "
    "اداکار اداکارہ ہدایت کار ٹکٹ شو تقریب جشن میلہ شادی ولیمہ منگنی ماتم "
    "جنازہ دعوت ضیافت تحفہ تحائف مبارکباد تعزیت خوشی غمی "
)

# Second seed tier - extra domain vocabulary merged into the sections above.
ADDITIONAL_SEEDS: Dict[str, str] = {
    "nature": (
        "پیپل نیم برگد بیری کیکر ٹہنی شاخ شاخیں پتوں جڑوں بیجوں چراگاہ سبزہ "
        "جنگلات زرافہ زیبرا ہرن سانپوں ازگر کوبرا مگرمچھ جھینگے کیکڑے سیپ مرجان "
        "مینڈک چھپکلی گرگٹ ریچھ بندر گوریلا کینگرو کوآلا پانڈا خچر بیل بھینسیں "
        "بکریاں بھیڑیں مرغیاں مرغے بطخیں کبوتروں طوطے کویل بلبل مینا فاختہ مور "
        "مورنی شکرا الوں چمگادڑ تتلیاں مکھیاں مکڑیاں چیونٹیاں بھڑ ٹڈا کھٹمل "
        "بگلا ہنس ہنسوں بازوں شہد گھونسلہ انڈے دھوپ ہیٹ وار رِم جھیم بوندا باندی "
        "بدلیاں چاندنی ستاروں سیارہ سیارے خلاء خلا کہکشائیں شہاب ثاقب نظام شمسی "
    ),
    "place": (
        "دروازوں کھڑکیاں دیواریں چھتیں صحنوں کمرے محراب گنبد مینار عمارت عمارتیں "
        "بلند عمارت ہوٹل ریسٹورنٹ ریسٹورانٹ کیفے چائے خانہ کتب خانہ عجائب گھر "
        "چڑیا گھر میوزیم تھانہ چوکی عدالت خانہ دفتروں فیکٹری کارخانہ ورکشاپ "
        "گودام منڈیاں بازارچہ پھاٹک چوکیداری برگ پلازہ مال اسٹاپ پٹرول پمپ "
        "بس اسٹاپ ٹرمینل ایرپورٹ ایئرپورٹ گودی بندرگاہیں کشتیاں جہازوں ریلوے "
        "کوہستان پہاڑیاں وادیاں دریاﺅں ساحلوں جزیرہ جزیرے جنگل گھاٹی میدان "
        "کھیت کھلیان گاؤں گاؤں والا دیہات محلہ گلی کوچے سڑکیں گزرگاہ شاہراہیں "
    ),
    "food": (
        "کچوری سموسے پکوڑے دہی بڑے چھولے چنے لوبیا راجما سرسوں متھرا چکی کی روٹی "
        "تندوری نان کلچہ پراٹھا پوری بھٹورا ڈبل روٹی کیک بسکٹ ٹافیاں مٹھائی "
        "رس گلہ گلاب جامن برفی لڈو جلیبی پاپڑی سوہان حلوہ پوری کھیر فرنی کسٹرڈ "
        "جلیبیاں کھویا ملائی ربڑی پنیر دہی لسی چھاچھ شربت ٹھنڈا لسی ٹھنڈائی "
        "انار دانہ گڑ والا چینی والا نمکین بسکٹ چرمرا چنا زردہ بریانی پلاؤ "
        "کڑھی نہاری حلیم کبابوں کوفتہ ٹکہ کھیرا سلاد رائتہ چٹنی"
    ),
    "household": (
        "چابیوں تالے ہتھوڑے کلہاڑی آریاں پیچکسیں ڈبوں ٹوکریاں بوتلیں گلاسوں "
        "تھرموس فلیسک چولہے اوون میں ٹوسٹر بلینڈر مکسچر گرائنڈر جوسر کیتلی "
        "سماور چائے دانی پیالی طشتری چمچے کانٹے چھری کدوکش چھلنی سال گرنی "
        "پیمانہ ترازو میٹر گھڑی دیواری گھڑی ساعت الارم سوئیاں دھاگے کپڑے "
        "قینچیاں استری بجلی استری جھاڑو پوچے بالٹی مغز صابن دان تولیے رومال "
    ),
    "clothing": (
        "کرتے پاجامے شلواروں قمیضوں دوپٹے چادریں شالیں سوٹنگ کوٹوں جیکٹیں "
        "سویٹرز ٹوپیوں پگڑیاں جوتوں چپلوں سینڈل موزے دستانے بٹوے چوڑیاں کنگن "
        "انگوٹھیاں ہاروں زیورات جھمکے بالیاں نتھ ناک کی نتھ پازیب بندھن "
        "ریشمی اونی کپاس والا لینن بنناں دھوتی پٹکا صدری واسکٹ شلوار قمیض "
    ),
    "body": (
        "پلکیں بھنوﺅں ماتھا کندھے بازﺅں کہنیاں گھٹنے ٹخنے ایڑیاں پنجے "
        "ہتھیلیاں انگلی کے نشان ناخنوں رگوں شریانیں پٹھے عضلات حرام مغز ریڑھ "
        "پسلیاں پھیپھڑا دل کی دھڑکن نبض فشار خون شوگر ذیابیطس کینسر ورم سوجن "
        "چوٹ زخم پٹی مرہم اینٹی بائیوٹک گولی کیپسول شربت ٹانکا ٹانکے پلستر "
        "ایکس رے الٹرا ساؤنڈ اسٹیتھو اسکوپ تھرمامیٹر آکسیجن ماسک وارڈ "
    ),
    "person": (
        "پروفیسر لیبارٹری اسسٹنٹ ریسرچ سکالر محقق مترجم ناشر مدیر صحافی فوٹو "
        "گرافر ہدایت کار پروڈیوسر فنکار نقاش خطاط گلوکار موسیقار ڈرمر بانسری "
        "نواز اداکارہ ماڈل رقاص بھانڈ نٹ مڈل کلاک ملاح ماہی گیر شکاری چرواہا "
        "باغبان مالی رکشہ والا ٹیکسی ڈرائیور ڈرائیور کنڈکٹر ٹکٹ چیکر چوکیدار "
        "گیٹ کیپر باورچی دودھ والا سبزی والا پھل والا کریانہ والا تاجر دکاندار "
        "سوداگر بروکر ایجنٹ نمائندہ ڈاکیا ڈاک والا خط بردار قاصد سفیر وزیر مشیر "
    ),
    "tech": (
        "ٹچ اسکرین اسمارٹ فون فیچر فون اینڈرائیڈ ایپ آئی او ایس اپ ڈیٹس ایموجی "
        "ایموجیز استیکر گروپ چیٹ ویڈیو کال وائس کال کانفرنس میٹنگ لنک شیئر "
        "ذاتی پیغام پیج ریچ کمنٹ لائک شیئر سبسکرائب چینل پلے بیک اسٹریمنگ "
        "براڈ بینڈ فائبر ڈی ایس ایل روٹر ماڈم ایتھرنیٹ نیٹ ورک کیبل وائرلیس "
        "پاس کی ہاٹ سپاٹ ہاٹ اسپاٹ ڈیٹا پیک ڈیٹا کارڈ سم کارڈ میموری کارڈ "
        "ہارڈ ڈسک سالڈ اسٹیٹ ڈرائیو ایس ایس ڈی بیک اپ کلاؤڈ اسٹوریج "
        "لاگ فائل ای میل ایڈریس سبجیکٹ ان باکس اسپام ٹوک اپلوڈ ڈاؤنلوڈ "
        "اسکرین شاٹ ریکارڈنگ ایڈیٹر ورڈ پریس بلوگ وی لاگ پوڈکاسٹ "
        "ایپلیکیشن اسٹور گوگل پلے اسٹور گوگل ڈرائیو "
        "مصنوعی ذہانت چیٹ جی پی ٹی جنریٹو ماڈل ٹوکنائزیشن لینگویج ماڈل "
        "پروگرامنگ لینگویج ازگر جاوا سی شارپ جاوا اسکرپٹ ٹائپ اسکرپٹ "
        "ڈیٹا بیس ایس کیو ایل کوئری ٹیبل انڈیکس سرور ہوسٹنگ ڈومین نیم "
    ),
    "society": (
        "بجٹ اجلاس بلدیہ بلدیاتی میونسپل کمشنر ڈپٹی کمشنر اسسٹنٹ کمشنر "
        "تحصیلدار پٹواری گرداور تحصیلدار چوکی دار تھانیدار ایس ایچ او "
        "مجسٹریٹ سیشن جج ہائی کورٹ سپریم کورٹ ریفرنس درخواست وکالت نامہ "
        "اقرار نامہ حلف نامہ گواہ گواہی شہادت ضمانت ضمانتی وارنٹ گرفتاری "
        "تلاشی چھاپہ رشوت رشوت خور بدعنوانی احتساب نیب محکمہ دفاتر "
        "وزارت سیکرٹری ایڈیشنل سیکرٹری جوائنٹ سیکرٹری افسر شاہی نوکر شاہی "
        "خریداری ٹھیکہ ٹینڈر بولی نیلام منڈی بھاؤ نرخ مہنگائی افراط زر "
        "سرمایہ کاری شیئر بازار حصص منافع نقصان کاروباری شراکت داری "
        "لیبر یونین مزدوروں حقوق انسانی حقوق بنیادی حقوق شہری حقوق ووٹر "
        "حلقہ پولنگ اسٹیشن بیلٹ پیپر الیکشن کمیشن نتائج اعلان حلف وفاداری"
    ),
    "education": (
        "نرسری کنڈر گارٹن پرائمری مڈل ہائی اسکول میٹرک انٹرمیڈیٹ بی اے "
        "بی ایس سی ایم اے ایم ایس سی ایم فل داخلہ ٹیسٹ انٹری ٹیسٹ "
        "داخلہ پالیسی کوٹہ اسکالرشپ وظیفہ وظائف فیسوں رعایت حاضری "
        "غیر حاضری چھٹی کی درخواست ٹائم ٹیبل نصابی کتابیں کاپیں کاپی "
        "پنسل پین ربڑ شارپنر جیومیٹری باکس بستہ اسکول بیگ یونیفارم "
        "ڈسپلن جرمانہ انعام تمغہ اسناد سند یافتہ گریجویٹ پوسٹ گریجویٹ "
        "پیپر سوال نامہ جوابی پرچہ جچ نمبروں پاس فیل امتیازی نمبر "
        "ٹاپر پوزیشن اول دوم سوم مشق سبق یادداشت نوٹس خلاصہ مباحثہ مضمون نویسی "
    ),
    "abstract": (
        "امانت دیانت خیانت بددیانتی رشوت خوری بدعنوانی خود غرضی ایثار قربانی "
        "ہمدردی غم گساری دل جوئی دل داری بے حسی سنگ دلی نرم دلی سخت دلی "
        "شکر گزاری ناشکری نمک حلالی نمک حرامی وفاداری بے وفائی مہربانی "
        "بدسلوکی خوش اخلاقی بداخلاقی سلیقہ بے سلیقگی سمجھ داری ناسمجھی "
        "بصیرت دور اندیشی غلط اندیشی خود اعتمادی اعتماد باہمی اعتماد "
        "اتحاد اتفاق اختلاف نفاق حسد رقابت مسابقت ہم آہنگی بے چینی بے سکونی "
        "سکون قلب اطمینان بے قراری تڑپ بے تاب تابیں قرار وارفتگی سرور طرب "
        "اندوہ الم دکھی دکھیاری غمگین مسرت شادمانی خوش حالی تنگ حالی "
        "دعا سلام درود فاتحہ ایصال ثواب صدقہ خیرات فدیہ کفارہ قربانی "
        "اذان اقامت وضو غسل تیمم سجدہ رکوع قیام تشہد سلام پھیرنا جماعت "
        "جمعہ عیدین شب قدر اعتکاف تراویح تہجد اشراق چاشت اوابین "
    ),
    "adjective": (
        "اونچ نیچ گہر اتھل ہموار ناہموار ٹیڑھا سیدھا کھڑا جھکا ترچھا "
        "گول بیضوی نوکیلا کند دھار دار بھاری پھرتیلا چست سڈول متناسب "
        "خوشبودار بدبودار چکنا کھردرا ریشے دار گھنا ویران آباد شاداب ہرا بھرا "
        "خشک نم زنگ آلود چمکتی دمکتی مدھم روشن تاریک صاف شفاف گدلا "
        "ذہین کند ذہن بیدار غافل چوکس لاپرواہ محتاط بے پروا مخلص بے غرض "
        "خود غرض ضدی ہٹی ضد کرنے والا نرم مزاج سخت گیر کھرا کھوٹا "
        "اصلی نقلی مصنوعی قدرتی تازہ دم سرسبز پُر سکون بے سکون پُر امید مایوس "
        "کم قیمت زیادہ قیمت منافع بخش نقصان دہ صحت بخش مضر صحت "
    ),
    "time": (
        "صبح سویرے دن چڑھے دوپہر کو ڈھلتی شام رات گئے آدھی رات پو پھٹنے "
        "طلوع آفتاب غروب آفتاب شفق سحر بھور پہر پہروں لمحہ بھر "
        "گزشتہ آئندہ موجودہ حالیہ سابقہ آنے والا گزرا ہوا اگلا پچھلا "
        "روزانہ ہفتہ وار ماہانہ سالانہ سہ ماہی شش ماہی وقتی عارضی مستقل "
        "تعطیلات چھٹیاں تہوار میلہ موسم برسات گرمیوں سردیوں بہار خزاں "
    ),
    "color": (
        "سیاہ سفید سرخوں نیلگوں سبزی مائل پیلاہٹ سرخی نیلاہٹ سیاہی "
        "رنگ برنگے کثیر رنگ یک رنگ دو رنگ سہ رنگ سنہرا تانبئی مسی "
        "چاندی جیسا سونے جیسا موتی جیسا پھیکا گہرا رنگین بے رنگ "
        "چوکھٹ مثلث مربع مستطیل مخروط گھنڈ دار بیضہ دائرہ نیم دائرہ "
    ),
}

# Explicit irregular / idiomatic derivations that no rule should invent.
EXTRA_FORMS: Dict[str, Tuple[str, ...]] = {
    "باغ": ("باغبان", "باغیچہ", "باغات", "باغوں"),
    "کتاب": ("کتابیں", "کتابوں", "کتابچہ", "کتب"),
    "دوست": ("دوستی", "دوستوں", "دوستوں", "دوستانہ", "دوستیاں"),
    "گھر": ("گھروں", "گھریلو", "گھروالا", "گھروالی"),
    "دکان": ("دکاندار", "دکانیں", "دکانوں"),
    "ملک": ("ملکوں", "ملکی", "ملک گیر"),
    "شہر": ("شہروں", "شہری", "شہریت"),
    "زمین": ("زمینیں", "زمینی", "زمیندار"),
    "دولت": ("دولت مند", "دولتیں"),
    "کار": ("کاروبار", "کاریں", "کاروں"),
    "ہاتھ": ("ہاتھوں", "ہاتھی", "ہتھیار"),
    "پانی": ("پانیوں", "پانی والا", "پنیر"),
    "دودھ": ("دودھ والا", "دودھیا"),
    "کھانا": ("کھانے", "کھانے پینے"),
    "پڑھنا": ("پڑھائی", "پڑھاکو"),
    "لکھنا": ("لکھائی", "لکھاری"),
    "بڑا": ("بڑائی", "بڑاپن"),
    "گندا": ("گندگی", "گندائی"),
    "ٹھنڈا": ("ٹھنڈک", "ٹھنڈی"),
    "میٹھا": ("میٹھاس", "میٹھی"),
    "کڑوا": ("کڑواہٹ", "کڑوی"),
    "کھٹا": ("کھٹاس", "کھٹی"),
    "سونا": ("سونے", "سنیار"),
    "پھول": ("پھولوں", "پھولی", "پھول والا"),
    "دل": ("دلی", "دلدار", "دلکش"),
    "عقل": ("عقلمند", "عقلی"),
    "علم": ("علمی", "عالم", "علوم"),
    "خبر": ("خبریں", "خبروں", "بے خبر"),
    "کام": ("کامی", "کاموں"),
    "روز": ("روزانہ", "روزی"),
    "ماہ": ("ماہانہ", "ماہوار"),
    "سال": ("سالانہ", "سالگرہ", "سالوں"),
    "ہفتہ": ("ہفتہ وار", "ہفتے"),
    "وقت": ("وقتی", "وقتاً"),
    "نوکری": ("نوکریاں", "نوکریوں"),
    "کمپیوٹر": ("کمپیوٹری", "کمپیوٹرز", "کمپیوٹروں"),
    "وائرس": ("وائرسی", "وائرسز"),
}

# Words that take the "بھر" emphasise (رات بھر -> راتبھر).
_BHAR_HOSTS: Set[str] = {
    "دن", "رات", "صبح", "شام", "سال", "مہینہ", "ہفتہ", "عمر", "جنم", "غم",
    "خوشی", "جیون", "دنیا", "جہان",
}

# Words that form a real compound with والا / والی (گھر والا، دودھ والا).
_WALA_HOSTS: Set[str] = {
    "گھر", "دکان", "بازار", "پانی", "دودھ", "روٹی", "چائے", "کھانا", "سالن",
    "کپڑا", "جوتا", "ٹوپی", "بچہ", "بچی", "لڑکا", "لڑکی", "کام", "مال", "دل",
    "ہاتھ", "زمین", "مکان", "گاڑی", "سائیکل", "موبائل", "کمپیوٹر", "کتاب",
    "دوا", "سبزی", "پھل", "پھول", "مچھلی", "گوشت", "انڈا", "چاول", "نمک",
    "مرچ", "تیل", "چینی", "آٹا", "بس", "ٹرین", "جہاز", "کشتی", "باغ",
    "کھیت", "فصل", "بکری", "گائے", "بھینس", "مرغی", "کتا", "بلی", "شہر",
    "گاؤں", "محلہ", "سڑک", "پل", "پہاڑ", "دریا",
}

# Productive prefixes and the bases they really attach to in Urdu.
_PREFIX_HOSTS: Dict[str, Set[str]] = {
    "بے": {"کار", "نام", "خبر", "بس", "حال", "شمار", "وفا", "ادب", "ہوش", "اخلاق",
           "ایمان", "شک", "شبہ", "جان", "حس", "چارہ", "پردہ", "رحم", "خواہش", "زور",
           "آرام", "بھروسہ", "وقت", "مطلب", "حد", "قانون", "مثال", "نظیر", "نقصان",
           "قصور", "گناہ", "سوچ", "سمجھ", "سہارا", "دل", "دھڑک", "خوف", "فائدہ"},
    "نا": {"کام", "اہل", "خوش", "پسند", "قابل", "صاف", "تمام", "انصاف", "فرمان",
           "گوارا", "جان", "ممکن", "کافی", "خدا", "شکر", "سپاہی", "چیز"},
    "غیر": {"ضروری", "ممکن", "حاضری", "موجود", "جانبدار", "ملکی", "یقینی", "مفید",
            "قانونی", "مستحکم", "متنازعہ", "سیاسی", "فطری", "معمولی", "انصافی"},
    "کم": {"زور", "بخت", "عمر", "آمدنی", "ظرف", "سواد", "نصیب", "بہتر", "کم",
           "مایہ", "ہمت", "مقدار", "شرح", "وزن", "قیمت"},
    "خوش": {"خبر", "شکل", "مزاج", "آواز", "رائے", "قسمت", "نصیب", "اندام", "خط",
            "خوش", "حالات", "بو", "ذائقہ", "نظم", "اسلوب"},
    "بد": {"نام", "تمیز", "مزاج", "شکل", "صورت", "چلن", "نصیب", "قسمت", "حال",
           "بھلا", "خو", "اطوار", "سلوکی", "عنوان", "نظمی", "انتظام"},
    "ہم": {"شکل", "نام", "وطن", "مذہب", "زبان", "سبب", "عقل", "درد", "کلام",
           "مشرب", "نشین", "عصر", "راز", "آغوش", "مکتب", "قوم", "جنس", "رنگ"},
    "خود": {"مختار", "اعتماد", "غرض", "پسند", "کار", "کفایت", "دار", "سوز", "نمائی"},
}

# Sections that take derivational expansion in --exhaustive mode (loanwords,
# function words and numbers are excluded: expanding them only creates noise).
EXHAUSTIVE_SECTIONS: Tuple[str, ...] = (
    "adjective", "abstract", "society", "person", "place", "nature", "food",
    "body", "household", "clothing", "color", "education",
)

# Ordinals / fractions that must not receive an extra "واں".
_ORDINAL_SKIP: Set[str] = {
    "پہلا", "دوسرا", "تیسرا", "چوتھا", "پانچواں", "چھٹا", "ساتواں", "آٹھواں",
    "نواں", "دسواں", "آدھا", "پاؤ", "چوتھائی", "تہائی", "دوگنا", "تگنا", "چوگنا",
    "نصف", "فیصد", "سو", "ہزار", "لاکھ", "کروڑ", "ارب", "کھرب",
}

# Words that take "والا / والی / والے" (concrete, agentive nouns).
_CONCRETE_SECTIONS: Set[str] = {
    "place", "person", "body", "food", "household", "clothing", "tech",
    "sport", "nature",
}


@dataclass(frozen=True)
class Rule:
    """Which morphology a lexicon section is allowed to generate."""

    plurals: str = "none"                  # none | urdu | loan
    suffixes: Tuple[str, ...] = ()         # productive derivational suffixes
    prefixes: Tuple[str, ...] = ()         # بے / نا / غیر / کم ...
    modifiers: Tuple[str, ...] = ()        # والا / سا / سی ...
    gender_forms: bool = False             # adjective feminine + oblique
    abstract_forms: bool = False           # -ائی / -ی / -پن nominalisation


RULES: Dict[str, Rule] = {
    "function": Rule(),
    "number": Rule(suffixes=("واں",)),
    "time": Rule(plurals="urdu", suffixes=("وار",)),
    "nature": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
    "place": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا", "والی")),
    "person": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
    "body": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
    "food": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
    "household": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
    "clothing": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
    "proper": Rule(),                     # names stay untouched
    "abstract": Rule(plurals="urdu", suffixes=("ی",)),
    "color": Rule(suffixes=("ی",), gender_forms=True),
    "adjective": Rule(
        prefixes=("بے", "نا", "غیر", "کم", "خوش", "بد", "ہم", "خود"),
        modifiers=("سا", "سی"),
        gender_forms=True,
        abstract_forms=True,
    ),
    "society": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
    "education": Rule(plurals="urdu", suffixes=("ی",)),
    "tech": Rule(plurals="loan", suffixes=("ی",), modifiers=("والا",)),
    "sport": Rule(plurals="urdu", suffixes=("ی",), modifiers=("والا",)),
}


# ---------------------------------------------------------------------------
# 3. THE FORGE   (deterministic, streaming word generator)
# ---------------------------------------------------------------------------
class LexiconForge:
    """Compiles every Urdu token the engine can plausibly need.

    Stages (all deterministic -> builds are byte-for-byte reproducible):

        1. curated seeds   -> daily / academic / technical vocabulary
        2. plurals         -> real Urdu plural + oblique phonology
        3. derivations     -> attach_suffix() with orthographic guards
        4. prefix families -> بے / نا / غیر / کم / خوش ... + root (+ suffix)
        5. modifiers       -> والا، سا، سی، بھر، وار on the right hosts
        6. adjective layer -> feminine/oblique + abstract nominalisation
        7. verb layer      -> infinitive, habitual, subjunctive, perfective,
                              future, imperative, polite and agentive forms
        8. extra forms     -> hand-curated irregulars (EXTRA_FORMS)
        9. exhaustive mode -> optional maximum-recall combinatorial explosion
    """

    def __init__(self, keep_diacritics: bool = False, min_len: int = 2, max_len: int = 40):
        self.keep_diacritics = keep_diacritics
        self.min_len = min_len
        self.max_len = max_len
        self._seen: Set[str] = set()
        self.stats: Dict[str, int] = {}

    # ---------------------------------------------------------------- core
    def _add(self, sink: List[str], raw: str, bucket: str) -> bool:
        token = canonicalize(raw, self.keep_diacritics)
        if not token or token in self._seen or not is_valid_token(token, self.min_len, self.max_len):
            return False
        self._seen.add(token)
        sink.append(token)
        self.stats[bucket] = self.stats.get(bucket, 0) + 1
        return True

    @staticmethod
    def _split(blob: str) -> List[str]:
        return [w for w in blob.split() if w]

    def _sections(self) -> Dict[str, List[str]]:
        merged: Dict[str, List[str]] = {}
        for name, words in self._base_sections().items():
            extra = ADDITIONAL_SEEDS.get(name, "")
            merged[name] = words + self._split(extra)
        return merged

    @staticmethod
    def _base_sections() -> Dict[str, List[str]]:
        return {
            "function": LexiconForge._split(FUNCTION_WORDS),
            "number": LexiconForge._split(NUMBER_WORDS),
            "time": LexiconForge._split(TIME_WORDS),
            "nature": LexiconForge._split(NATURE_WORDS),
            "place": LexiconForge._split(PLACE_WORDS),
            "proper": LexiconForge._split(PROPER_NOUNS),
            "person": LexiconForge._split(PERSON_WORDS),
            "body": LexiconForge._split(BODY_WORDS),
            "food": LexiconForge._split(FOOD_WORDS),
            "household": LexiconForge._split(HOUSEHOLD_WORDS),
            "clothing": LexiconForge._split(CLOTHING_WORDS),
            "animal": LexiconForge._split(NATURE_WORDS),
            "color": LexiconForge._split(COLOR_WORDS),
            "abstract": LexiconForge._split(ABSTRACT_WORDS),
            "adjective": LexiconForge._split(ADJECTIVE_WORDS),
            "society": LexiconForge._split(SOCIETY_WORDS),
            "education": LexiconForge._split(EDUCATION_WORDS),
            "tech": LexiconForge._split(TECH_WORDS),
            "sport": LexiconForge._split(SPORT_WORDS),
        }

    # --------------------------------------------------------------- forge
    def forge(self, exhaustive: bool = False) -> Tuple[List[str], List[str]]:
        """Return ``(all_tokens, curated_roots)``."""
        sections = self._sections()
        curated: List[str] = []
        out: List[str] = []

        # stage 1 - curated seeds
        for words in sections.values():
            for word in words:
                self._add(curated, word, "1_curated")
        out.extend(curated)
        self.stats["1_curated_total"] = len(curated)

        # stages 2-6 - per-section morphology
        for name, words in sections.items():
            self._apply_rule(name, words, out)

        # stage 7 - verbs
        self._verbs(out)

        # stage 8 - curated irregulars
        before = len(out)
        for base, forms in EXTRA_FORMS.items():
            self._add(out, base, "8_extra_forms")
            for form in forms:
                self._add(out, form, "8_extra_forms")
        self.stats["8_extra_total"] = len(out) - before

        # stage 9 - optional combinatorial maximum-recall expansion
        if exhaustive:
            expandable: List[str] = []
            for name in EXHAUSTIVE_SECTIONS:
                expandable.extend(sections.get(name, ()))
            self._exhaustive(out, expandable or curated)
        return out, curated

    # ------------------------------------------------------- rule execution
    def _apply_rule(self, name: str, words: Sequence[str], out: List[str]) -> None:
        rule = RULES.get(name)
        if rule is None:
            return
        before = len(out)
        bucket = "2_%s" % name
        is_number = (name == "number")
        for word in words:
            if len(word) < 2:
                continue
            # 1. plurals + oblique forms
            if rule.plurals != "none" and _pluralizable(word):
                for form in urdu_plurals(word, loanword=(rule.plurals == "loan")):
                    self._add(out, form, bucket)
            # 2. derivational suffixes (orthography-guarded)
            if len(word) >= 3:
                for suffix in rule.suffixes:
                    if is_number and word in _ORDINAL_SKIP:
                        continue
                    self._add(out, attach_suffix(word, suffix), bucket)
            # 3. productive prefixes - only on bases that really take them
            if len(word) >= 3:
                for prefix in rule.prefixes:
                    hosts = _PREFIX_HOSTS.get(prefix)
                    if hosts and word in hosts:
                        self._add(out, prefix + word, bucket)               # بےکار
                        self._add(out, prefix + attach_suffix(word, "ی"), bucket)  # بےکاری
            # 4. compound modifiers
            self._modifiers(name, word, rule, out, bucket)
            # 5. adjective agreement + nominalisation
            if rule.gender_forms:
                self._gender_forms(word, out, bucket)
            if rule.abstract_forms:
                self._abstract_forms(word, out, bucket)
        self.stats["%s_total" % bucket] = len(out) - before

    def _modifiers(self, name: str, word: str, rule: Rule,
                   out: List[str], bucket: str) -> None:
        """Attach ہر compound modifier the host word really accepts."""
        for mod in rule.modifiers:
            if mod in ("والا", "والی", "والے"):
                if word in _WALA_HOSTS and word[-1] != "و":
                    self._add(out, word + mod, bucket)
            elif mod in ("سا", "سی", "سے"):
                if word[-1] not in "اہیے" and word[-1] != mod[0]:
                    self._add(out, word + mod, bucket)           # اچھاسا، تیزسا
            elif len(word) >= 3:
                self._add(out, word + mod, bucket)
        if word in _BHAR_HOSTS:
            self._add(out, word + "بھر", bucket)                 # راتبھر، دنبھر

    # ------------------------------------------------------------ adjectives
    def _gender_forms(self, word: str, out: List[str], bucket: str) -> None:
        """Urdu adjectives agree in gender/number: اچھا -> اچھی، اچھے."""
        if word.endswith("ا") and len(word) >= 3:
            self._add(out, word[:-1] + "ی", bucket)      # feminine singular
            self._add(out, word[:-1] + "ے", bucket)      # oblique / plural

    def _abstract_forms(self, word: str, out: List[str], bucket: str) -> None:
        """Nominalise adjectives: بڑا -> بڑائی، نرم -> نرمی، اچھا -> اچھاپن."""
        if len(word) < 3:
            return
        if word.endswith("ا"):
            self._add(out, word[:-1] + "ائی", bucket)    # بڑائی، اونچائی، گہرائی
            self._add(out, word + "پن", bucket)          # بڑاپن، اچھاپن
        elif word.endswith("ہ"):
            return
        elif word.endswith("ی"):
            return
        else:
            self._add(out, word + "ی", bucket)           # نرمی، گرمی، سختی
            self._add(out, word + "پن", bucket)          # صاف پن

    # ------------------------------------------------------------------ verbs
    def _verbs(self, out: List[str]) -> None:
        before = len(out)
        roots = self._split(VERB_ROOTS)
        for root in roots:
            if len(root) < 2:
                continue
            for form in conjugate(root):
                self._add(out, form, "7_verb_forms")
        self.stats["7_verb_total"] = len(out) - before

    # -------------------------------------------------------------- exhaustive
    def _exhaustive(self, out: List[str], curated: Sequence[str]) -> None:
        """Maximum-recall mode: cross-product affixes over every curated root.

        Every emitted token is still *letter-legal* Urdu, which makes this mode
        valuable for spell-checking / fuzzy-search recall. It deliberately
        over-generates, so it is opt-in (``--exhaustive``).
        """
        before = len(out)
        prefixes = ("بے", "نا", "لا", "غیر", "ہم", "خود", "نو", "کم", "خوش", "بد")
        suffixes = ("ی", "پن", "گی", "یت", "دار", "مند", "ناک", "انہ", "کار", "دان")
        stack_prefixes = ("بے", "نا", "غیر", "کم")          # safest stackers
        stack_suffixes = ("ی", "پن", "گی")                  # safest heads
        for word in curated:
            if len(word) < 3 or not _pluralizable(word):
                continue
            for suf in suffixes:
                self._add(out, attach_suffix(word, suf), "9_exhaustive")
            for pre in prefixes:
                self._add(out, pre + word, "9_exhaustive")
                if pre in stack_prefixes:
                    for suf in stack_suffixes:
                        self._add(out, pre + attach_suffix(word, suf), "9_exhaustive")
        self.stats["9_exhaustive_total"] = len(out) - before


# ---------------------------------------------------------------------------
# 4. VERB MORPHOLOGY   (root -> full Urdu conjugation family)
# ---------------------------------------------------------------------------
VERB_ROOTS: str = (
    "ہو کر جا آ دیکھ سن بول کہہ پڑھ لکھ کھا پی سو جاگ اٹھ بیٹھ چل دوڑ رک لے دے "
    "خرید بیچ پکا دھو پہن بنا باندھ کھول توڑ جوڑ ڈھونڈ پا کھو رکھ بھر پھینک "
    "اچھال مار چھوڑ پکڑ سیکھ سکھا سمجھ جان مان مانگ بلا پکار ہنس رو مسکرا شرما ڈر "
    "ڈانٹ سوچ بھول کھیل ناچ گا بجا سنا بتا دکھا چھپا مل ملا بچا بچھ سیک "
    "بن مر جی لڑ جیت ہار گزار سنبھال بدل لٹا سوکھ جل پگھل جم ٹوٹ پھٹ چھیڑ پال "
    "بدلو جھک نکل نکال لٹک لپٹ چمک دمک سنور سدھر سکڑ پھیل گھوم گھسیٹ کھینچ "
    "کھسک سرک سہم تھم تھک گن گنوا بہا بہک اگا اُکھاڑ ڈس ڈسا چبھ نوچ کاٹ پیس "
    "رگڑ سلا سلوا بنوا پہنچ پوچھ اتر چڑھ لہرا جھول جھاڑ پونچھ پھیر سدھار نکھار "
    "کھٹک ٹھہر ٹھونس ٹال ٹیک ٹیپ لپک لپیٹ سنبھلا"
)


# Perfective forms that the general rule cannot derive (irregular verbs).
IRREGULAR_PERFECTIVE: Dict[str, Tuple[str, ...]] = {
    "کر": ("کیا", "کیے", "کیں"),
    "جا": ("گیا", "گئے", "گئیں"),
    "آ": ("آیا", "آئے", "آئیں"),
    "ہو": ("ہوا", "ہوئے", "ہوئیں"),
    "لے": ("لیا", "لیے", "لیں"),
    "دے": ("دیا", "دیے", "دیں"),
    "پی": ("پیا", "پیے", "پیں"),
    "سو": ("سویا", "سوئے", "سوئیں"),
    "ٹوٹ": ("ٹوٹا", "ٹوٹے"),
    "چل": ("چلا", "چلے"),
    "بن": ("بنا", "بنے"),
    "مل": ("ملا", "ملے"),
    "جل": ("جلا", "جلے"),
    "مر": ("مرا", "مرے", "مؤا"),
}


def conjugate(root: str) -> List[str]:
    """Return the productive conjugation family of an Urdu verb *root*.

    ``root`` is the stem without the infinitive ``نا`` (کھا، دیکھ، کر، ڈھونڈ ...).
    The output mixes the *fused* single-token spelling used by this engine
    (کھاتا، دیکھیں، کرنےوالا) which is exactly what a single-space-tokenised
    dictionary needs.
    """
    # ے-final roots (لے، دے) switch to their ی-base for every suffix:
    # دی -> دینا، دیتا، دیا، دیںگے   (never "دےتے")
    if root.endswith("ے"):
        root = root[:-1] + "ی"

    forms: List[str] = [root + "نا", root + "نی", root + "نے", root + "نےوالا",
                        root + "نےوالی", root + "نےوالے"]

    # habitual / imperfective
    forms += [root + "تا", root + "تی", root + "تے", root + "تیں"]

    last = root[-1]
    if last == "و":                                     # ہو، سو، رو
        subj, imper, polite = root + "ئیں", root + "ؤ", root + "ئیے"
        fut, fut_f, fut_pl = root + "گا", root + "گی", root + "ںگے"
    elif last in "اآ":                                  # کھا، جا، آ، بنا
        subj, imper, polite = root + "ئیں", root + "ؤ", root + "ئیے"
        fut, fut_f, fut_pl = root + "ئےگا", root + "ئےگی", root + "ئیںگے"
    elif last == "ی":                                   # دی، لی، جی
        subj, imper, polite = root + "ں", root + "و", root + "ں"
        fut, fut_f, fut_pl = root + "ےگا", root + "ےگی", root + "ںگے"
    else:                                               # دیکھ، کر، پڑھ
        subj, imper, polite = root + "یں", root + "و", root + "یے"
        fut, fut_f, fut_pl = root + "ےگا", root + "ےگی", root + "یںگے"

    forms += [subj, imper, polite, fut, fut_f, fut_pl]

    # perfective (irregulars first, then the regular vowel/consonant rules)
    if root in IRREGULAR_PERFECTIVE:
        forms += list(IRREGULAR_PERFECTIVE[root])
    elif last in "اآ":
        forms += [root + "یا", root + "ئے", root + "ئیں"]        # گایا، آیا، جائیں
    elif last == "و":
        forms += [root + "یا", root + "ئے"]                      # رویا، سوئے
    else:
        forms += [root + "ا", root + "ے"]                        # پڑھا، لکھے
        if last != "ی":
            forms.append(root + "ی")                             # دیکھی، پڑھی
        else:
            forms.append(root + "ں")                             # دیں، لیں

    # causative + verbal nouns (skipped on open syllables: کھلانا is irregular)
    if last not in "اآیو":
        forms += [root + "وانا", root + "وانے"]                  # کروانا، پڑھوانا
        forms += [root + "ائی", root + "اوٹ"]                    # پڑھائی، لکھاوٹ
    return _dedupe(forms)


# ---------------------------------------------------------------------------
# 5. COMPILE + WRITE THE COMPRESSED DATABASE
# ---------------------------------------------------------------------------
def _report_build(stats: Dict[str, int]) -> None:
    print("[urduofdani] lexicon compiled in %.3fs" % stats.get("0_build_seconds", 0.0))
    for key in sorted(stats):
        if key.startswith("0_"):
            continue
        print("    + %-24s %10s" % (key, f"{stats[key]:,}"))
    print("    = %-24s %10s unique Urdu words" % ("TOTAL", f"{stats['0_total_words']:,}"))


def compile_lexicon(
    max_words: int = 0,
    keep_diacritics: bool = False,
    min_len: int = 2,
    max_len: int = 40,
    exhaustive: bool = False,
    verbose: bool = True,
) -> Tuple[List[str], Dict[str, int]]:
    """Compile the lexicon and return ``(sorted_words, stats)``.

    ``max_words=0`` means *unlimited* (keep everything the forge produces).
    When a cap is given, the alphabetical list is sampled evenly so the whole
    alphabet stays represented instead of truncating the tail.
    """
    t0 = time.perf_counter()
    forge = LexiconForge(keep_diacritics=keep_diacritics, min_len=min_len, max_len=max_len)
    words, _roots = forge.forge(exhaustive=exhaustive)
    words.sort()
    total = len(words)

    if max_words and total > max_words:
        step = total / float(max_words)
        words = [words[int(i * step)] for i in range(max_words)]
        total = len(words)

    stats: Dict[str, int] = dict(forge.stats)
    stats["0_total_words"] = total
    stats["0_chars"] = sum(len(w) + 1 for w in words) - 1
    stats["0_build_seconds"] = round(time.perf_counter() - t0, 4)
    if verbose:
        _report_build(stats)
    return words, stats


def _iter_text_chunks(words: Sequence[str], chunk_tokens: int = CHUNK_TOKENS) -> Iterator[str]:
    """Yield the payload in streaming chunks -> never materialises a giant string."""
    for start in range(0, len(words), chunk_tokens):
        yield SEPARATOR.join(words[start:start + chunk_tokens])


def build_urdu_database(
    output_path: str | os.PathLike[str] = DB_FILENAME,
    max_words: int = 0,
    keep_diacritics: bool = False,
    min_len: int = 2,
    max_len: int = 40,
    exhaustive: bool = False,
    verbose: bool = True,
) -> Dict[str, object]:
    """Compile the lexicon and atomically write the gzip binary."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    words, lexicon_stats = compile_lexicon(
        max_words=max_words, keep_diacritics=keep_diacritics,
        min_len=min_len, max_len=max_len, exhaustive=exhaustive, verbose=verbose,
    )

    t0 = time.perf_counter()
    raw_bytes = 0
    # zlib with wbits=31 == raw DEFLATE inside a standard gzip container, and
    # MTIME is 0, so identical seeds always produce a byte-identical artifact.
    compressor = zlib.compressobj(GZIP_LEVEL, zlib.DEFLATED, GZIP_WBITS,
                                  GZIP_MEMLEVEL, zlib.Z_DEFAULT_STRATEGY)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=".urdu_db_", suffix=".part", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "wb") as fh:
            first = True
            for chunk in _iter_text_chunks(words):
                if not first:
                    chunk = SEPARATOR + chunk
                data = chunk.encode("utf-8")
                raw_bytes += len(data)
                block = compressor.compress(data)
                if block:
                    fh.write(block)
                first = False
            tail = compressor.flush()
            if tail:
                fh.write(tail)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)              # atomic replace (Windows-safe)
        try:
            os.chmod(path, 0o644)               # keep the artifact world-readable
        except OSError:
            pass
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    write_seconds = time.perf_counter() - t0

    packed_bytes = path.stat().st_size
    ratio = (1.0 - packed_bytes / raw_bytes) * 100.0 if raw_bytes else 0.0
    stats: Dict[str, object] = {
        **lexicon_stats,
        "0_raw_bytes": raw_bytes,
        "0_packed_bytes": packed_bytes,
        "0_compression_percent": round(ratio, 2),
        "0_write_seconds": round(write_seconds, 4),
        "0_sha256": _sha256(path),
        "0_output": str(path),
    }
    if verbose:
        print(
            "[urduofdani] wrote %s\n"
            "    raw      : %s\n"
            "    gzip     : %s  (%.1f%% smaller)\n"
            "    io time  : %.3fs\n"
            "    sha256   : %s" % (
                path.name, _human(raw_bytes), _human(packed_bytes), ratio,
                write_seconds, stats["0_sha256"],
            )
        )
    return stats


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _human(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return "%d B" % num if unit == "B" else "%.2f %s" % (num, unit)
        num /= 1024.0
    return "%.2f GB" % num


def load_urdu_database(path: str | os.PathLike[str] = DB_FILENAME) -> List[str]:
    """Decompress the whole database and return it as a Python list of words."""
    with gzip.open(path, "rb") as fh:
        payload = fh.read().decode("utf-8")
    return payload.split(SEPARATOR) if payload else []


def iter_urdu_words(path: str | os.PathLike[str] = DB_FILENAME,
                    block_bytes: int = 1 << 20) -> Iterator[str]:
    """Stream words with constant memory - for multi-hundred-MB dictionaries."""
    with gzip.open(path, "rb") as fh:
        carry = ""
        while True:
            block = fh.read(block_bytes)
            if not block:
                break
            text = carry + block.decode("utf-8", errors="ignore")
            parts = text.split(SEPARATOR)
            carry = parts.pop()
            for word in parts:
                if word:
                    yield word
        if carry:
            yield carry


# ---------------------------------------------------------------------------
# 6. RUNTIME ENGINE   (drop-in for any Python app / Tkinter / Flask UI)
# ---------------------------------------------------------------------------
class UrduEngine:
    """In-memory Urdu dictionary with O(1) membership and O(log n) autocomplete.

    Example
    -------
    >>> engine = UrduEngine()                    # auto-finds urdu_database.txt.gz
    >>> len(engine) > 10_000
    True
    >>> "کمپیوٹر" in engine
    True
    >>> engine.suggest("کم", limit=5)[0]
    'کم'
    """

    def __init__(self, path: str | os.PathLike[str] | None = None, lazy: bool = False):
        self.path = Path(path) if path else _locate_database()
        self._words: List[str] = []
        self._lookup: Set[str] = set()
        self.load_seconds = 0.0
        if not lazy:
            self.load()

    # -- lifecycle --------------------------------------------------------
    def load(self) -> "UrduEngine":
        t0 = time.perf_counter()
        self._words = load_urdu_database(self.path)
        self._lookup = set(self._words)
        self.load_seconds = time.perf_counter() - t0
        return self

    def extend(self, words: Iterable[str]) -> "UrduEngine":
        """Merge your own app/domain vocabulary and re-index in one pass."""
        merged = set(self._lookup)
        for word in words:
            token = canonicalize(word)
            if is_valid_token(token):
                merged.add(token)
        self._words = sorted(merged)
        self._lookup = merged
        return self

    # -- queries ----------------------------------------------------------
    def __len__(self) -> int:
        return len(self._words)

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and canonicalize(word) in self._lookup

    def __iter__(self) -> Iterator[str]:
        return iter(self._words)

    def __getitem__(self, index: int) -> str:
        return self._words[index]

    def words(self) -> List[str]:
        return self._words

    def suggest(self, prefix: str, limit: int = 8) -> List[str]:
        """Instant autocomplete via binary search over the sorted word list."""
        prefix = canonicalize(prefix)
        if not prefix:
            return self._words[:limit]
        idx = bisect.bisect_left(self._words, prefix)
        out: List[str] = []
        while idx < len(self._words) and self._words[idx].startswith(prefix):
            out.append(self._words[idx])
            idx += 1
            if len(out) >= limit:
                break
        return out

    def search(self, query: str, limit: int = 20) -> List[str]:
        """Substring search - handy for an offline search box / spell helper."""
        query = canonicalize(query)
        if not query:
            return []
        return [w for w in self._words if query in w][:limit]

    def random_word(self, seed: int | None = None) -> str:
        return random.Random(seed).choice(self._words)

    def info(self) -> Dict[str, object]:
        return {
            "path": str(self.path),
            "words": len(self._words),
            "load_seconds": round(self.load_seconds, 6),
            "packed_bytes": self.path.stat().st_size if self.path.exists() else 0,
        }


def _locate_database() -> Path:
    """Find the DB next to the script, in cwd, in ./data, or inside the bundle."""
    here = Path(__file__).resolve().parent
    candidates = (
        here / DB_FILENAME,
        Path.cwd() / DB_FILENAME,
        here / "data" / DB_FILENAME,
        Path(getattr(sys, "_MEIPASS", here)) / DB_FILENAME,     # PyInstaller onefile
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


# ---------------------------------------------------------------------------
# 7. VERIFY + BENCHMARK
# ---------------------------------------------------------------------------
def verify_database(path: str | os.PathLike[str] = DB_FILENAME,
                    export_txt: str | os.PathLike[str] | None = None) -> bool:
    """Integrity check: gzip stream, single-line payload, no junk, no dupes."""
    path = Path(path)
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8")
    words = text.split(SEPARATOR)

    checks: List[Tuple[str, bool, str]] = [
        ("gzip readable", True, "%d bytes packed payload" % path.stat().st_size),
        ("no newline", "\n" not in text and "\r" not in text, "single line"),
        ("no comma", "," not in text, "comma-free"),
        ("no digits", not _FORBIDDEN.search(text), "digit-free"),
        ("no duplicates", len(words) == len(set(words)),
         "%d tokens / %d unique" % (len(words), len(set(words)))),
        ("all tokens legal", all(is_valid_token(w) for w in words), "100% Urdu letters"),
    ]
    ok = all(passed for _, passed, _ in checks)
    print("[urduofdani] verifying %s" % path.name)
    for name, passed, detail in checks:
        print("    [%s] %-18s %s" % ("PASS" if passed else "FAIL", name, detail))

    if export_txt:
        Path(export_txt).write_bytes(raw)          # raw == the plain single-line text
        print("    [OK]   exported plain text -> %s" % export_txt)
    return ok


def benchmark(path: str | os.PathLike[str] = DB_FILENAME, repeats: int = 5) -> Dict[str, float]:
    """Measure cold decompression + list construction in milliseconds."""
    path = Path(path)
    packed = path.stat().st_size
    timings: List[float] = []
    words: List[str] = []
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter()
        words = load_urdu_database(path)
        timings.append((time.perf_counter() - t0) * 1000.0)     # -> milliseconds

    # separate pass so tracemalloc overhead never pollutes the timings
    tracemalloc.start()
    load_urdu_database(path)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # uncompressed size in UTF-8 BYTES (Urdu letters are 2 bytes each)
    raw_bytes = sum(len(w.encode("utf-8")) + 1 for w in words) - 1 if words else 0
    best = min(timings)
    avg = sum(timings) / len(timings)
    per_sec = len(words) / (avg / 1000.0) if avg else 0.0
    saved = (1 - packed / raw_bytes) * 100.0 if raw_bytes else 0.0

    print("\n" + "=" * 68)
    print(" urduofdani :: B E N C H M A R K")
    print("=" * 68)
    print("  database          : %s" % path.name)
    print("  words             : %s" % f"{len(words):,}")
    print("  packed (.gz)      : %s" % _human(packed))
    print("  unpacked (RAM)    : %s" % _human(raw_bytes))
    print("  compression saved : %.1f%%" % saved)
    print("  cold load (best)  : %.3f ms" % best)
    print("  cold load (avg)   : %.3f ms   (%d runs)" % (avg, len(timings)))
    print("  throughput        : %s words/sec" % f"{per_sec:,.0f}")
    print("  peak RAM (loader) : %s" % _human(peak))
    print("  engine ready      : UrduEngine().load_seconds -> %.6f s" % (best / 1000.0))
    print("=" * 68 + "\n")

    return {
        "words": float(len(words)),
        "packed_bytes": float(packed),
        "raw_bytes": float(raw_bytes),
        "best_ms": best,
        "avg_ms": avg,
        "words_per_sec": per_sec,
        "peak_bytes": float(peak),
    }


# ---------------------------------------------------------------------------
# 8. CLI
# ---------------------------------------------------------------------------
def _enable_utf8_console() -> None:
    """Windows cp1252 consoles raise UnicodeEncodeError when printing Urdu."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_urdu_database",
        description="urduofdani - compile urdu_database.txt.gz "
                    "(single-space tokenized + gzip packed).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-o", "--output", default=DB_FILENAME, help="output .gz path")
    p.add_argument("-m", "--max-words", type=int, default=0,
                   help="cap the lexicon (0 = unlimited / exhaustive)")
    p.add_argument("--min-len", type=int, default=2, help="minimum token length")
    p.add_argument("--max-len", type=int, default=40, help="maximum token length")
    p.add_argument("--keep-diacritics", action="store_true",
                   help="keep harakat instead of folding them")
    p.add_argument("--exhaustive", action="store_true",
                   help="maximum-recall combinatorial expansion (over-generates)")
    p.add_argument("--verify", action="store_true", help="run integrity checks after build")
    p.add_argument("--export", metavar="TXT", default=None,
                   help="also export the plain single-line .txt")
    p.add_argument("--benchmark", type=int, nargs="?", const=5, default=None, metavar="N",
                   help="benchmark N decompression runs")
    p.add_argument("--no-build", action="store_true", help="skip compilation (use existing .gz)")
    p.add_argument("--samples", type=int, default=6, help="print N random words at the end")
    p.add_argument("--version", action="version", version="urduofdani %s" % SCRIPT_VERSION)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    _enable_utf8_console()
    args = _build_parser().parse_args(argv)
    out = Path(args.output)

    if not args.no_build:
        build_urdu_database(
            output_path=out,
            max_words=max(0, args.max_words),
            keep_diacritics=args.keep_diacritics,
            min_len=args.min_len,
            max_len=args.max_len,
            exhaustive=args.exhaustive,
        )
    elif not out.exists():
        print("[urduofdani] ERROR: %s not found - run once without --no-build." % out)
        return 2

    if args.verify:
        if not verify_database(out, export_txt=args.export):
            return 1
    elif args.export:
        with gzip.open(out, "rb") as fh:
            Path(args.export).write_bytes(fh.read())
        print("[urduofdani] exported plain text -> %s" % args.export)

    if args.benchmark is not None:
        benchmark(out, repeats=args.benchmark)

    if args.samples:
        engine = UrduEngine(out)
        print("[urduofdani] %s words indexed in %.3f ms" %
              (f"{len(engine):,}", engine.load_seconds * 1000))
        random.seed(0)
        print("[urduofdani] samples: %s" % " ".join(random.sample(engine.words(), args.samples)))
        print("[urduofdani] suggest('کم') -> %s" % " | ".join(engine.suggest("کم", 8)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
