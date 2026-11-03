"""Stage 4: chunking rules and the label in front of every chunk."""

from app.core.enums import ContentType
from app.rag.ingestion.chunking import MAX_TOKENS, MIN_TOKENS, join_lines, make_chunks
from app.rag.ingestion.labels import build_context_label, chapter_label
from app.rag.ingestion.structure import (
    DetectedChapter,
    DetectedExercise,
    DetectedTopic,
    DocumentStructure,
    Line,
    Segment,
)
from app.rag.ingestion.text_quality import estimate_tokens


def _lines(texts: list[str], page: int = 1) -> list[Line]:
    return [
        Line(index=i, page=page + i // 10, text=t, size=None, bold=False, heading_level=None)
        for i, t in enumerate(texts)
    ]


def _structure(*segments: Segment) -> DocumentStructure:
    return DocumentStructure(chapters=[DetectedChapter(1, "Fractions", "heading")], segments=list(segments))


_SENTENCE = "A fraction tells us how many equal parts of a whole we are talking about here."


def test_long_explanations_are_cut_into_overlapping_pieces_at_sentence_ends():
    lines = _lines([_SENTENCE] * 120)
    chunks = make_chunks(_structure(Segment(ContentType.CONCEPT, 0, None, None, lines)))

    assert len(chunks) > 3
    for chunk in chunks[:-1]:
        assert MIN_TOKENS <= chunk.token_count <= MAX_TOKENS
        assert chunk.content.endswith(".")
    # Neighbouring chunks share their boundary sentence.
    assert chunks[1].content.startswith(chunks[0].content.splitlines()[-1])
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 12


def test_a_small_last_piece_joins_the_one_before():
    lines = _lines([_SENTENCE] * 23)  # just over one chunk
    chunks = make_chunks(_structure(Segment(ContentType.CONCEPT, 0, None, None, lines)))
    assert len(chunks) == 1


def test_questions_and_examples_are_never_split_or_merged():
    long_example = _lines([_SENTENCE] * 60)
    question = _lines(["1. Add 1/4 and 2/4."])
    chunks = make_chunks(
        _structure(
            Segment(ContentType.EXAMPLE, 0, None, None, long_example, {"example_number": "3"}),
            Segment(ContentType.EXERCISE_QUESTION, 0, None, 0, question, {"question_number": "1"}),
            Segment(
                ContentType.EXERCISE_QUESTION,
                0,
                None,
                0,
                _lines(["2. Add 1/3 and 1/3."]),
                {"question_number": "2"},
            ),
        )
    )
    assert [chunk.content_type for chunk in chunks] == [
        ContentType.EXAMPLE,
        ContentType.EXERCISE_QUESTION,
        ContentType.EXERCISE_QUESTION,
    ]
    assert chunks[0].token_count > MAX_TOKENS  # kept whole on purpose
    assert chunks[1].meta == {"question_number": "1"}


def test_a_whole_word_paragraph_on_one_line_is_still_split():
    paragraph = " ".join([_SENTENCE] * 80)
    chunks = make_chunks(_structure(Segment(ContentType.CONCEPT, 0, None, None, _lines([paragraph]))))
    assert len(chunks) > 1
    assert all(chunk.token_count <= MAX_TOKENS for chunk in chunks)


def test_empty_segments_are_skipped_and_hyphenated_words_repaired():
    chunks = make_chunks(
        _structure(
            Segment(ContentType.OTHER, None, None, None, _lines(["•", "-"])),
            Segment(
                ContentType.CONCEPT,
                0,
                None,
                None,
                _lines(["Two numbers are equi-", "valent when they match."]),
            ),
        )
    )
    assert len(chunks) == 1
    assert chunks[0].content == "Two numbers are equivalent when they match."
    assert join_lines(_lines(["2 -", "x"])) == "2 -\nx"


def test_context_label():
    label = build_context_label(
        class_level="class_8",
        subject="Mathematics",
        chapter=DetectedChapter(2, "Linear Equations", "heading"),
        topic=DetectedTopic("2.3", "Solving Equations", None),
        exercise=DetectedExercise("2.3", None),
        content_type=ContentType.EXERCISE_QUESTION,
        meta={"question_number": "4"},
    )
    assert label.split(" · ") == [
        "Class 8",
        "Mathematics",
        "Chapter 2 Linear Equations",
        "2.3 Solving Equations",
        "Exercise 2.3",
        "Question 4",
    ]
    assert chapter_label(3, "Chapter 3") == "Chapter 3"
    assert chapter_label(None, "Notes") == "Notes"
    summary = build_context_label(
        class_level="ukg",
        subject="English",
        chapter=None,
        topic=None,
        exercise=None,
        content_type="summary",
        meta={},
    )
    assert summary == "UKG · English · Summary"


def test_token_estimate_is_used_for_chunks():
    chunks = make_chunks(_structure(Segment(ContentType.CONCEPT, 0, None, None, _lines([_SENTENCE]))))
    assert chunks[0].token_count == estimate_tokens(_SENTENCE)
