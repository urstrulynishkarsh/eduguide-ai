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
| **5** | ✅ | **Frontend foundation.** Next.js app, design system with the four age-based layouts, landing page, sign-up / sign-in, onboarding, child mode. | `frontend/` | screens for items 1–4 |
| **6** | ✅ | **Frontend MVP.** My Books and upload with progress, Create Practice, the student practice screen (including the picture-based one for Nursery–Class 2), basic progress. **The MVP works end to end here.** | `frontend/` | 14 Student practice interface |

## Phase 2

| Step | Status | What you get | Folders it fills | Spec items (§46) |
|---|---|---|---|---|
| **7** | ✅ | **Adaptive learning.** Mastery per topic, difficulty that follows performance, weak-topic detection, daily recommendations. | `backend/app/adaptive_learning` · `backend/app/analytics` | 1 Adaptive difficulty · 3 Weak-topic detection · 4 Study recommendations |
| **8** | ✅ | **Mock tests and study planner** (backend). Sectioned, timed tests with a result report; study plans that update with performance. | `backend/app/services` · `backend/app/api/v1` | 5 Mock tests · 6 Study planner |
| **9** | ✅ | **Parent dashboard, test and plan screens, the two assistants.** Parent AI Assistant and Student AI Tutor (hint first, answer last). | `frontend/` · `backend/app/api/v1` | 2 Parent dashboard |

## Phase 3

| Step | Status | What you get | Folders it fills | Spec items (§46) |
|---|---|---|---|---|
| **10** | ✅ | **Previous-year paper analysis, misconception detection, JEE / NEET / CUET modes.** Papers read into sections and questions, matched to the textbook chapters by the AI, where the marks go and a test like them; repeated wrong ideas found and put right; exam patterns with negative marking. Plus their screens. | `backend/app/analytics` · `backend/app/adaptive_learning` · `backend/app/question_generation` | 1 Previous-year analysis · 2 Misconception detection · 3 Competitive exam modes |
| **11** | ✅ | **Languages, gamification, advanced analytics.** Hindi / Hinglish screens, structure for more Indian languages, streaks / XP / badges, richer charts. | `frontend/` · `backend/app/analytics` | 4 Multi-language support · 5 Gamification · 6 Advanced analytics |
| **12** | ✅ | **Production hardening.** Rate limiting, background workers on Redis, Docker images, CI, monitoring, a security review. | `infra/` · whole project | — |

Note: content in **Hindi and Hinglish** works from Steps 3–4 (the language is part of every request
to the AI); Step 11 translated the screens and made a place for further Indian languages.

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

## What Step 5 added

```
frontend/
├── package.json · package-lock.json     exact versions (Next.js 16.4, React 19.3, Tailwind 4.3, …)
├── .env.example                         API_BASE_URL (copy to .env.local)
├── next.config.ts · proxy.ts            Cache Components on; proxy = token renewal + area redirects
├── app/
│   ├── page.tsx                         landing page (spec §49)
│   ├── (entry)/                         login, register, onboarding/child, onboarding/profile, who-is-learning
│   ├── parent/                          layout (menu), children, children/new, children/[studentId], settings
│   ├── learn/                           layout (the four layouts), home, exit (leave child mode)
│   ├── signout/route.ts                 clears the session cookies
│   ├── globals.css                      design tokens and the four data-ui-mode palettes
│   └── loading.tsx · not-found.tsx
├── lib/
│   ├── session.ts · routes.ts           cookies and token claims · which area a session may see
│   ├── backend.ts · api.ts              calling the API (api.ts is server-only and reads the cookie)
│   ├── actions/auth.ts · students.ts    Server Actions behind every form
│   ├── forms.ts                         form fields → API bodies; API errors → messages by field
│   ├── navigation.ts                    parent menu; student menu per layout, filtered by features
│   ├── copy.ts                          every word on screen
│   └── types.ts · utils.ts
├── components/                          learner-profile-form (class first), nav-links, field, …; ui/ (shadcn)
└── tests/unit (Vitest, 62) · tests/e2e (Playwright, 7 journeys × desktop + phone)
```

No backend changes. To update a Step 4 setup: install **Node.js 22 or 24 LTS**, then in
`frontend/`: `npm install`, `cp .env.example .env.local`, `npm run dev`. For the browser tests,
once: `npx playwright install chromium`.

## What Step 6 added

```
frontend/
├── app/parent/dashboard · progress          basic dashboard and progress of the chosen child
├── app/parent/books/…                        My Learning Library, Upload Book, a book, a chapter page
├── app/parent/practice · practice/[id]       Create Practice; a prepared practice with "Start now with …"
├── app/learn/practice · practice/[id]        choose practice; the practice screen and its results
├── app/learn/concepts · concepts/[id]        Learn a Concept ("Explain this" with sources)
├── app/learn/progress                        My progress / My Stars
├── app/**/loading.tsx                        one per page that loads data (re-exports app/loading.tsx)
├── app/api/books/[bookId]/documents          the upload route (streams the file to the backend)
├── lib/actions/books.ts · practice.ts        child switcher, books and files; practice, answers, help, explain
├── components/                               practice-player, book-uploader, practice-chooser, explain-box,
│                                             progress-view, document-checklist, child-switcher, …
└── tests/unit (80) · tests/e2e (10 journeys × desktop + phone)
backend/
├── scripts/demo_questions.py                 hand-written practice questions for the two demo books
├── scripts/sample_data/ukg-picture-book-sample.txt   Anaya's sample book (Hindi)
├── scripts/seed.py                           + the UKG book and the demo questions
├── app/services/practice_service.py          `to_question` is public (the seed reuses it)
└── tests/unit/test_demo_questions.py         the demo questions pass the generated questions' checks
```

No API or database changes. To update a Step 5 setup: `python -m scripts.seed` (adds Anaya's book and
the demo questions; nothing else is touched), then rebuild or restart the frontend.

## What Step 7 added

```
backend/
├── alembic/versions/0005_adaptive_learning.py   student_mastery, recommendations, practice_sessions.topic_id
├── tests/unit/test_adaptive_rules.py            credit, mastery, the level rule, status
├── tests/api/test_adaptive.py                   levels up and down, strengthen / continue / review /
│                                                new chapter, done, the youngest, who may see it
└── app/
    ├── adaptive_learning/mastery.py             an area's numbers after every answer; the level rule
    ├── adaptive_learning/recommendations.py     today's list (India time); marking one done
    ├── analytics/progress.py                    + first_answers(), shared with mastery
    ├── models/adaptive.py · schemas/adaptive.py the two tables; the responses
    ├── services/adaptive_service.py             who may see it; which books are the learner's
    ├── api/v1/adaptive.py                       /students/{id}/mastery, /students/{id}/recommendations
    ├── services/practice_service.py             practice for one topic; answers update mastery
    └── services/library_service.py · rag/retrieval.py   get_topic, chunks by topic
```

To update a Step 6 setup: `alembic upgrade head` (migration 0005), `pytest`. No new libraries and
no frontend changes.

## What Step 8 added

```
backend/
├── alembic/versions/0006_…py            mock_tests, mock_test_questions, test_attempts, study_plans,
│                                        study_plan_items; question_attempts: test_attempt_id, marks
├── tests/unit/test_paper.py · test_planner.py
├── tests/api/test_mock_tests.py · test_study_plans.py
├── tests/api/helpers.py                 + family_with_book(), bank() (shared with test_adaptive.py)
└── app/
    ├── models/practice.py               QuestionSettings: the columns a practice and a test share
    ├── models/mock_test.py · study_plan.py · schemas/mock_test.py · study_plan.py
    ├── services/question_bank.py        unseen questions from the bank, writing the rest, the
    │                                    background job frame - moved out of practice_service, shared
    ├── question_generation/paper.py     which tests a class has; sections, marks, default size and time
    ├── question_generation/checking.py  is_correct() → None for written answers; written_marks() (part marks)
    ├── services/mock_test_service.py    make the paper, sittings, saved answers, marking, the report
    ├── adaptive_learning/planner.py     the study planner's rules (tasks, then days) - no database
    ├── services/study_plan_service.py   one plan per learner, planned again each morning; ticked off
    ├── api/v1/mock_tests.py · study_plans.py
    ├── analytics/progress.py            first_answers() also per test sitting
    └── utils/pagination.py              the cursor pages of the books list, now shared with tests
```

To update a Step 7 setup: `alembic upgrade head` (migration 0006 - already applied to this
machine's database at the end of the step), `pytest`. No new libraries and no frontend changes.

## What Step 9 added

```
backend/                                  Part A
├── alembic/versions/0007_chat.py         chat_sessions, chat_messages
├── app/llm/base.py · anthropic_provider.py · groq_provider.py
│                                         stream_text(): replies piece by piece (same fallback, effort
│                                         and caching settings as the structured calls)
├── app/analytics/progress.py             week(): the last 7 days (India time)
├── app/schemas/dashboard.py · services/dashboard_service.py · api/v1/dashboard.py
│                                         GET /students/{id}/dashboard (snapshot() is shared)
├── app/chat/tutor.py · assistant.py      the hint ladder (code decides the rung) · the assistant's facts
├── app/models/chat.py · schemas/chat.py · services/chat_service.py · api/v1/chat.py
│                                         conversations; POST …/messages streams Server-Sent Events
├── scripts/demo_questions.py · seed.py   + 4 short and 3 long Class 7 questions
└── tests/                                test_dashboard, test_chat, test_tutor, test_citations
frontend/                                 Part B
├── app/parent/dashboard                  the full dashboard
├── app/parent/tests/… · learn/tests/…    Mock Tests, Create Test, a test with its sittings and report;
│                                         the learner's tests and the test screen
├── app/parent/plans/… · learn/plan/…     Study Plans and Make a plan; today's tasks
├── app/parent/assistant/… · learn/tutor/…   the Parent AI Assistant and the Student AI Tutor
├── app/api/chat/[chatId]/messages        passes a streamed reply through (behind proxy.ts)
├── lib/actions/tests.ts · plans.ts · chat.ts · lib/sse.ts (reads Server-Sent Events)
├── components/                           answer-input, question-chooser + question-settings-form,
│                                         start-button, test-player, test-report, plan-view, plan-form,
│                                         dashboard, chat-box, chat-screen
└── tests/unit (110) · tests/e2e (13 journeys × desktop + phone)
```

To update a Step 8 setup: `alembic upgrade head` (migration 0007), `python -m scripts.seed` (adds the
7 new demo questions; nothing else changes), then restart the API and rebuild or restart the frontend.
No new libraries. `npm test` needs Node.js 22.12 or newer.

## What Step 10 added

```
backend/
├── alembic/versions/0008_…py            paper_analyses, paper_questions, student_misconceptions;
│                                        mock_tests.exam, student_mastery.examined_until
├── app/rag/ingestion/structure.py       question-paper mode: one chapter per file, sections as exercises
├── app/rag/ingestion/labels.py          exercise_title() (a paper's "Section A" as printed), shared
├── app/question_generation/paper.py     EXAMS (JEE / NEET / CUET patterns, negative marks, pace),
│                                        pattern_for(), spread() (shared with the analysis)
├── app/analytics/paper_reading.py       the AI reads a paper: marks, format, textbook area of each question
├── app/analytics/papers.py              where the marks go, trend, layout, the test's sections - no database
├── app/adaptive_learning/misconceptions.py   after_answer() (resolve, due?), examine() (the AI), lists
├── app/models/paper.py · schemas/paper.py · services/paper_analysis_service.py · api/v1/papers.py
├── app/services/question_bank.py        ChapterPlace (a section spread over chapters); mistakes to the writer
├── app/services/mock_test_service.py    exam patterns, negative marking, previous_year tests, examine jobs
├── app/services/dashboard_service.py · api/v1/adaptive.py   misconceptions (dashboard, GET …/misconceptions)
└── tests/                               test_papers (unit + api), test_misconceptions, exam modes in
                                         test_mock_tests, papers in test_structure, test_paper
frontend/
├── components/paper-analysis.tsx        the analysis on a paper book's page
├── components/dashboard.tsx             + Mistakes (Understand Mistakes / Mistakes to fix)
├── components/question-chooser.tsx      the exam-mode note; previous_year is not chosen here
├── components/test-report.tsx           testSummary() (with the exam); a lost mark in red
├── lib/navigation.ts                    conceptHref() (shared by recommendations, plan tasks, mistakes)
├── lib/actions/books.ts                 analysePapers()
└── tests/unit/papers-and-mistakes.test.tsx · tests/e2e/papers.spec.ts
```

To update a Step 9 setup: `alembic upgrade head` (migration 0008 - already applied to this machine's
database), then restart the API and rebuild or restart the frontend. No new libraries, no seed change.

## What Step 11 added

```
backend/
├── alembic/versions/0009_…py            student_rewards, student_badges; the reason columns of
│                                        recommendations and study_plan_items become jsonb
├── app/analytics/rewards.py             XP, levels, streaks, the day's goal, badges: record() (in the
│                                        answer's transaction) and summary()
├── app/analytics/progress.py            weeks() and shares() beside week(), one counting function (_periods)
├── app/models/rewards.py · schemas/rewards.py · api/v1/rewards.py   GET /students/{id}/rewards
├── app/schemas/adaptive.py              Reason: a code and its numbers instead of an English sentence
├── app/adaptive_learning/recommendations.py · planner.py · mastery.right_lately()   reasons as codes
├── app/schemas/auth.py · auth/service.py · api/v1/auth.py   PATCH /auth/me (screen language)
├── app/services/dashboard_service.py    rewards on the dashboard; trends() → GET …/progress/trends
├── app/services/practice_service.py · mock_test_service.py   rewards counted with each answer / submit
├── scripts/seed.py                      the demo parent's screens are English
└── tests/                               test_rewards (unit + api), test_trends; reasons as codes
frontend/
├── lib/copy/                            en.ts · hi.ts · hinglish.ts (one shape, `Copy`), index.ts (the
│                                        languages, said(), classLabel(), reasonText()), server.ts
│                                        (getCopy(), titled())
├── components/copy-provider.tsx         useCopy() for client components
├── components/language-picker.tsx       landing, entry pages, parent Settings, a solo student's header
├── components/form-message.tsx          errors worded by their code
├── components/rewards.tsx               RewardStrip, BadgeList
├── components/charts.tsx                ColumnChart (the week chart, generalised), LineChart, Sparkline,
│                                        DataTable
├── components/progress-over-time.tsx    the Progress pages' charts
├── app/layout.tsx                       the screen language (cookie), Noto Sans Devanagari
├── app/**                               every page: getCopy() / titled(); class labels, reasons, dates
│                                        in the screen language
└── tests/unit (132): languages, rewards, charts · tests/e2e (15 journeys): languages.spec.ts;
                                         practice journeys in the child's language, with rewards
```

To update a Step 10 setup: `alembic upgrade head` (migration 0009 - already applied to this machine's
database; it removes today's recommendations, which are made again on the next visit), then restart
the API and rebuild or restart the frontend. No new libraries. The demo parent now signs in to
English screens; on a database seeded before Step 11 its account stays Hinglish until it is switched
in Settings (this machine's database was switched).

## What Step 12 added

```
backend/
├── alembic/versions/0010_auth_sessions.py   auth_sessions (tokens name their session: `ses`)
├── app/core/tasks.py            RedisTaskQueue (SAQ, JSON, a key per piece of work) beside the
│                                in-process queue, chosen by REDIS_URL; run_job() counts each job
├── app/worker.py                python -m app.worker [--check]: JOBS, heartbeats, resumes unfinished work
├── app/core/rate_limits.py      fixed windows in Redis or memory; check(), failures() (sign-in)
├── app/core/redis.py · metrics.py   one Redis client; Prometheus counters, served on METRICS_PORT
├── app/core/middleware.py       + security headers, requests counted by route pattern
├── app/core/logging.py          LOG_FORMAT=json
├── app/core/config.py           REDIS_URL (required in production), LOG_FORMAT, METRICS_PORT
├── app/core/database.py         hide_parameters in production
├── app/auth/ · api/v1/auth.py   sessions; POST /auth/logout; sign-in and sign-up limits
├── app/api/deps.py              limit_account(), limit_address(), client_address()
├── app/api/health.py            /health/ready also checks Redis
├── app/llm/*_provider.py        AI calls and tokens counted
├── app/main.py                  API docs off in production; resumes work only without Redis
├── Dockerfile · .dockerignore   one image: api, worker, migrate (Tesseract inside, never root)
└── tests/                       redis/ (queue, worker, limits; Redis db 15), test_sessions,
                                 test_rate_limits (api + unit), test_route_security (every route),
                                 headers / metrics / JSON logs in test_health, Word-file bombs
frontend/
├── next.config.ts               security headers (CSP without nonces); standalone output for Docker
├── app/signout/route.ts · lib/actions/auth.ts   sign out on the backend; leaving child mode too;
│                                the browser's address passed on at sign-in and sign-up
├── lib/backend.ts               endSession(), forwardedFor
├── lib/copy/hi.ts · hinglish.ts too_many_requests, daily_limit_reached
├── Dockerfile · .dockerignore
└── tests/unit/signout.test.ts
infra/
├── docker-compose.production.yml   Caddy → frontend → api; worker; migrate; PostgreSQL; Redis;
│                                   Prometheus (profile monitoring)
├── Caddyfile · production.env.example
└── monitoring/prometheus.yml · alerts.yml
.github/workflows/ci.yml          backend, frontend, e2e, images (+ pip-audit, npm audit)
docs/08-security-review.md        what was checked, fixed, and is still open
docker-compose.yml                + Redis
```

To update a Step 11 setup: `docker compose up -d` (starts Redis, which the tests now need),
`pip install -r requirements-dev.txt` (saq, redis, prometheus-client, pip-audit; pillow 13 and
fastembed 0.9.1), `alembic upgrade head` (migration 0010 - already applied to this machine's
database; **everyone signs in once more**), then restart the API and rebuild or restart the
frontend. `REDIS_URL` stays empty locally unless you want a worker (README).

## Notes for next step

*Rewritten at the end of every step. Last updated: end of Step 12.*

### Where things stand

- **All 12 steps are done.** Backend: 413 tests pass (live tests skipped), `ruff` clean,
  `pip-audit` clean. Frontend: 136 unit tests and 15 browser journeys (desktop + phone) pass;
  `lint`, `typecheck`, `format:check` and `build` are clean; `npm audit` has 8 moderate warnings,
  all in the lint tools.
- Tried for real in Step 12: the API and a worker with Redis reading a book (the job in Redis, the
  worker's and the API's metrics, `--check`); the whole production setup on this computer
  (`DOMAIN=localhost`: HTTPS, http → https, headers, JSON logs) with the sign-up journeys run
  through it; all 30 journeys against the production build with the CSP on.
- **CI has not run yet**: it runs on the first push to GitHub. If a job fails there, its log and
  (for the browser journeys) the uploaded report say why.
- Node.js: run frontend commands as `PATH="$HOME/.local/node-v24/bin:$PATH" npm …` (unchanged).

### What Step 12 built

- **Background workers.** `REDIS_URL` empty: jobs run in the API, as before. Set: `RedisTaskQueue`
  sends a job's name and ids (JSON) to Redis through SAQ, keyed by name and ids so the same work is
  never queued twice; `python -m app.worker` runs only the jobs in `JOBS`, marks a running job alive
  every 30 s (taken over after 120 s without), gives up a job after 2 hours or 3 tries, and queues
  unfinished work again when it starts. A stopping worker waits 10 s, then puts running jobs back.
  The rewards row lock is untouched (it is in the answer's request, not a job).
- **Rate limits** (docs/03 §3.11): failed sign-ins (10 per email, 60 per address, 15 minutes; a
  full count refuses before the password is checked; a successful sign-in counts nothing), sign-ups
  (60 per address an hour), and per family: 20 AI requests a minute / 300 a day, 60 practices,
  tests or paper analyses a day, 100 uploads a day. `429 too_many_requests` /
  `daily_limit_reached` with `Retry-After`; worded in Hindi and Hinglish. Fail open if Redis is down.
- **Sessions**: `auth_sessions`, one per sign-in and per child-mode session; every request checks
  the token's session; `POST /auth/logout` (Sign out, leaving child mode). Refresh tokens are not
  rotated (on purpose: parallel renewals). Old rows go at the next sign-in.
- **Security headers** on the API and every page; no API docs in production; production refuses to
  start without `REDIS_URL`. **Monitoring**: Prometheus metrics on `METRICS_PORT` (API and worker),
  `infra/monitoring/` alert rules, JSON logs, readiness with Redis, the worker's `--check`.
- **Docker / server**: one backend image (api, worker, migrate), the standalone frontend image,
  Caddy in front; README "Run it on a server". **CI**: `.github/workflows/ci.yml`, actions pinned to
  commits. **Security review**: docs/08, with the fixes it led to (pillow, query values in errors,
  uvicorn's access log, a 429 that broke the form).

### Known issues

- docs/08 §8.3 lists what is still open; first: the DPDP lawyer review, password reset (it must
  revoke the sessions), backups (nothing automates them), the CSP's inline scripts.
- `fastembed` 0.9.1 was 12 days old when pinned (the rule is two weeks), to get pillow 13's fixes.
- **The Hindi and Hinglish wording has not been read by a native speaker** (`lib/copy/hi.ts`,
  `hinglish.ts`), including Step 12's two new messages.
- The rate limits, like the XP rules, are starting values; watch `eduguide_rate_limited_total`.
- Unchanged: written test answers need the AI to be marked; the server does not submit a test whose
  time ran out; lists show the first 50; a failed first chat message leaves an empty conversation;
  without Redis, reading a book can still hold the API up for a few seconds; reading a paper and
  the assistant / tutor are untried on a real model (worth one check with `LLM_PROVIDER=groq`);
  uploads live on one server's disk (object storage is one `FileStorage` adapter away).
- **Running the browser tests next to your own servers:** start the API with `LLM_PROVIDER=none` (or
  use separate ports), or the paper and assistant journeys call the AI. The journeys make 22
  sign-ups; the limit is 60 an hour per address, so with `REDIS_URL` set (shared counts) run them at
  most twice an hour, or clear the counts with `docker compose exec -T redis redis-cli --scan --pattern 'eduguide:limit:*' | xargs docker compose exec -T redis redis-cli del`.

### What comes next

The 12-step plan is complete. Sensible next pieces, each worth its own plan first: a pilot with a
few families (and the native-speaker read and the lawyer review before it), password reset and
email checks, automated backups, object storage for uploads, Alertmanager for the alerts, and the
server submitting timed-out tests.
