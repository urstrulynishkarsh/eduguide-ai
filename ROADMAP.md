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
| **8** | ⏭ | **Mock tests and study planner** (backend). Sectioned, timed tests with a result report; study plans that update with performance. | `backend/app/services` · `backend/app/api/v1` | 5 Mock tests · 6 Study planner |
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

## Notes for next step

*Rewritten at the end of every step. Last updated: end of Step 7.*

### Where things stand

- Steps 1–7 are done. Backend: 286 tests pass (live tests skipped), `ruff` clean. The frontend
  did not change in Step 7 (its 80 unit tests and 10 browser journeys passed at the end of Step 6).
- **Added after Step 7: Groq as a second AI provider** (free plan). `app/llm/groq_provider.py`,
  `groq==1.7.0` in requirements, `LLM_PROVIDER=groq` + `GROQ_API_KEY` in `backend/.env`;
  `LLM_MODEL_*` now default to empty = the provider's own models (`DEFAULT_MODELS` in each
  adapter). Live tests (`tests/live/test_ai_providers.py`) run for every provider with a key.
  To update: `pip install -r requirements-dev.txt`.

### What Step 7 built

- **Areas.** Mastery is kept per *area*: a topic of a chapter, or the chapter itself for questions
  without a topic (most of Anaya's demo questions have none). One `student_mastery` row per learner
  and area, worked out again after every answer, in the answer's transaction
  (`mastery.record_answer`, called from `practice_service.answer`).
- **The numbers** (doc 7, 7.9) come from the last 10 *first* answers in the area
  (`analytics.progress.first_answers`, shared with basic progress): accuracy; mastery (credit 1 for
  right, −0.25 per hint, 0.25 after the solution, 0 for wrong; recent and harder answers weigh more);
  confidence (answers ÷ 10). Status: `needs_attention` below 60 % over ≥ 5 answers (Class 6–12 only),
  `strong` at mastery ≥ 0.85 over ≥ 5 answers, otherwise `learning`.
- **Adaptive difficulty** (Class 6–12): each area has a level, starting at medium, moved by the rule
  (> 85 % up, < 60 % down) only on ≥ 5 answers given since it last moved (`difficulty_since`).
  Nursery–Class 5: no levels, no weak label; gentle repetition with easy questions.
- **Recommendations**: at most 3 a day, made on the first `GET` of the day (India time, fixed
  +05:30) and kept for the day; in order `strengthen` (weak area: revise + practice at its lowered
  level) · `continue` (being learned, practised this week) · `review` (not practised for 7 days) ·
  `new_chapter` (never practised, books of the learner's class). Each carries a ready
  `PracticeCreate` body (`practice`) and, for strengthen, an `ExplainRequest` (`revise`). Finishing a
  practice of the same place marks it `done` (`recommendations.mark_done`).
- **Practice for one topic**: `PracticeCreate.topic_id` (one place at most, as before); the bank
  filters by topic, the writer gets the topic's text first, and new questions are filed under it.
- New endpoints: `GET /students/{id}/mastery`, `GET /students/{id}/recommendations` (docs/03 §3.6).
  New tables: `student_mastery`, `recommendations`; new column `practice_sessions.topic_id`
  (docs/02 §2.5).

### Known issues

- **No AI provider has been tried with a real key yet.** The plan is Groq's free plan: add the key,
  run `pytest -m live` first, then try Explain and a small practice. Expect: open models write
  weaker Hindi / Hinglish and maths than Claude (the independent review drops wrong questions, so a
  practice may get fewer); the free plan allows only a few thousand tokens a minute, so a request
  with a full 6,000-token passage budget may be refused as too large (HTTP 413 in the log). If so,
  lower `PASSAGE_BUDGET` in `practice_service.py` or the output budget for Groq.
- Practice from a recommendation needs unseen saved questions at that place and difficulty;
  otherwise it needs the AI.
- **Recommendations are fixed for the day.** If a child fixes a weak topic in the morning, its
  "strengthen" item stays (it turns `done` only when a practice of that place is finished) until the
  next day's list. There is no "dismiss" yet.
- Answers given before Step 7 are not in mastery until the learner answers again in that area (then
  the area is worked out from all its history). The demo data has no answers, so nothing is lost there.
- The reasons are English sentences built from fixed wording (translated screens: Step 11).
- **Node.js on this machine is still v21.5.0**: the site and `next build` run, but Vitest does not
  start (it needs Node ≥ 22). Install the Node 24 LTS macOS installer from nodejs.org.
- Unchanged: the upload route does not renew tokens; `E2E…` children can be left behind by an
  interrupted browser run; `npm audit` (17 moderate, one ESLint dependency); no rate limiting, token
  revocation or security headers yet (Step 12).

### What Step 8 needs to know

- Step 8 is **backend**: mock tests (sections, timing, a result report) and the study planner
  (plans that update with performance). Planned tables: `mock_tests`, `mock_test_questions`,
  `test_attempts`, `study_plans`, `study_plan_items` (docs/02 §2.7). Check the class profile:
  `practice_tests` (Class 3+), `chapter_tests` (6+), `timed_tests` and `full_mock_tests` (9+).
- **Questions**: reuse the question bank and the writer (`practice_service._from_bank`,
  `generator.generate`, `to_question`); a test place can be a book, chapter, topic or exercise.
- **Mastery should count test answers.** `mastery.record_answer` reads `question_attempts` through
  `first_answers`, which groups by `practice_session_id`. Either store test answers there too (one
  attempt per question) or teach `first_answers` about tests; then call `record_answer` per answer.
- **Study plans** can build on `student_mastery` (weak areas, levels, last practised) and on the
  recommendation order; `recommendations.today()` gives the India-time day.
- Frontend hooks waiting for Step 9: "Recommended for You" on the learner home, strong areas / needs
  attention and **Start Recommended Practice** (post `practice` as-is) on the parent dashboard.
  Every new page that loads data needs its own `loading.tsx` (see `frontend/app/loading.tsx`).
