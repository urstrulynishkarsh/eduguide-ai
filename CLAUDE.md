# CLAUDE.md

Guidance for Claude when working in this repository. Read this file and ROADMAP.md at the start of every session.

## Project overview

An AI-powered study platform for Indian school students, Nursery to Class 12 (and JEE/NEET aspirants). Parents sign up, create child profiles, and upload textbooks. The app reads the books, splits them into chapters, exercises and chunks, and generates practice questions with hints and solutions. Layouts adapt to the child's age group.

User roles: parent and student. A student is either a child profile under a parent (used through child mode) or a solo student with their own account. There is no admin role.

## Tech stack

- Backend: Python 3.12 (3.11+ works) + FastAPI, fully async
- Database: PostgreSQL 16 with pgvector, run in Docker (`pgvector/pgvector:pg16`)
- ORM / migrations: SQLAlchemy 2.1 (async, asyncpg) + Alembic, one migration per step (`0001`–`0004` so far)
- Auth: JWT access tokens (30 min) + refresh tokens (14 days) with PyJWT; passwords hashed with Argon2. Child mode is a parent token limited to one child.
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui (not built yet; starts in step 5)
- AI provider: Claude API through the `anthropic` SDK, model `claude-opus-5-5` for every tier (connected in step 3). Switched off unless `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` are set in `backend/.env`.
- Search: local multilingual embeddings (`intfloat/multilingual-e5-base` through fastembed / ONNX, 768 dimensions) plus PostgreSQL keyword search
- File parsing: pypdfium2 (PDF), python-docx + lxml (DOCX), plain text (TXT); optional OCR with Tesseract (`OCR_PROVIDER=tesseract`)
- Tests and checks: pytest + pytest-asyncio + httpx; ruff (line length 110)

## Folder structure

```
backend/
  app/
    main.py              # the FastAPI app; start-up resumes unfinished background work
    api/                 # route handlers (thin); v1/ holds the feature routes
    auth/                # sign-up, sign-in, tokens, child mode, "who is calling"
    class_profiles/      # the rules for each class, Nursery to Class 12
    core/                # settings, database, security, errors, middleware, task queue, shared enums
    models/              # database tables
    schemas/             # request/response schemas
    services/            # business logic, transactions, data isolation
    storage/             # where uploaded files are kept
    rag/                 # reading books (ingestion/), OCR, embeddings, search, explanations
    llm/                 # AI provider interface + Claude adapter
    question_generation/ # write -> check -> independent review of questions; marking answers
    analytics/           # progress numbers
    adaptive_learning/   # empty until step 7
    utils/
  alembic/versions/      # migrations
  scripts/               # init_env, seed, reembed, eval_retrieval
  tests/                 # unit/ (nothing running), api/ (needs the database), live/ (real Claude, opt-in)
frontend/                # only a README until step 5
docs/                    # design docs 01-07
infra/postgres/init/     # creates the separate test database
docker-compose.yml
ROADMAP.md
CLAUDE.md
```

## How to run

```
# Database (from the project folder)
docker compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m scripts.init_env          # first time only: creates .env with a random secret
alembic upgrade head
python -m scripts.seed              # optional: demo accounts and a sample book
uvicorn app.main:app --reload       # API docs at http://localhost:8000/docs

# Tests (the database must be running)
pytest                              # live tests are skipped
pytest -m live                      # real calls to Claude; needs ANTHROPIC_API_KEY in .env

# Code checks
ruff check . && ruff format --check .

# Database migrations
alembic revision --autogenerate -m "what changed" --rev-id 0005   # next free number; review the file
alembic upgrade head
```

## What exists so far

- Step 1: design docs, sign-up and sign-in, parent and student roles, child profiles, child mode, class rules
- Step 2: book upload and reading (PDF, DOCX, TXT, optional OCR), chapters, topics, exercises, chunks
- Step 3: search inside books (meaning + keyword), the Claude connection, "Explain this" with sources
- Step 4: practice engine: checked question generation, question bank, hints → steps → answer, attempts, basic progress
- Next: step 5, the frontend foundation

See ROADMAP.md for the full 12-step plan and the "Notes for next step" handoff section.

## Coding conventions

- Keep route handlers thin; put logic in services.
- Every new endpoint needs input validation and at least one test.
- Every new database table or column needs a migration.
- Use clear names; no abbreviations for domain terms (book, chapter, exercise, chunk, attempt).
- Check that a parent can only access their own children's data on every endpoint.
- Never hard-code secrets or API keys. Read them from environment variables (.env, which is not committed).
- Keep features within the current roadmap step. Don't start future steps early.

## Rules for Claude

- **Never run git commit, git push, git reset, git rebase, or any git command that changes history. The user commits manually.** Read-only git commands (git status, git diff, git log) are fine.
- Show a plan before writing code for a new roadmap step, and wait for approval.
- Run the tests after making changes, and fix failures before saying the step is done.
- When a step is finished, update ROADMAP.md: mark the step done and rewrite the "Notes for next step" section (what was built, new models/tables, new endpoints, known issues, loose ends).
- If something in this file is out of date, point it out and suggest the fix.
