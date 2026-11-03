"""The tutor's hint ladder: code decides how much help each reply may give, one rung at a time."""

from app.chat import tutor
from app.chat.tutor import State, Understanding
from app.models import DocumentChunk
from app.rag.retrieval import Passage, build_context


def _said(intent: str, hints_only: bool = False) -> Understanding:
    return Understanding(intent=intent, hints_only=hints_only, search_query="")


def _walk(*intents: str, state: State | None = None) -> list[str | None]:
    """The rung of each reply, for a conversation of these intents."""
    state = state or State()
    rungs = []
    for intent in intents:
        step = tutor.next_step(state, _said(intent), "Solve 2x + 4 = 10")
        rungs.append(step.rung)
        state = step.state
    return rungs


def test_a_new_problem_starts_with_a_nudge_and_each_request_climbs_one_rung():
    assert _walk("new_problem", "more_help", "more_help", "more_help", "more_help", "more_help") == [
        "hint_1",
        "hint_2",
        "concept",
        "steps",
        "answer",
        "answer",  # the top stays the top
    ]


def test_asking_for_the_answer_never_skips_a_rung():
    assert _walk("new_problem", "show_answer", "show_answer") == ["hint_1", "hint_2", "concept"]


def test_hints_only_stops_at_the_second_hint():
    state = tutor.next_step(State(), _said("new_problem", hints_only=True), "Solve 2x + 4 = 10").state
    assert _walk("more_help", "show_answer", "more_help", state=state) == ["hint_2", "hint_2", "hint_2"]
    # Asked later, it holds from then on, even after the concept was explained.
    later = State("Solve 2x + 4 = 10", rung=2, hints_only=False)
    step = tutor.next_step(later, _said("more_help", hints_only=True), "only hints please")
    assert (step.rung, step.state.hints_only) == ("hint_2", True)


def test_an_attempt_is_checked_and_answered_with_the_next_rung():
    step = tutor.next_step(State("Solve 2x + 4 = 10", rung=0), _said("attempt"), "x = 7?")
    assert (step.reply, step.rung, step.state.rung) == ("check", "hint_2", 1)


def test_help_without_a_problem_asks_which_one_and_other_messages_keep_the_problem():
    assert tutor.next_step(State(), _said("more_help"), "help").reply == "chat"
    in_hand = State("Solve 2x + 4 = 10", rung=1)
    for intent, reply in (("concept", "explain"), ("chat", "chat"), ("off_topic", "off_topic")):
        step = tutor.next_step(in_hand, _said(intent), "…")
        assert (step.reply, step.rung, step.state) == (reply, None, in_hand)


def test_the_reply_task_says_what_this_rung_may_show():
    chunk = DocumentChunk(
        content="Example 2: Solve 2x + 4 = 10.",
        context_label="Class 7 · Chapter 4",
        page_start=61,
        token_count=12,
    )
    passages = build_context([Passage(chunk, 0.9)])
    hint = tutor.next_step(State(), _said("new_problem"), "Solve 2x + 4 = 10")

    text = tutor.task(hint, "Solve 2x + 4 = 10", passages, "hinglish")

    assert text.startswith("This reply is Hint 1") and "Not allowed: any working" in text
    assert "Write in Hinglish" in text
    assert "<problem>Solve 2x + 4 = 10</problem>" in text and '<passage tag="S1"' in text
    assert text.endswith("<message>Solve 2x + 4 = 10</message>")
    checked = tutor.next_step(hint.state, _said("attempt"), "x = 7")
    assert tutor.task(checked, "x = 7", passages, "en").startswith("The student has tried an answer")
    hints_only = tutor.next_step(State(), _said("new_problem", hints_only=True), "Solve it, hints only")
    assert "hints only" in tutor.task(hints_only, "Solve it, hints only", passages, "en")
