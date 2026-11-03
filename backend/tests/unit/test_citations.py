"""Chat replies mark the book passages they use; the marks become a sources list under the reply."""

from app.services.chat_service import citations


def test_citations_are_taken_out_whole_and_their_tags_collected():
    reply = "Subtract 4 from both sides (see [S1]). Then divide [S2, S3]. Done [S1][S4]. A (short [S2]) note."

    content, used = citations(reply)

    assert content == "Subtract 4 from both sides. Then divide. Done. A (short) note."
    assert used == {"S1", "S2", "S3", "S4"}
    assert citations("No books needed here.") == ("No books needed here.", set())
