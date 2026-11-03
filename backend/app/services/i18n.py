"""Script helpers shared by Leak Guard, rule checks and display code."""

import re

_TO_LATIN = str.maketrans("०१२३४५६७८९", "0123456789")
_TO_DEVANAGARI = str.maketrans("0123456789", "०१२३४५६७८९")
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_LATIN = re.compile(r"[A-Za-z]")

NE_NUMBER_WORDS = {"एक": 1, "दुई": 2, "तीन": 3, "चार": 4, "पाँच": 5, "छ": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10}
EN_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def normalise_digits(text: str) -> str:
    """Devanagari digits -> Latin, so '९८१२३४५६७८' scans like '9812345678'."""
    return text.translate(_TO_LATIN)


def to_devanagari_digits(text: str) -> str:
    return str(text).translate(_TO_DEVANAGARI)


def detect_language(text: str) -> str:
    """'ne' when the text has at least as many Devanagari letters as Latin ones."""
    ne = len(_DEVANAGARI.findall(text))
    en = len(_LATIN.findall(text))
    return "ne" if ne and ne >= en else "en"


def has_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text))
