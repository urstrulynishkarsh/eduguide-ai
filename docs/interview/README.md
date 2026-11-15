# EduGuide AI: interview notes

Notes for explaining this project in a technical interview: what it does, why each technology was
chosen, what else could have been used, and what to say when asked.

## How to use these notes

1. Learn the **30-second pitch** and the **2-minute walk-through** below until you can say them
   without reading.
2. For every technology, be ready with three things: **why it is here**, **what else you could have
   used and why you didn't**, and **what you would change**.
3. Back every claim with a number or a file in the repo. "Recall@5 of 1.00 on 18 questions" beats
   "search works well".
4. Answer every "why X?" question with the same shape:
   **the need → the choice → the alternative I rejected and why → the trade-off I accepted.**

## The files

| File | What it covers |
|---|---|
| [01-project-and-architecture.md](01-project-and-architecture.md) | The problem, the users, the architecture, the key decisions, the hard problems solved |
| [02-backend-python-fastapi.md](02-backend-python-fastapi.md) | Python, FastAPI, Uvicorn, Pydantic, and the backend's patterns |
| [03-database-postgres-pgvector.md](03-database-postgres-pgvector.md) | PostgreSQL, pgvector, full-text search, SQLAlchemy, asyncpg, Alembic |
| [04-rag-books-and-search.md](04-rag-books-and-search.md) | Reading books (PDF, Word, OCR), chunking, embeddings, hybrid search |
| [05-ai-llm-layer.md](05-ai-llm-layer.md) | The LLM interface, Claude and Groq, checking questions, the hint ladder, streaming |
| [06-frontend-nextjs.md](06-frontend-nextjs.md) | Next.js 16, React 19, TypeScript, Tailwind 4, shadcn/ui, sessions, languages |
| [07-auth-and-security.md](07-auth-and-security.md) | JWT, sessions, Argon2, child mode, the parent PIN, rate limits, headers, privacy |
| [08-jobs-infra-devops.md](08-jobs-infra-devops.md) | Background jobs (SAQ, Redis), Docker, Caddy, Prometheus, CI |
| [09-testing-and-quality.md](09-testing-and-quality.md) | pytest, Vitest, Playwright, axe, ruff, ESLint, audits, measuring search |
| [10-interview-questions.md](10-interview-questions.md) | Likely questions with short answers, system design, weaknesses, stories |

## The 30-second pitch

> EduGuide AI turns a child's own school textbooks into a personal tutor. A parent uploads the
> books; the app reads them into chapters, exercises and questions, then writes practice questions
> from them, checks every question with a second, independent AI solve, and adapts the difficulty
> to how the child is doing. It covers Nursery to Class 12 plus JEE and NEET, in English, Hindi
> and Hinglish, and the screens change with the child's age. I built it as a FastAPI and
> PostgreSQL backend with pgvector search and a Next.js 16 frontend, with Docker, CI and over
> 600 automated tests.

## The 2-minute walk-through

1. **Problem.** Indian families buy textbooks, but practice material rarely matches *their* book,
   *their* board and *their* child's level. Children under 10 have no email, and the family
   usually shares one phone.
2. **Users.** A parent signs up and adds children. A child has no login: the parent hands over the
   device in **child mode**, a session limited to that one child that only a 4-digit parent PIN
   can end. Older students can also sign up on their own.
3. **Reading books.** An uploaded PDF, Word or text file is checked, read page by page (with OCR
   for scanned pages), split into chapters, topics, examples and exercise questions, cut into
   labelled chunks and embedded with a local multilingual model. All of this runs as a background
   job with a progress checklist.
4. **Search.** Hybrid search: vector search (pgvector) and keyword search (PostgreSQL full text),
   merged with reciprocal rank fusion. Every search is filtered to the family's own books inside
   the same SQL query. If nothing relevant is found, the app says so instead of guessing.
5. **AI.** One small `LLMProvider` interface with two adapters: Claude and Groq. Every answer is
   parsed into a Pydantic model. Questions are written in batches, checked by code, then solved
   again by a separate reviewer call that never sees the proposed answer. Questions that fail are
   replaced or dropped.
6. **Learning loop.** Mastery per topic after every answer, difficulty that moves up above 85 %
   and down below 60 %, daily recommendations, mock tests with part marks, a study plan made again
   each morning, an AI tutor that gives hints before answers, and a parent assistant.
7. **Production.** Redis-backed background workers, rate limits, revocable sessions, security
   headers, Docker images behind Caddy (HTTPS), Prometheus metrics, and CI on GitHub Actions.

## Numbers to remember

| What | Number |
|---|---|
| Classes covered | 15 (Nursery, LKG, UKG, Class 1–12), in 5 bands, with 4 screen layouts |
| Screen languages | 3 (English, Hindi, Hinglish); 8 more Indian languages registered for later |
| Backend code | about 15,000 lines of Python in `backend/app` |
| Frontend code | about 11,000 lines of TypeScript |
| API | 64 routes, 29 tables, 11 migrations |
| Screens | 41 pages |
| Tests | 431 backend (6 of them opt-in live AI tests), 153 frontend unit, 40 browser (Playwright) |
| Search quality | recall@5 = 1.00, MRR = 0.96 on 18 questions in English, Hindi and Hinglish |
| Search model | multilingual-e5-base: 768 dimensions, about 1 GB, runs on the server, no API key |
| Tokens | access 30 minutes, refresh 14 days, each tied to a session that sign-out revokes |
| AI limits per family | 20 requests a minute, 300 a day |
| Question writing | 10 questions per call on Claude, 3 on Groq's free plan; at most 2 rounds of replacements |

## The five points that make this project stand out

1. **AI output is treated as data, not text.** Every model answer fills a Pydantic schema, passes
   checks written in code, and for questions gets an independent second solve. The app would
   rather give fewer questions than a wrong one.
2. **Data isolation is enforced by design, not by habit.** The search filter object cannot be
   created without the family's id, every route is tested without a token, and another family's
   id answers 404, not 403.
3. **One database does three jobs.** PostgreSQL holds the relational data, the vectors (pgvector)
   and the keyword index (`tsvector` + GIN), so filters, ranking and isolation happen in one SQL
   statement and one transaction.
4. **Built for India.** Hindi and Hinglish search, OCR for old non-Unicode Hindi fonts, NCERT's
   one-PDF-per-chapter books, shared family phones, and India's data protection law (DPDP Act).
5. **Production habits from the start.** Swappable providers behind interfaces, resumable
   background jobs, rate limits, revocable sessions, a security review, pinned versions, CI with
   audits, and accessibility checks in the browser tests.
