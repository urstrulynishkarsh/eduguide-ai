"""Languages the platform knows about.

Two different things are tracked for each language:

* `content_enabled` - the AI may talk to the learner in this language today
  (questions, explanations, hints, study plans, and the UI).
* `medium_allowed`  - it can be picked as the child's medium of instruction at
  school. A child can study in a Marathi-medium school even before the AI can
  write Marathi content.

To switch on a new content language later, flip `content_enabled` to True
(and add its UI translations in the frontend). No schema change is needed.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Language:
    code: str
    label: str  # English name
    native_label: str  # name written in the language itself
    content_enabled: bool
    medium_allowed: bool


_ALL: tuple[Language, ...] = (
    Language("en", "English", "English", content_enabled=True, medium_allowed=True),
    Language("hi", "Hindi", "हिन्दी", content_enabled=True, medium_allowed=True),
    # Hindi written in Roman letters and mixed with English. Spoken, not a school medium.
    Language("hinglish", "Hinglish", "Hinglish", content_enabled=True, medium_allowed=False),
    Language("mr", "Marathi", "मराठी", content_enabled=False, medium_allowed=True),
    Language("gu", "Gujarati", "ગુજરાતી", content_enabled=False, medium_allowed=True),
    Language("bn", "Bengali", "বাংলা", content_enabled=False, medium_allowed=True),
    Language("ta", "Tamil", "தமிழ்", content_enabled=False, medium_allowed=True),
    Language("te", "Telugu", "తెలుగు", content_enabled=False, medium_allowed=True),
    Language("kn", "Kannada", "ಕನ್ನಡ", content_enabled=False, medium_allowed=True),
    Language("ml", "Malayalam", "മലയാളം", content_enabled=False, medium_allowed=True),
    Language("pa", "Punjabi", "ਪੰਜਾਬੀ", content_enabled=False, medium_allowed=True),
)

LANGUAGES: dict[str, Language] = {language.code: language for language in _ALL}

DEFAULT_LANGUAGE = "en"

# A catch-all so parents whose school medium is not listed are never blocked.
OTHER_MEDIUM = Language("other", "Other", "Other", content_enabled=False, medium_allowed=True)


def content_languages() -> list[Language]:
    """Languages the AI and the UI can use right now."""
    return [language for language in _ALL if language.content_enabled]


def medium_options() -> list[Language]:
    """Choices for "medium of instruction" on the child profile."""
    return [language for language in _ALL if language.medium_allowed] + [OTHER_MEDIUM]


def is_content_language(code: str) -> bool:
    language = LANGUAGES.get(code)
    return language is not None and language.content_enabled


def is_medium(code: str) -> bool:
    return any(option.code == code for option in medium_options())
