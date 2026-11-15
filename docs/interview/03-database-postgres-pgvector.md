# 3. Database: PostgreSQL, pgvector, SQLAlchemy, asyncpg, Alembic

---

## 3.1 PostgreSQL 16

**What:** the relational database. Runs in Docker as `pgvector/pgvector:pg16`.

**Why here**
- **The data is relational.** Account → parent → children → profiles; book → documents → chapters
  → topics → exercises → questions → attempts. Joins, foreign keys and transactions are the natural
  fit. There are 29 tables.
- **One database does three jobs:** relational data, **vectors** (pgvector) and **keyword search**
  (`tsvector`). Filters, ranking and family isolation happen in one SQL statement.
- **Transactions.** A book's chapters, exercises and chunks are written in one transaction: a
  failed read leaves nothing half-saved.
- **Mature and free**, with managed versions on every cloud (AWS RDS, Google Cloud SQL, Azure,
  Neon, Supabase).

| Alternative | Good at | Why not here |
|---|---|---|
| MySQL | Popular, fast reads | No pgvector equivalent in community MySQL; weaker full-text search, especially for Hindi |
| MongoDB | Flexible documents | The data is deeply relational; isolation needs joins; multi-document transactions are clumsier |
| SQLite | Zero setup | One writer at a time; no pgvector (sqlite-vec exists but is young); not for a multi-process server |
| Supabase / Neon | Managed PostgreSQL | Still PostgreSQL underneath, so it is a hosting choice, not a different design. Local Docker keeps development free and offline |

**Say it:** "PostgreSQL because the data is relational and I wanted vectors and keyword search in
the same database. A search filters by family, class and chapter and ranks by meaning in one query,
inside one transaction, with no second system to keep in sync."

---

## 3.2 pgvector (vector search inside PostgreSQL)

**What:** a PostgreSQL extension that adds a `vector` column type and distance operators (cosine,
L2, inner product), plus approximate indexes (HNSW, IVFFlat).

**How it is used**
- `document_chunks.embedding` is `vector(768)` (multilingual-e5-base), and each row records the
  model that made it (`embedding_model`).
- Search: `ORDER BY embedding <=> query_vector` (cosine distance) **inside the filtered set**.
- **No approximate index on purpose.** Filters are tight (one family, usually one book or chapter),
  so the candidate set is small. An exact scan is fast and has perfect recall. An approximate
  index (HNSW) only pays off for wide searches across many books, and filtered approximate search
  can return too few results.

**Why not a separate vector database**

| Alternative | Good at | Why not here |
|---|---|---|
| Pinecone | Managed, scales to billions of vectors | Paid; children's book text goes to another company; a second copy of ownership data to keep in sync |
| Qdrant / Weaviate / Milvus | Fast approximate search, rich filters | Another service to run, back up and secure; two writes per chunk with no shared transaction |
| Chroma / FAISS | Easy local prototyping | FAISS is a library, not a database (no filters or persistence of its own); Chroma isn't built for multi-tenant production |
| Elasticsearch / OpenSearch | Keyword + vector in one engine | Heavy (JVM, memory); still a second store next to PostgreSQL |

**Say it:** "At this scale a separate vector database adds cost and a sync problem without adding
quality. pgvector lets the family filter and the similarity ranking run in the same SQL statement.
If one day searches span millions of chunks, I'd add an HNSW index first, and only then think about
moving vectors out."

**Follow-ups**
- *"When would you add HNSW?"* When searches cover many books and the exact scan gets slow
  (measure p95 latency). pgvector 0.8 has iterative index scans, which help filtered queries.
- *"Cosine or dot product?"* The e5 vectors are normalised, so they rank the same. Cosine is used.
- *"What if you change the embedding model?"* New vector size and meaning: a migration for the
  column, then `python -m scripts.reembed`. Each vector records its model, so stale ones are found.

---

## 3.3 Full-text search in PostgreSQL (`tsvector` + GIN)

**What:** PostgreSQL's built-in keyword search.

**How it is used**
- `search_text` is a **generated, stored column**:
  `to_tsvector('simple', context_label || ' ' || content)`. The database keeps it up to date.
- A **GIN index** on it makes `@@` (matches) queries fast.
- The `'simple'` configuration means **no stemming**. An English stemmer would mangle Hindi words;
  `'simple'` matches Hindi and English words as written.
- The query is turned into `word1 | word2 | …` (any word may match) and ranked with `ts_rank`.

**Why keyword search at all, if you have vectors?** Vectors are weak at exact things: "Exercise
2.3", a formula name, a rare term. Keywords catch them. The two are merged with reciprocal rank
fusion (see [04 §4.8](04-rag-books-and-search.md)).

| Alternative | Why not here |
|---|---|
| Elasticsearch / OpenSearch | Better analyzers and BM25, but a whole second system |
| Meilisearch / Typesense | Great typo tolerance; still a second store to sync |
| `pg_trgm` (trigram) | Good for fuzzy matching of names; less suited to ranking passages |
| ParadeDB / pg_search (BM25 in PostgreSQL) | Real BM25 inside PostgreSQL; a newer extension, worth trying if ranking needs improving |

---

## 3.4 SQLAlchemy 2.1 (async ORM)

**What:** the Python ORM and SQL toolkit. Version 2.x has typed models (`Mapped[...]`) and full
asyncio support.

**Why here**
- **Typed models** (`Mapped[uuid.UUID]`, `Mapped[str | None]`) that type checkers understand.
- **Expressive enough for this project's queries:** pgvector's `cosine_distance`, `tsvector`
  `@@` with `ts_rank`, row-value comparisons `tuple_(created_at, id) < (…)` for cursor pages, and
  generated columns (`Computed(...)`).
- **Async sessions** with asyncpg.
- **Alembic** (same authors) for migrations.
- **SQL injection is handled by design:** every query is built by the ORM with bound parameters.
  The only raw SQL is a `SELECT 1` health check and one parameterised `to_tsvector` call.

**Details worth mentioning**
- `eager_defaults=True`: database-generated values are read back in the same statement, because a
  lazy second query is not allowed in async sessions.
- `expire_on_commit=False`: objects stay usable after commit without a reload.
- `pool_pre_ping=True`: dead connections are found before use (after a database restart).
- `hide_parameters=True` in production: a failed query's error doesn't print its values (which can
  be a child's answer or name) into the logs.
- A **naming convention** for indexes and constraints, so migrations are predictable.

| Alternative | Why not here |
|---|---|
| Django ORM | Tied to Django; async support is partial |
| SQLModel | A thin layer over SQLAlchemy + Pydantic; lags behind SQLAlchemy 2.x features |
| Tortoise ORM | Async-first, but smaller ecosystem and weaker migrations |
| Raw asyncpg / SQL files | Full control, but lots of boilerplate and no model layer |
| Prisma (Python client) | Good in Node; the Python client is community-maintained |

---

## 3.5 asyncpg

**What:** a fast PostgreSQL driver for asyncio, written in Cython. It uses PostgreSQL's binary
protocol.

**Why here:** the fastest async PostgreSQL driver for Python, and SQLAlchemy's standard async
driver (`postgresql+asyncpg://`).

| Alternative | Why not here |
|---|---|
| psycopg 3 (async mode) | A good choice too, also async. asyncpg is faster and the common pairing with SQLAlchemy async |
| psycopg2 | Sync only: would block the event loop |

**Story:** a `ConnectionRefusedError` from asyncpg on start-up just means PostgreSQL isn't
running (Docker was stopped). `/health/ready` checks the database, so the container's health check
catches it in production.

---

## 3.6 Alembic (migrations)

**What:** schema migrations for SQLAlchemy.

**How it is used**
- **One migration per roadmap step** (`0001`–`0011`), numbered by hand (`--rev-id 0012`). The
  database only ever contains tables that working code uses.
- Autogenerate, then **review the file by hand** (autogenerate misses things like extensions,
  generated columns or data changes).
- **The tests build the test database from the migrations on every run**, so a broken migration
  fails the tests.
- In production a one-shot `migrate` container runs `alembic upgrade head` before the API starts.

| Alternative | Why not here |
|---|---|
| `Base.metadata.create_all()` | No history, no way to change an existing database |
| Flyway / Liquibase | Language-neutral SQL migrations; lose the link to SQLAlchemy models |
| Django migrations | Tied to Django |

**Follow-up: "How do you run migrations with no downtime?"** Expand → migrate → contract: add the
new column (nullable), deploy code that writes both, backfill, switch reads, then drop the old
column in a later migration. Never rename or drop in the same deploy as the code change.

---

## 3.7 Schema decisions worth explaining

| Decision | Why |
|---|---|
| **UUID primary keys** | Ids can't be guessed or counted ("there are 5,000 users"); safe to create in the app before insert |
| **`owner_user_id` on every derived row** (documents, chunks, questions, attempts…) | One column rule for isolation; the search filter can't be built without it |
| Class, board, subject, language **copied onto each chunk** | Search filters on them in the same query as the ranking, without joins |
| **Timestamps from the application clock** | `now()` is frozen inside a transaction; two rows saved together would get the same time and could not be ordered |
| **Generated column** for the keyword index | The database keeps it correct; the code can't forget to update it |
| Indexes such as `(owner_user_id, book_id)`, `(document_id, position)`, `(student_id, created_at)` | Match the real queries: a family's books, a document in order, a learner's recent attempts |
| **Cursor pagination** on `(created_at, id)` | Stable pages while new rows arrive; no slow `OFFSET` |
| The solution is stored on the question | One language per question; "explain in Hindi" is generated on request, so a separate table would only duplicate it |
| Questions saved per family and reused | Never repeat a question to the same learner; siblings reuse checked questions; fewer AI calls |

**Follow-up: "How would you scale the database?"**
1. Measure first (slow query log, `EXPLAIN ANALYZE`).
2. Connection pooling (PgBouncer) when there are many API processes.
3. Read replicas for dashboards and progress pages.
4. An HNSW index for wide vector searches.
5. Partition big append-only tables (`question_attempts`) by time.
6. Only then think about sharding by family. Every row already has the family's id, which makes it
   a natural shard key.
