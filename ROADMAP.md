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
| **10** | ⏭ | **Previous-year paper analysis, misconception detection, JEE / NEET / CUET modes.** | `backend/app/analytics` · `backend/app/adaptive_learning` · `backend/app/question_generation` | 1 Previous-year analysis · 2 Misconception detection · 3 Competitive exam modes |
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

## Notes for next step

*Rewritten at the end of every step. Last updated: end of Step 9.*

### Where things stand

- Steps 1–9 are done. Backend: 343 tests pass (live tests skipped), `ruff` clean. Frontend: 110 unit
  tests and 13 browser journeys (desktop + phone, twice in a row) pass; `lint`, `typecheck`,
  `format:check` and `build` are clean.
- Checked in a real browser (the production build, the API with the AI off): a chapter test from the
  chapter page, **Start now with …**, answers, submit, the report for the child and the parent; a
  study plan for a new family, today's tasks, **Start Recommended Practice**, the assistant and the
  tutor without the AI. The screens were also looked at on a desktop and a phone (dashboard, test
  screen, report, plans, Create Test, assistant, tutor).
- **Not tried on a real model in Part B**: the assistant and tutor screens with the AI on (Groq's
  free daily allowance had run out in Part A). Part A's stricter rung instructions and the removal of
  "(see [S1])" citations are still untried on a real model too. Worth one check with `LLM_PROVIDER=groq`.
- **Node.js on this Mac**: the default `node` is still 21.5. Node 24.22.2 (the official prebuilt,
  checksum-checked) is in `~/.local/node-v24`; run frontend commands as
  `PATH="$HOME/.local/node-v24/bin:$PATH" npm …`. Homebrew here runs under Rosetta on macOS 27 and
  compiles Node from source, so it was not used.

### What Step 9 built (frontend)

- **Shared pieces.** `answer-input.tsx`: every answer format, `answerFor()` and `draftOf()` (a saved
  answer back as a draft) — practice and tests use it. `start-button.tsx` (was QuickPractice): any
  Server Action plus ready-made fields as hidden inputs (empty ones are left out) — a chapter's
  Practice and Take Test, a recommendation, a plan task. `lib/forms.ts` now holds `Result`,
  `attempt()`, `questionRequestFromForm()` and `questionsError()` shared by practice and tests.
  "Soon" is gone (every menu item works).
- **Create Test** (`question-chooser.tsx`, with Create Practice): the kinds the class has
  (`KIND_FEATURE`), chosen in the same GET form as the place; a full mock test picks only a book, a
  chapter test needs a chapter (the button waits for one). An empty number of questions gets the
  usual length; the time limit field exists only with `timed_tests`.
- **The test screen** (`test-player.tsx`): one question at a time, a grid, the section and its marks;
  a choice is saved at once, typing after a 1-second pause, all saves in order; submit sends what is
  still waiting first. The countdown starts from `seconds_left` (the device's clock, not the
  deadline) and submits at 0 — also at once for a sitting reopened after its time ran out. After
  submitting the page shows the report (`test-report.tsx`). A save or a submit that does not get
  through says so and the screen carries on (a dropped save never blocks submitting).
- **Tests and child mode**: `startChildMode(studentId, { practice } | { test })`; for a test the
  sitting is started as the parent first, so a failure changes nothing. A learner's own new test goes
  to `/learn/tests`, where it starts once ready.
- **Plans**: the parent sees every day and can remove the plan; the learner sees today's tasks
  (Start, ✓ Done / Undo) and the days to come. A learn task opens `/learn/concepts/{chapter}?q=&task=`
  and is ticked off once explained. A student who signed up alone makes their own plan
  (`/learn/plan/new`); in child mode the parent does.
- **Dashboard** (`dashboard.tsx`): the week as columns in plain CSS (no chart library); the lighter
  step `--primary-light` was checked with the dataviz validator (one hue, 2.48:1 on the card).
  Strong / needs attention reuse the progress bars. Recommended is also on the learner's home, where a
  weak topic can be revised first. The parent's Progress page adds the recent tests.
- **The assistant and the tutor** (`chat-screen.tsx`, `chat-box.tsx`): a conversation is made with
  its first message; the reply streams through `app/api/chat/[chatId]/messages` and `lib/sse.ts`;
  when a new conversation's first reply is kept, the box resets and opens the conversation's address
  (pages stay mounted with their state). On an error the question goes back into the box. Suggested
  questions never contain the child's name. A conversation of another child (after switching) is not
  shown.
- **proxy.ts** now runs before `/api/chat/…` too (token renewal); only the upload route is left out —
  a unit test checks the matcher (`unstable_doesMiddlewareMatch`).

### Known issues

- **Written answers in a test need the AI to be marked.** With it off, a sitting with a written
  answer cannot be submitted, and a saved answer cannot be emptied (the API refuses an empty answer).
  The browser journey answers only objective questions.
- The server still does not submit a test whose time ran out; the screen does (when it reaches 0,
  or when the sitting is opened again).
- Lists show the first 50 tests and the first 50 conversations (no "older" pages yet). There is no
  endpoint to delete a test.
- A first message that fails leaves an empty conversation in the database (hidden in the list).
- The learner's home reads the whole dashboard for Recommended and today's plan (it also works out
  the week and mastery, which the home does not show).
- Replies are shown as plain text (no Markdown formatting). The youngest home shows recommendations
  without their reasons; the tutor and tests are not in the Nursery–Class 5 menus (docs/04 §4.4).
- Recommendations and plans use only the family's shared books and the learner's own: a temporary
  browser-test child has none, so the plan journey signs up a new family and uploads the sample book.
- **Reading a book can hold the API up for a few seconds** when several are read at once (its
  pure-Python steps run in threads but share the interpreter with the requests). The browser tests
  therefore wait up to 10 seconds per check (`playwright.config.ts`). Step 12's workers move reading
  out of the API process.
- **Running the browser tests next to your own servers:** `npm run test:e2e` reuses a frontend already
  on port 3000 and the API on 8000. With the AI on, the recommended-practice, assistant and tutor steps
  then call it. To keep the allowance, start the API with `LLM_PROVIDER=none` for the tests.
- Unchanged: the plan is made again only once a day; recommendations are fixed for the day; reasons are
  English sentences; answers given before Step 7 enter mastery only when the learner answers again in
  that area; the upload route does not renew tokens; `npm audit` (17 moderate); no rate limiting,
  token revocation or security headers yet (Step 12); Groq's free plan is slow (about 4 minutes for a
  5-question hard practice). No negative marking or JEE / NEET paper patterns yet (Step 10).

### What Step 10 needs to know

- Step 10 is **previous-year paper analysis, misconception detection and JEE / NEET / CUET modes**
  (docs/03 §3.9 plans `POST /books/{id}/paper-analysis`). Class profiles already carry
  `previous_year_questions` and `competitive_exam_modes`, and learner profiles the goal (`jee`,
  `neet`, `cuet`).
- **Papers**: question papers can already be uploaded as books (`material_type`); reading finds each
  exercise question. Test papers are built in `question_generation/paper.py` (sections, marks, time);
  exam patterns with negative marking would go there and in the marking of `mock_test_service`.
- **Screens**: Create Test's kinds come from `KIND_FEATURE` in `components/question-chooser.tsx` and
  `copy.testKinds`; papers and reports are drawn from the API's sections and marks, so new sections
  need no screen change. A negative mark would show as it is in the report.
- **Misconceptions**: every answer is a `question_attempts` row (with the response, help used and,
  for written answers, the AI's feedback); mastery lives in `adaptive_learning/mastery.py`; the tutor
  already checks a learner's attempt (`chat/tutor.py`).
- Every new page that loads data needs its own `loading.tsx`; all wording in `frontend/lib/copy.ts`.
