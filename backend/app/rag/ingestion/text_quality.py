"""Small text helpers: cleaning lines, recognising scripts, spotting pages that need OCR."""

import re
import unicodedata

# Characters that only cause trouble: soft hyphen, byte-order mark, object replacement.
# Zero-width joiner / non-joiner are kept - they change how Devanagari is written.
_DROP_CHARS = dict.fromkeys(map(ord, "­﻿￼"), None)
_SPACES = re.compile(r"[ \t  -   　]+")

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize_line(text: str) -> str:
    """NFC form, one space between words, no stray control characters."""
    text = unicodedata.normalize("NFC", text).translate(_DROP_CHARS)
    text = "".join(ch for ch in text if ch in "\t" or unicodedata.category(ch)[0] != "C" or ch in "‌‍")
    return _SPACES.sub(" ", text).strip()


def to_ascii_digits(text: str) -> str:
    """'२.३' -> '2.3'. Hindi books often number exercises with Devanagari digits."""
    return text.translate(_DEVANAGARI_DIGITS)


def letter_count(text: str) -> int:
    return sum(1 for ch in text if ch.isalpha())


def detect_language(text: str, default: str) -> str:
    """'hi' for mostly-Devanagari text, 'en' for mostly-Latin text, otherwise `default`.

    Good enough to tag a chunk; real language identification is not needed for that.
    """
    devanagari = len(_DEVANAGARI.findall(text))
    latin = len(_LATIN.findall(text))
    if devanagari + latin < 3:
        return default
    return "hi" if devanagari >= latin else "en"


# Old Hindi fonts (Kruti Dev and friends) store Devanagari as Latin letters and punctuation,
# so text comes out as e.g. "Hkkjr ,d d`f"k iz/kku ns'k gS". Those words are full of symbols in the
# middle of words and of "kk" (the vowel sign ा), which real English almost never has.
_LEGACY_SYMBOLS = re.compile(r"[A-Za-z][;`~|^{}\\/,'\"][A-Za-z]")
_LEGACY_KK = re.compile(r"kk")


def looks_like_legacy_font(text: str) -> bool:
    words = [word for word in text.split() if len(word) >= 3 and _LATIN.search(word)]
    if len(words) < 12:
        return False
    suspicious = sum(1 for word in words if _LEGACY_SYMBOLS.search(word) or _LEGACY_KK.search(word))
    return suspicious / len(words) > 0.25


MIN_LETTERS_PER_PAGE = 25


def page_needs_ocr(text: str) -> bool:
    """True when the page has (almost) no usable text: a scan, a photo, or a legacy-font page."""
    return letter_count(text) < MIN_LETTERS_PER_PAGE or looks_like_legacy_font(text)


def estimate_tokens(text: str) -> int:
    """Rough token count without loading a tokenizer.

    English is about 4 characters (or 1.3 words) per token. Devanagari splits into many more pieces
    with most tokenizers, about 2 characters per token. The larger estimate wins.
    """
    devanagari = len(_DEVANAGARI.findall(text))
    by_characters = (len(text) - devanagari) / 4 + devanagari / 2
    return max(1, round(max(len(text.split()) * 1.3, by_characters)))
