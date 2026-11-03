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
| **9** | ⏭ | **Parent dashboard, test and plan screens, the two assistants.** Parent AI Assistant and Student AI Tutor (hint first, answer last). | `frontend/` · `backend/app/api/v1` | 2 Parent dashboard |

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

## Notes for next step

*Rewritten at the end of every step. Last updated: end of Step 8, plus the Step 9 progress note below.*

### Step 9 in progress: Part A (backend) done — say "continue step 9" for Part B (frontend)

Step 9 was split in two (agreed plan). **Part A is done and tested**: 343 backend tests pass
(`pytest`), `ruff` clean. Commit it before Part B. To update a Step 8 setup: `alembic upgrade head`
(migration 0007), `python -m scripts.seed` (adds the 7 new demo questions; nothing else changes).
This machine's database is already upgraded and seeded.

What Part A added:

```
backend/
├── alembic/versions/0007_chat.py         chat_sessions, chat_messages
├── app/llm/base.py · anthropic_provider.py · groq_provider.py
│                                         stream_text(): chat replies piece by piece (same fallback,
│                                         effort and caching settings as the structured calls)
├── app/analytics/progress.py             week(): the last 7 days (India time)
├── app/schemas/dashboard.py · services/dashboard_service.py · api/v1/dashboard.py
│                                         GET /students/{id}/dashboard (snapshot() is shared)
├── app/chat/tutor.py                     the hint ladder (next_step: code decides the rung) + prompts
├── app/chat/assistant.py                 the parent assistant's prompts and <child_data> facts
├── app/models/chat.py · schemas/chat.py · services/chat_service.py · api/v1/chat.py
│                                         conversations; POST …/messages streams Server-Sent Events
├── app/services/learn_service.py         learner_books(), book_languages(), find_passages() shared
├── app/services/mock_test_service.py     recent_results()
├── app/services/study_plan_service.py    current_plan() (the plan, re-planned if a new day)
├── scripts/demo_questions.py · seed.py   4 short + 3 long Class 7 questions; the seed adds only
│                                         the demo questions not there yet
└── tests/                                test_dashboard, test_chat, test_tutor, test_citations;
                                          streaming in test_llm / test_groq / tests/live
```

Endpoints: docs/03 §3.8. Tables: docs/02 §2.7. How the tutor and the assistant work: docs/06 §6.5.
SSE events: `delta {"text"}`, then `done {"question", "answer"}` (both saved, the answer with
`sources` and the tutor's `rung`) or `error {"code", "message"}` (nothing saved). Errors before the
reply starts are JSON (503 `ai_not_configured`, 422 `insufficient_context`, 404 `chat_not_found`,
403 `parent_required` for a learner opening an assistant conversation).

Checked on the real server with Groq: the dashboard, an assistant answer (first text after 1.7 s),
tutor Hint 1 then — for "just tell me the answer" — Hint 2. After that run the rung instructions
were made stricter ("Not allowed: …", two to four sentences) and citations like "(see [S1])" are
now removed whole; **neither change has been tried on a real model yet**, because Groq's free daily
allowance for `gpt-oss-120b` (200,000 tokens) ran out during the check. It resets over 24 hours.

**Part B — the frontend (the agreed plan):**
- **First, Node 24** (Vitest needs ≥ 22; this Mac has 21.5). Still to be answered: may Claude run
  `brew install node@24` (keg-only: `node` stays 21 and 24 is used only for this project's
  commands), or will you install Node 24 LTS from nodejs.org?
- Menus: Mock Tests, Study Plans, AI Assistant (parent) and Tests, Study Plan, AI Tutor (learner)
  lose "Soon". The tutor stays in the Class 6–12 menus only (docs/04 §4.4).
- Parent: the full dashboard (`GET …/dashboard`: week bars, strong / needs attention, Recommended
  with **Start Recommended Practice** → the practice page with "Start now with …", recent tests,
  today's plan); Mock Tests (list, Create Test, a test with **Start now with {child}** — child mode,
  then `POST /mock-tests/{id}/attempts` as the child — its sittings and reports); Study Plans (the
  plan by day, Make a plan); AI Assistant (conversations, streamed answers with sources, suggested
  questions); the chapter page's **Take Test** (chapter test from Class 6, practice test of the
  chapter in Class 3–5, hidden below); Progress + topics and recent tests.
- Learner: home **Recommended for You** and **Today's plan**; Tests (list, the test screen: timer
  from `deadline` / `seconds_left` for Class 9+, sections, a question grid, `PUT` each answer as
  chosen, auto-submit at 0, `GET /test-attempts/{id}` after a reload, then the report); Study Plan
  (today's tasks with Start and ✓ Done; learn tasks open Learn a Concept with the question filled
  in; a solo student can make a plan); AI Tutor (streamed replies, the rung as a label).
- Streaming: a route handler `app/api/chat/[chatId]/messages/route.ts` passes the backend's stream
  through, like the upload route; include `/api/chat` in the proxy's matcher so tokens are renewed
  (it excludes all of `/api/` today because the upload must not be buffered).
- Tests: unit (the stream reader, the test timer and answers, the report, the plan view, the
  dashboard) and browser journeys (a parent makes a chapter test and the child takes it — answer only
  objective questions, written ones need the AI — then the report; a plan and today's tasks; Start
  Recommended Practice; assistant and tutor say the AI is off). Every new page gets `loading.tsx`;
  all wording in `lib/copy.ts`.
- At the end: docs/04 routes, README, CLAUDE.md "What exists so far", this file (Step 9 ✅).

### Where things stand

- Steps 1–8 are done. Backend: 325 tests pass (live tests skipped), `ruff` clean. The frontend did
  not change in Steps 7 and 8 (its 80 unit tests and 10 browser journeys passed at the end of Step 6).
- Checked on the real server with the demo data (Aarav): a test made from saved questions, an answer
  saved, the test submitted and its report; a two-week plan made and read back. What that run added
  to the demo data was removed again.

### What Step 8 built

- **Mock tests** (docs/03 §3.7). Kinds: `practice` (Class 3+, any one place or all books), `chapter`
  (Class 6+, one chapter), `full_mock` (Class 9+, a book or all books, always timed: about 2 minutes a
  mark). A time limit needs Class 9+. Otherwise `422 test_not_for_class` (`details` says `kind` or
  `duration_minutes`). Default size: practice = the class's usual number, chapter 15, full mock 30;
  capped by the class's maximum.
- **The paper** (`paper.py`): sections A objective (MCQ, true/false, fill blank, assertion-reason,
  case-based; 1 mark), B numerical (2), C short answer (2), D long answer (5), each only where the
  class uses one of its formats; every section gets at least one question, the rest by share. Stored
  in `mock_tests.sections`; each question's section, position and marks in `mock_test_questions`.
- **Questions** come exactly as for practice: `question_bank.from_bank` (never a question the learner
  was given in a practice **or a test** - practice now skips test questions too), then the AI writes
  each section's shortfall in the background (`prepare_test`, resumed at start-up), committing after
  each section so written questions stay in the bank even if a later section fails.
- **A sitting** (`test_attempts`): `POST /mock-tests/{id}/attempts` starts it (or returns the one in
  progress; after a submitted one it is a retake). Answers are saved one by one into `responses`
  (`PUT …/answers/{question_id}`, one atomic `||` update) and can be changed until submitted; refused
  after the deadline + 1 minute (`test_time_over`). No hints/steps in a test.
- **Marking on submit**: exact formats as in practice; written answers by the AI, whose `Grade` now
  also gives `key_points_covered` → that share of the marks, to the nearest half mark. All AI calls
  happen before anything is stored, so a failure leaves the sitting as it was and submit can be sent
  again. Each answer becomes a `question_attempts` row with `test_attempt_id` and `marks`
  (`practice_session_id` is now optional; a check constraint wants exactly one). Mastery is worked out
  again for every area answered, so **tests count for progress, mastery and recommendations**.
  Unanswered questions earn 0 and are not counted. Submitting twice returns the same report.
- **The report**: score / total / percentage, time taken, answered / correct / wrong / unanswered,
  by section, by chapter and topic (weakest first), and every question with the response, marks,
  feedback and the worked solution.
- **Study plans** (one per learner, `study_plans.student_id` unique; a new plan replaces the old one;
  not in child mode, but a child can tick tasks off). Built by rules (`planner.py`), not the AI:
  weak areas first (learn + practise at the lowered level), then each chapter in book order - new:
  learn + practise; below the target: practise, **as many times as it needs** (one per 25 points of
  mastery it lacks, the later ones in rounds through the chapters, so they are spread out); at the
  target: one review at the end. The last day: one test per book - full mock (Class 9+), practice
  test (Class 3–8), none below. Learn 15 minutes, practice 20, a test its length. Final tasks are
  placed backwards from the last day, the rest spread evenly before within `daily_minutes`; what does
  not fit is counted in `unscheduled`.
- **It follows performance**: on the first `GET /students/{id}/study-plan` of a day (India time), past
  pending tasks become `missed`, pending tasks from today on are replaced by a new plan from the
  latest mastery; done / skipped tasks stay and their minutes count. Finishing a practice of a task's
  place, or submitting a whole-book test of its book, marks it `done` (`practice_done`,
  `book_test_done`); learn tasks are ticked with `PATCH /study-plan-items/{id}`.
- Shared now: `QuestionView.of()`, `QuestionRequest` (base of `PracticeCreate` and `MockTestCreate`),
  `Response` (base of `AnswerIn`), `student_service.class_profile()`, `mastery.practice_level()` /
  `right_lately()`, `recommendations.practice_body()` / `revise_body()`, `checking.AnswerShapeError` is
  itself the `422 answer_does_not_fit`.

### Known issues

- **The demo data has only objective questions.** Without an AI key a demo test can only be a
  1-question one (any second question falls in the short-answer section). Step 9's browser tests
  will need a few short- and long-answer demo questions in `scripts/demo_questions.py`.
- **The server does not submit a test when time runs out**; the screen must call `submit` when the
  timer reaches 0. A sitting left in a closed tab stays `in_progress` with `seconds_left: 0`, and
  starting the test again returns it: the screen should then submit it and show the report.
- **Marking runs inside the submit request**, one AI call per written answer, one after another. On
  the Groq free plan a paper with many written answers is slow and can hit the per-minute limit
  (`503 ai_unavailable`; the answers are kept, submit again).
- The plan is made again only once a day: practice finished today shows in tomorrow's plan, and a
  task already planned for later stays until then. Plans work per chapter (per topic only for weak
  topics); the minutes per task are fixed estimates. A replaced plan is gone, with its history.
- There is no endpoint to delete a test (they stay in the list).
- No negative marking or JEE / NEET paper patterns yet (Step 10).
- Unchanged from Step 7: recommendations are fixed for the day; answers given before Step 7 enter
  mastery only when the learner answers again in that area; reasons are English sentences built from
  fixed wording; **Node.js on this machine is still v21.5.0** (Vitest needs ≥ 22); the upload route
  does not renew tokens; `E2E…` children can be left behind by an interrupted browser run (the dev
  database has many); `npm audit` (17 moderate); no rate limiting, token revocation or security
  headers yet (Step 12). Groq free plan: about 4 minutes for a 5-question hard practice.

### What Step 9 needs to know

- Step 9 is **frontend + two assistants**: the parent dashboard (`GET /students/{id}/dashboard`,
  planned), the test and plan screens, the Parent AI Assistant and the Student AI Tutor (hint first,
  answer last; `chat_sessions`, `chat_messages`, docs/02 §2.8).
- **Test screens** (docs/04): `/parent/tests` (`GET /students/{id}/mock-tests`, cursor pages, each with
  its sittings), `/parent/tests/new` (kinds and the timer shown by the profile's `practice_tests`,
  `chapter_tests`, `full_mock_tests`, `timed_tests`), `/parent/tests/[testId]` (poll while `preparing`,
  then the sittings and their reports); `/learn/tests` and `/learn/tests/[attemptId]`: start with
  `POST /mock-tests/{id}/attempts`, show the countdown from `deadline` / `seconds_left`, `PUT` each
  answer as it is chosen, `GET /test-attempts/{id}` after a reload, submit at 0 or on the button, then
  show `TestReport`. The chapter page's **Take Test**: `kind: "chapter"` from Class 6, a `practice` test
  with `chapter_id` in Class 3–5; hidden for Nursery–Class 2.
- **Plan screens**: `/parent/plans` (`GET /students/{id}/study-plan`; `404 study_plan_not_found` = no
  plan yet) and `/parent/plans/new` (exam date, minutes a day, target, chapters); `/learn/plan` shows
  today's day of the plan: each task's `practice` / `revise` / `test` body goes as-is to
  `POST /practice/sessions` / `POST /learn/explain` / `POST /mock-tests`; a learn task is ticked off
  with `PATCH` after the explanation. Show `unscheduled` as "Not everything fits: add minutes a day or
  choose fewer chapters".
- Frontend hooks still waiting from Step 7: "Recommended for You" on the learner home, strong areas /
  needs attention and **Start Recommended Practice** on the parent dashboard.
- Every new page that loads data needs its own `loading.tsx`; all wording in `frontend/lib/copy.ts`
  (parent words: docs/04 §4.5).
