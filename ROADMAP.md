# EduGuide AI — Build Roadmap

The project is built in 12 steps. Every step ends with something that **runs and is tested**,
and each step fills specific folders, so you always know where the new code is.

Status: ✅ done · ⏭ next · ⬜ later

## Phase 1 — Core MVP

| Step | Status | What you get | Folders it fills | Spec items (§46) |
|---|---|---|---|---|
| **1** | ✅ | **Blueprint + backend foundation.** Design documents, database, sign-up / sign-in, parent and student roles, class selection, child profiles, class-aware rules, child mode. | `docs/` · `backend/app/core` · `models` · `schemas` · `auth` · `class_profiles` · `services` · `api` · `backend/alembic` · `backend/tests` · tables: `users`, `parents`, `students`, `student_profiles` | 1 Authentication · 2 Roles · 3 Class selection · 4 Student profile |
| **2** | ✅ | **Upload and read books.** Upload PDF / DOCX / TXT safely, read the text (OCR for scanned pages when Tesseract is installed), find chapters, topics, exercises and each exercise question, cut the book into labelled pieces, library API. | `backend/app/rag/ingestion` · `backend/app/storage` · `backend/app/services` · `backend/app/api/v1` · tables: `books`, `documents`, `chapters`, `topics`, `exercises`, `document_chunks` | 5 Upload · 6 Parsing · 7 Chapter detection · 8 Chunking |
| **3** | ✅ | **Search inside books + AI connection.** A local multilingual embedding model, vectors stored in PostgreSQL (pgvector), meaning search plus keyword search merged by rank, filters (family, book, class, chapter, exercise), context with source citations, "Explain this", and the swappable AI layer (Claude). | `backend/app/llm` · `backend/app/rag` · new columns on `document_chunks` | 9 Embeddings · 10 Vector database · 11 RAG retrieval |
| **4** | ✅ | **Practice engine.** Class-aware question generation, automatic checking with an independent second solve and regeneration, a reusable question bank, hints → steps → answer, practice sessions, recording attempts, basic performance numbers. | `backend/app/question_generation` · `backend/app/analytics` · `backend/app/services` · `backend/app/api/v1` · tables: `questions`, `practice_sessions`, `practice_items`, `question_attempts` | 12 Question generation · 13 Solutions · 15 Basic performance tracking |
| **5** | ⏭ | **Frontend foundation.** Next.js app, design system with the four age-based layouts, landing page, sign-up / sign-in, onboarding, child mode. | `frontend/` | screens for items 1–4 |
| **6** | ⬜ | **Frontend MVP.** My Books and upload with progress, Create Practice, the student practice screen (including the picture-based one for Nursery–Class 2), basic progress. **The MVP works end to end here.** | `frontend/` | 14 Student practice interface |

## Phase 2

| Step | Status | What you get | Folders it fills | Spec items (§46) |
|---|---|---|---|---|
| **7** | ⬜ | **Adaptive learning.** Mastery per topic, difficulty that follows performance, weak-topic detection, daily recommendations. | `backend/app/adaptive_learning` · `backend/app/analytics` | 1 Adaptive difficulty · 3 Weak-topic detection · 4 Study recommendations |
| **8** | ⬜ | **Mock tests and study planner** (backend). Sectioned, timed tests with a result report; study plans that update with performance. | `backend/app/services` · `backend/app/api/v1` | 5 Mock tests · 6 Study planner |
| **9** | ⬜ | **Parent dashboard, test and plan screens, the two assistants.** Parent AI Assistant and Student AI Tutor (hint first, answer last). | `frontend/` · `backend/app/api/v1` | 2 Parent dashboard |

## Phase 3

| Step | Status | What you get | Folders it fills | Spec items (§46) |
|---|---|---|---|---|
| **10** | ⬜ | **Previous-year paper analysis, misconception detection, JEE / NEET / CUET modes.** | `backend/app/analytics` · `backend/app/adaptive_learning` · `backend/app/question_generation` | 1 Previous-year analysis · 2 Misconception detection · 3 Competitive exam modes |
| **11** | ⬜ | **Languages, gamification, advanced analytics.** Hindi / Hinglish screens, structure for more Indian languages, streaks / XP / badges, richer charts. | `frontend/` · `backend/app/analytics` | 4 Multi-language support · 5 Gamification · 6 Advanced analytics |
| **12** | ⬜ | **Production hardening.** Rate limiting, background workers on Redis, Docker images, CI, monitoring, a security review. | `infra/` · whole project | — |

Note: content in **Hindi and Hinglish** already works. Explanations have it from Step 3 and
practice questions from Step 4, because the language is part of every request to the AI.
Step 11 adds translated screens and further languages.

## How every step is delivered

1. Claude shows a plan for the step and waits for your approval (see `CLAUDE.md`).
2. The code is written directly in this project folder. Before a step is called done, the tests
   (`pytest`) and the code checks (`ruff check .` and `ruff format --check .`) must pass.
3. This file is updated: the step is marked ✅ and "Notes for next step" below is rewritten.
4. You bring your setup up to date with the commands listed under that step below, then **commit
   yourself** (`git add -A && git commit -m "Step N: …"`). Claude never commits.

## What Step 1 created

```
eduguide-ai/
├── README.md                  setup instructions
├── ROADMAP.md                 this file
├── docker-compose.yml         PostgreSQL (with pgvector) for local development
├── infra/postgres/init/       creates the separate test database
├── docs/                      the blueprint - read these before changing the design
│   ├── 01-architecture.md
│   ├── 02-database-schema.md
│   ├── 03-api-contracts.md
│   ├── 04-frontend-routes.md
│   ├── 05-rag-pipeline.md
│   ├── 06-llm-interfaces.md
│   └── 07-class-aware-rules.md
├── frontend/                  only a README until Step 5
└── backend/
    ├── .env.example           every setting, explained
    ├── requirements.txt       pinned versions (requirements-dev.txt adds the test tools)
    ├── pyproject.toml         pytest and ruff settings
    ├── alembic/               database migrations (0001: accounts and learners)
    ├── scripts/               init_env.py (creates .env), seed.py (demo accounts)
    ├── tests/                 unit/ needs nothing running · api/ needs the database
    └── app/
        ├── main.py            the FastAPI app
        ├── core/              settings, database, security, errors, logging, shared vocabulary
        ├── models/            database tables
        ├── schemas/           request / response shapes
        ├── auth/              sign-up, sign-in, tokens, child mode, "who is calling"
        ├── class_profiles/    the rules for each class, Nursery to Class 12
        ├── services/          business logic and data isolation
        ├── api/               HTTP routes (thin)
        ├── rag/               (Steps 2-4)
        ├── llm/               (Step 3)
        ├── question_generation/   (Steps 4, 10)
        ├── adaptive_learning/     (Steps 7, 10)
        ├── analytics/         (Steps 4, 7, 10, 11)
        └── utils/
```

`CLAUDE.md` (instructions for Claude) was added after Step 4.

## What Step 2 added

```
backend/
├── alembic/versions/0002_…py      books, documents, chapters, topics, exercises, document_chunks
├── scripts/sample_data/           a sample chapter the seed script puts in "My Books"
├── tests/fakes.py · samples.py    stand-ins for OCR, and sample PDF / DOCX / TXT books
└── app/
    ├── storage/                   FileStorage interface + local folder (uploads are private)
    ├── core/tasks.py              background TaskQueue (in-process now, Redis in Step 12)
    ├── core/middleware.py         + upload / request size limit
    ├── models/library.py          the six new tables
    ├── schemas/library.py         request / response shapes
    ├── services/library_service.py    books, chapters, exercises - and who may see them
    ├── services/document_service.py   upload, retry, remove, resume after a restart
    ├── api/v1/books.py · documents.py · chapters.py
    ├── api/v1/library_views.py    turns library rows into responses (progress checklist, sources)
    └── rag/
        ├── ocr.py                 OCRProvider + Tesseract adapter (off unless OCR_PROVIDER=tesseract)
        └── ingestion/             check file -> read text -> clean -> find structure -> chunks
```

To update a Step 1 setup: `pip install -r requirements-dev.txt` (new libraries),
`alembic upgrade head` (migration 0002), `pytest`, and optionally `python -m scripts.seed` for the
sample book.

## What Step 3 added

```
backend/
├── alembic/versions/0003_…py     pgvector, chunk vectors, keyword index
├── scripts/reembed.py             make every book searchable (run once after upgrading from Step 2)
├── scripts/eval_retrieval.py      search quality on the sample book (recall@5, MRR, threshold)
├── scripts/sample_data/retrieval-eval.json   the questions that evaluation asks
├── tests/live/                    opt-in real calls to Claude:  pytest -m live
└── app/
    ├── llm/                       LLMProvider interface + Claude adapter (structured output, tiers)
    ├── rag/embeddings.py          local multilingual search model (no key, no cost per book)
    ├── rag/retrieval.py           filtered vector + keyword search, context with [S1] tags
    ├── rag/answering.py           query understanding, grounded explanation, citation check
    ├── rag/indexing.py            re-embeds stale chunks
    ├── services/learn_service.py  "Explain this", or "not enough information"
    ├── schemas/learn.py           request / response shapes
    └── api/v1/learn.py            POST /learn/explain
```

To update a Step 2 setup: `pip install -r requirements-dev.txt`, `alembic upgrade head`
(migration 0003), `python -m scripts.reembed`, `pytest`. To use Explain, set
`LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` in `backend/.env`.

## What Step 4 added

```
backend/
├── alembic/versions/0004_practice.py   questions, practice_sessions, practice_items, question_attempts
├── tests/api/test_practice.py          Create Practice -> answer -> help -> progress
├── tests/unit/test_question_checks.py · test_question_generator.py
└── app/
    ├── question_generation/           write -> check -> independent review -> replace; marking answers
    │   ├── schemas.py                 what the AI fills in
    │   ├── strategy.py                formats, difficulty mix, JEE / NEET / board strategy
    │   ├── validation.py              the checks of spec §19 a program can decide
    │   ├── generator.py               the batch loop
    │   └── checking.py                exact marking; AI marking of written answers
    ├── analytics/progress.py          basic performance
    ├── models/practice.py             the four new tables
    ├── schemas/practice.py            request / response shapes
    ├── rag/retrieval.py               + search by place (an exercise, a chapter, a book)
    ├── services/practice_service.py   Create Practice, the question bank, answers, help, explain
    └── api/v1/practice.py             /practice/sessions..., /students/{id}/progress
```

To update a Step 3 setup: `alembic upgrade head` (migration 0004), `pytest`. With the AI switched
on, `pytest -m live` also runs the whole write-and-review loop on the real model (two MCQs).

## Notes for next step

*Rewritten at the end of every step. Last updated: end of Step 4.*

### Where things stand

- Steps 1–4 are done: the **whole MVP backend** works. 246 tests pass (2 live tests skipped by
  default); `ruff check` and `ruff format --check` are clean; migration 0004 is applied to the
  development database.
- Step 4 is not committed yet. Commit it before Step 5 starts.

### What Step 4 built

- **Create Practice** from an exercise, a chapter, a book or all of a child's books, with count,
  difficulty, question type and language. The class profile decides which formats are allowed,
  the usual count, and option counts (for example, 3 options for Nursery–Class 2).
- **Generation loop**: the AI writes up to 10 questions per batch. Program checks come first
  (spec §19). A second, independent solve follows on the strong tier, without seeing the
  proposed answer. Failed questions are rewritten with the reasons, for at most 2 extra rounds;
  questions that still fail are dropped. A session can therefore hold fewer questions than asked.
- **Question bank**: checked questions are saved per family and reused. A learner is never served
  a question they have already seen, so the AI writes only the shortfall.
- Sessions are prepared **in the background** (`preparing` → `ready`; `failed` with a
  parent-friendly message). A session still `preparing` when the API stops is picked up again
  at the next start, as unfinished books are. Every answer is a `question_attempts` row with the
  time taken and the help that was opened.
- **Help**: Hint (one at a time) → Show Steps → Show Answer. "Explain this question" uses the
  styles from Step 3. Nursery–Class 2 get `try_again` on a wrong answer, and the answer is not
  revealed.
- **Marking** is exact for choice, number, blank and matching answers. Written answers are marked
  by the AI (fast tier).
- **Progress** counts the first answer to each question in a session: accuracy, time, hints, and
  results by chapter and by topic, plus recent sessions.

### New tables (migration 0004)

| Table | Holds |
|---|---|
| `questions` | the question bank: owner, book / chapter / topic / exercise, class, subject, format, style, difficulty, language, body, answer, hints, solution, source chunks, page, validation result |
| `practice_sessions` | one Create Practice: learner, place, settings, `status`, `error_code`, `completed_at` |
| `practice_items` | which questions a session serves, in order, and the help opened (hints, steps, answer) |
| `question_attempts` | every answer: response, correct or not, feedback, time, hints used, solution viewed |

### New endpoints

| Method and path | Purpose |
|---|---|
| `POST /api/v1/practice/sessions` | Create Practice (201; poll while `preparing`) |
| `GET /api/v1/practice/sessions/{id}` | the session and its questions (never with answers) |
| `POST /api/v1/practice/sessions/{id}/answers` | answer one question |
| `POST /api/v1/practice/sessions/{id}/questions/{question_id}/help` | hint / steps / answer |
| `POST /api/v1/practice/sessions/{id}/questions/{question_id}/explain` | explain simply / like I'm 10 / Hindi / Hinglish |
| `GET /api/v1/students/{id}/progress` | basic progress |

Full shapes are in [docs/03-api-contracts.md](docs/03-api-contracts.md) §3.5.

### Known issues

- **The real Claude API has not been tried yet** (there is no key). The request and response
  shapes were checked offline only. Run `pytest -m live` once `ANTHROPIC_API_KEY` is set.
- The "not enough information" threshold (`min_similarity = 0.76`) separates covered questions
  from off-topic ones only narrowly on the sample book (0.766 vs 0.752). Check it again with
  `python -m scripts.eval_retrieval` on real textbooks.
- Vector search is exact, with no vector index, inside the family's filtered set. That is fine
  at family scale; add an HNSW index if it gets slow. There is no separate reranker either:
  the merged rank order is used (see `app/rag/retrieval.py`).
- Background jobs run inside the API process. Rate limiting, token revocation on sign-out and
  security headers are still missing; all of these are planned for Step 12.

### Loose ends

- **Node.js on this machine is v21.5.0**, an odd-numbered release with no support. Install the
  LTS (`brew install node@22`) before Step 5.

### What Step 5 needs to know

- The API runs at `http://localhost:8000/api/v1`, with interactive docs at `/docs`. CORS already
  allows `http://localhost:3000` (`CORS_ORIGINS` in `backend/.env`).
- **Sign-in:**
  - `POST /auth/register` and `POST /auth/login` return an access token (30 minutes) and a
    refresh token (14 days);
  - `POST /auth/refresh` and `GET /auth/me` complete the set;
  - keep the tokens in httpOnly cookies set by the Next.js server
    ([docs/04-frontend-routes.md](docs/04-frontend-routes.md) §4.6).
- **Onboarding:** `GET /meta/options` returns everything the forms need, and
  `GET /meta/classes/{class_level}` returns one class's rules. Children are managed with
  `/students` and their profile with `PUT /students/{id}/profile`.
- **Child mode:** `POST /students/{id}/session` returns a token that can act only as that child.
- **The four layouts** come from the class profile's `ui_mode`: `playful` (Nursery–Class 2),
  `friendly` (Classes 3–5), `standard` (Classes 6–8) and `dense` (Classes 9–12). Its `features` say which screens to hide.
- Every error has the shape `{"error": {"code", "message", "details"}}`. Use `code` to choose the
  message shown on screen; `message` is plain English that is safe to show a parent.
- In parent-facing screens, use the words in docs/04 §4.5, not technical terms.
