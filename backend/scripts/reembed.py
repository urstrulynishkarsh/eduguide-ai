"""Make every chunk searchable with the current search model.

    python -m scripts.reembed

Needed once after upgrading from Step 2 (books read before search existed), and after changing
the search model. Safe to run any time: only chunks without an up-to-date vector are embedded.
"""

import asyncio

from app.core.database import SessionLocal, engine
from app.rag.indexing import embed_stale_chunks


async def main() -> None:
    try:
        async with SessionLocal() as db:
            count = await embed_stale_chunks(db)
    finally:
        await engine.dispose()
    print(f"Embedded {count} chunk(s).")


if __name__ == "__main__":
    asyncio.run(main())
