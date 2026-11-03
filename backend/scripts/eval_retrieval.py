"""Measure search quality on the sample book with the real search model (docs/05-rag-pipeline.md §5.6).

    python -m scripts.seed            # once: puts the sample book in the demo parent's library
    python -m scripts.eval_retrieval

Prints recall@5 (is the right passage in the top 5?), MRR, and the best similarity of questions
the book does not cover - the threshold (`min_similarity` of the search model) must separate them.
The search runs as in the app, but on the raw question (without the AI rewriting step).
"""

import asyncio
import json
import statistics
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.models import Book, User
from app.rag import embeddings, retrieval
from scripts.seed import PARENT_EMAIL, SAMPLE_BOOK_TITLE

EVAL_FILE = Path(__file__).parent / "sample_data" / "retrieval-eval.json"


async def main() -> None:
    cases = json.loads(EVAL_FILE.read_text())
    embedder = embeddings.get_embedding_provider()
    try:
        async with SessionLocal() as db:
            owner = await db.scalar(select(User.id).where(User.email == PARENT_EMAIL))
            book_id = await db.scalar(
                select(Book.id).where(Book.owner_user_id == owner, Book.title == SAMPLE_BOOK_TITLE)
            )
            if book_id is None:
                raise SystemExit("Run `python -m scripts.seed` first.")
            where = retrieval.ChunkFilter(owner, book_ids=[book_id])

            async def run(question: str) -> list[retrieval.Passage]:
                vector = await embedder.embed_query(question)
                return await retrieval.search(db, query_vector=vector, query_text=question, where=where)

            hits, reciprocal, relevant_best = 0, [], []
            for case in cases["questions"]:
                found = await run(case["question"])
                labels = [p.chunk.context_label for p in found]
                rank = next((i for i, label in enumerate(labels) if case["expect"] in label), None)
                hits += rank is not None and rank < 5
                reciprocal.append(1 / (rank + 1) if rank is not None else 0.0)
                relevant_best.append(max(p.similarity for p in found))
                mark = f"#{rank + 1}" if rank is not None else "MISS"
                print(f"{mark:>5}  {case['question']}")
            off_topic_best = [
                max((p.similarity for p in await run(q)), default=0.0) for q in cases["off_topic"]
            ]
    finally:
        await engine.dispose()

    total = len(cases["questions"])
    print(f"\nrecall@5 {hits / total:.2f}   MRR {statistics.mean(reciprocal):.2f}   ({total} questions)")
    print(f"best similarity, covered questions: lowest {min(relevant_best):.3f}")
    print(f"best similarity, off-topic:         highest {max(off_topic_best):.3f}")
    print(f"current threshold ({embedder.model_name}): {embedder.min_similarity}")


if __name__ == "__main__":
    asyncio.run(main())
