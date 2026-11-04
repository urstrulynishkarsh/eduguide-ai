# CLAUDE.md

Guidance for Claude when working in this repository. Read this file and ROADMAP.md at the start of every session.

## Project overview

An AI-powered study platform for Indian school students, Nursery to Class 12 (and JEE/NEET aspirants). Parents sign up, create child profiles, and upload textbooks. The app reads the books, splits them into chapters, exercises and chunks, and generates practice questions with hints and solutions. Layouts adapt to the child's age group.

User roles: parent and student. A student is either a child profile under a parent (used through child mode) or a solo student with their own account. There is no admin role.

## Tech stack

- Backend: Python 3.12 (3.11+ works) + FastAPI, fully async
- Database: PostgreSQL 16 with pgvector, run in Docker (`pgvector/pgvector:pg16`)
- ORM / migrations: SQLAlchemy 2.1 (async, asyncpg) + Alembic, one migration per step (`0001`–`0009` so far)
- Auth: JWT access tokens (30 min) + refresh tokens (14 days) with PyJWT; passwords hashed with Argon2. Child mode is a parent token limited to one child.
- Frontend: Next.js 16 (App Router, Cache Components on) + React 19 + TypeScript + Tailwind CSS 4 + shadcn/ui (radix), Node.js 22/24 LTS. Versions are pinned exactly in `frontend/package.json`. Next.js 16 differs from older versions: read `frontend/node_modules/next/dist/docs/` before using an API you are unsure of (`middleware` is now `proxy.ts`)
- Frontend tests and checks: Vitest + Testing Library (unit), Playwright (end to end, against the real API), ESLint, Prettier (print width 110), `tsc`
- AI provider: switched off unless `backend/.env` sets one. `LLM_PROVIDER=groq` + `GROQ_API_KEY`: open models on Groq through the `groq` SDK (free plan; `openai/gpt-oss-20b` / `-120b`). `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`: Claude through the `anthropic` SDK, `claude-opus-5-5` for every tier (connected in step 3). Both behind `app/llm/`'s `LLMProvider`.
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
    question_generation/ # write -> check -> independent review of questions; marking answers; test papers
    analytics/           # progress numbers and progress over time; previous-year paper analysis; streaks, XP, badges
    adaptive_learning/   # mastery per topic, difficulty that follows it, daily recommendations, study planner,
                         # misconceptions
    chat/                # the Student AI Tutor (hint ladder) and the Parent AI Assistant
    utils/
  alembic/versions/      # migrations
  scripts/               # init_env, seed (+ demo_questions: practice without an AI key), reembed, eval_retrieval
  tests/                 # unit/ (nothing running), api/ (needs the database), live/ (real Claude, opt-in)
frontend/
  app/                   # screens: (entry)/ sign-in, sign-up, onboarding, who-is-learning; parent/; learn/;
                         # api/ holds the two route handlers: book upload, chat replies (streamed)
  proxy.ts               # before every page: renews tokens, sends each session to its area
  lib/                   # session cookies, backend calls (server only), Server Actions, navigation;
                         # copy/ holds every word on screen, one file per language (en, hi, hinglish)
  components/            # shared pieces; ui/ holds the shadcn components in use
  tests/                 # unit/ (Vitest), e2e/ (Playwright; needs the database and the API)
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
pytest -m live                      # real calls to Groq / Claude, for each key in .env

# Code checks
ruff check . && ruff format --check .

# Frontend (from frontend/; the API must be running for the site to work)
npm install
cp .env.example .env.local          # first time only
npm run dev                         # http://localhost:3000
npm test                            # unit tests
npm run test:e2e                    # browser journeys; needs the API and `python -m scripts.seed`;
                                    # first time: npx playwright install chromium
npm run lint && npm run typecheck && npm run format:check && npm run build

# Database migrations
alembic revision --autogenerate -m "what changed" --rev-id 0010   # next free number; review the file
alembic upgrade head
```

## What exists so far

- Step 1: design docs, sign-up and sign-in, parent and student roles, child profiles, child mode, class rules
- Step 2: book upload and reading (PDF, DOCX, TXT, optional OCR), chapters, topics, exercises, chunks
- Step 3: search inside books (meaning + keyword), the Claude connection, "Explain this" with sources
- Step 4: practice engine: checked question generation, question bank, hints → steps → answer, attempts, basic progress
- Step 5: frontend foundation: landing page, sign-up / sign-in, onboarding, "Who is learning?", child mode, Children and Settings, the four age-based layouts
- Step 6: frontend MVP, the app works end to end: My Books and upload with the reading checklist, chapter page, Create Practice, the practice screen (with the picture version for Nursery–Class 2), Learn a Concept, progress, basic dashboard, child switcher; demo practice questions in the seed
- Step 7: adaptive learning (backend): mastery per topic after every answer, difficulty that follows it,
  weak-topic detection, daily recommendations, practice for one topic
- Step 8: mock tests and study planner (backend): sectioned papers from the question bank (practice,
  chapter, full mock; timed from Class 9), saved answers, marking with part marks, the result report;
  one study plan per learner, planned again each morning from mastery
- Step 9: the full parent dashboard (week chart, strong / needs attention, Start Recommended Practice,
  today's plan, recent tests); Mock Tests and the test screen (grid, timer, answers saved as given,
  report); Study Plans (today's tasks with Start and ✓ Done); the Parent AI Assistant and the Student
  AI Tutor (hint ladder), replies streamed as Server-Sent Events; Recommended for You on the learner home
- Step 10: previous-year papers (read into sections and questions; the AI matches every question to a
  textbook chapter; where the marks go, trends, the latest layout; a test like the papers);
  misconception detection (the AI names repeated wrong ideas, a rule resolves them; shown to parent
  and learner, given to the question writer and the assistant); JEE / NEET / CUET modes (exam
  patterns with negative marking, by the learner's goal)
- Step 11: every screen in English, Hindi and Hinglish (a language picker; child mode in the child's
  language; backend reasons and errors worded by code), streaks / XP / levels / badges (stars and
  stickers for Nursery–Class 2), progress over time (12-week chart, test scores, by subject, kind of
  question and difficulty; marks by year on a paper analysis)
- Next: step 12, production hardening (rate limiting, Redis workers, Docker images, CI, monitoring,
  security review)

See ROADMAP.md for the full 12-step plan and the "Notes for next step" handoff section.

## Coding conventions

- Keep route handlers thin; put logic in services.
- Every new endpoint needs input validation and at least one test. Every new screen needs at least one unit or browser test.
- Screen text goes in `frontend/lib/copy/`, never inline: add it to `en.ts`, `hi.ts` and `hinglish.ts` (the
  `Copy` type fails the build if one is missing). Pages, layouts and async server components use
  `await getCopy()`, synchronous server components a `copy` prop, client components `useCopy()`
  (docs/04 §4.6). The backend sends codes, not sentences, for anything a screen shows. Parent screens
  use the words in docs/04 §4.5.
- Every frontend page that loads data gets its own `loading.tsx` (`export { default } from "@/app/loading";`),
  or moving between pages waits on the server with no sign of life (see `frontend/app/loading.tsx`).
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
