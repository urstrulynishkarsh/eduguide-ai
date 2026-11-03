"""Checks every generated question must pass (spec §19, docs/06 §6.4).

`problems()` is the deterministic part: format allowed for the class, options valid with exactly
one correct, answer present for the format, sentence and step limits of the class profile,
citations of passages that exist, no duplicates. `review_problem()` compares the question with the
independent review: the same answer, supported by the passages, right for the class and difficulty.
Each returns a short reason, which is fed back to the writer when a replacement is asked for.
"""

import math
import re
import unicodedata

from app.class_profiles import ClassProfile
from app.core.enums import QuestionFormat
from app.question_generation.schemas import (
    CHOICE_FORMATS,
    NUMBER_FORMATS,
    WRITTEN_FORMATS,
    GeneratedQuestion,
    Review,
)
from app.rag.ingestion.text_quality import to_ascii_digits

_SENTENCE = re.compile(r"(?<=[.?!।])\s+")
_SENTENCE_SLACK = 1.5  # the profile's words-per-sentence is "about"; allow some room
_LEVELS = {"easy": 0, "medium": 1, "hard": 2}


def normalize(text: str) -> str:
    """For comparing answers and spotting repeats: lower case, ASCII digits, no punctuation."""
    text = to_ascii_digits(unicodedata.normalize("NFC", text)).casefold()
    text = "".join(ch if ch.isalnum() or unicodedata.category(ch).startswith("M") else " " for ch in text)
    return " ".join(text.split())


def numbers_match(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=0.01, abs_tol=1e-6)


def _option_count(profile: ClassProfile, question_format: QuestionFormat) -> int:
    return {QuestionFormat.TRUE_FALSE: 2, QuestionFormat.ASSERTION_REASON: 4}.get(
        question_format, profile.mcq_option_count
    )


def problems(
    question: GeneratedQuestion,
    *,
    profile: ClassProfile,
    formats: list[QuestionFormat],
    difficulty: str,
    tags: set[str],
    seen: set[str],
) -> str | None:
    """The first reason this question cannot be used, or None."""
    fmt = question.format
    if fmt not in formats:
        return f"format {fmt} was not asked for"
    if question.style not in profile.question_styles:
        return f"style {question.style} is not used for this class"
    if difficulty != "mixed" and question.difficulty != difficulty:
        return f"difficulty should be {difficulty}"
    if not question.text.strip() or normalize(question.text) in seen:
        return "the question is empty or repeats another question"
    if not question.source_tags or not set(question.source_tags) <= tags:
        return "source_tags must name passages that were given"

    if fmt in CHOICE_FORMATS:
        options = [normalize(option) for option in question.options]
        if len(options) != _option_count(profile, fmt) or len(set(options)) != len(options) or "" in options:
            return f"needs exactly {_option_count(profile, fmt)} different, non-empty options"
        if question.correct_option is None or not 0 <= question.correct_option < len(options):
            return "correct_option must point at one of the options"
        if fmt is QuestionFormat.VISUAL_CHOICE and not all(
            any(unicodedata.category(ch) == "So" for ch in option) for option in question.options
        ):
            return "every visual_choice option needs an emoji"
        if fmt is QuestionFormat.CASE_BASED and not (question.case or "").strip():
            return "case_based needs the case"
    elif fmt in NUMBER_FORMATS:
        if question.numeric_answer is None or not math.isfinite(question.numeric_answer):
            return "numeric_answer is missing"
    elif fmt is QuestionFormat.FILL_BLANK:
        if "___" not in question.text or not [a for a in question.accepted_answers if a.strip()]:
            return "fill_blank needs ____ in the text and accepted_answers"
    elif fmt is QuestionFormat.MATCHING:
        left, right = question.match_left, question.match_right
        if (
            not 2 <= len(left) <= 5
            or len(left) != len(right)
            or len({normalize(r) for r in right}) != len(right)
        ):
            return "matching needs 2 to 5 pairs with different right-hand items"
    elif fmt in WRITTEN_FORMATS and not ((question.model_answer or "").strip() and question.key_points):
        return "written questions need model_answer and key_points"

    longest = max((len(sentence.split()) for sentence in _SENTENCE.split(question.text)), default=0)
    if longest > profile.max_sentence_words * _SENTENCE_SLACK:
        return f"sentences must stay near {profile.max_sentence_words} words"
    if not question.steps or len(question.steps) > profile.max_solution_steps:
        return f"the solution needs 1 to {profile.max_solution_steps} steps"
    if not 1 <= len(question.hints) <= 2 or not question.final_answer.strip():
        return "needs one or two hints and a final_answer"
    return None


def review_problem(question: GeneratedQuestion, review: Review, *, difficulty: str) -> str | None:
    """The reason the independent review rejects this question, or None."""
    fmt = question.format
    if fmt in CHOICE_FORMATS and review.solved_option != question.correct_option:
        return "a second solver chose a different option"
    if fmt in NUMBER_FORMATS and (
        review.solved_value is None or not numbers_match(review.solved_value, question.numeric_answer or 0.0)
    ):
        return "a second solver got a different number"
    if fmt is QuestionFormat.FILL_BLANK and normalize(review.solved_text or "") not in {
        normalize(answer) for answer in question.accepted_answers
    }:
        return "a second solver filled the blank differently"
    if (fmt is QuestionFormat.MATCHING or fmt in WRITTEN_FORMATS) and review.shown_answer_correct is not True:
        return "the answer was judged wrong"
    if not review.supported_by_passages:
        return "not everything needed is in the passages"
    if not review.fits_class:
        return review.problem or "not right for this class"
    if difficulty != "mixed" and abs(_LEVELS[review.difficulty] - _LEVELS[question.difficulty]) > 1:
        return f"judged {review.difficulty}, not {question.difficulty}"
    return None
