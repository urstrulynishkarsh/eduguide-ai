# EduGuide AI — Build Roadmap

The project is built in 12 steps. Every step ends with something that **runs and is tested**,
and each step fills specific folders, so you always know where the new code is.

Status: ✅ done · ⏭ next · ⬜ later

## Phase 1 — Core MVP

| Step | Status | What you get | Folders it fills | MVP items in the spec (§46) |
|---|---|---|---|---|
| **1** | ✅ | **Blueprint + backend foundation.** Design documents, database, sign-up / sign-in, parent and student roles, class selection, child profiles, class-aware rules, child mode. | `docs/` · `backend/app/core` · `models` · `schemas` · `auth` · `class_profiles` · `services` · `api` · `backend/alembic` · `backend/tests` | 1 Authentication · 2 Roles · 3 Class selection · 4 Student profile |
| **2** | ✅ | **Upload and read books.** Upload PDF / DOCX / TXT safely, read the text (OCR for scanned pages), find chapters, exercises and questions, cut the book into labelled pieces, library API. | `backend/app/rag/ingestion` · `backend/app/storage` · `backend/app/services` · `backend/app/api/v1` · new tables: `documents`, `books`, `chapters`, `topics`, `exercises`, `document_chunks` | 5 Upload · 6 Parsing · 7 Chapter detection · 8 Chunking |
| **3** | ⏭ | **Search inside books + AI connection.** Embeddings, vector index, filtered retrieval (class / subject / chapter / exercise), reranking, context with source citations, and the swappable LLM layer. | `backend/app/llm` · `backend/app/rag` | 9 Embeddings · 10 Vector database · 11 RAG retrieval |
| **4** | ⬜ | **Practice engine.** Class-aware question generation, automatic checking and regeneration, hints → steps → answer, practice sessions, recording attempts, basic performance numbers. | `backend/app/question_generation` · `backend/app/analytics` · `backend/app/services` | 12 Question generation · 13 Solutions · 15 Basic performance tracking |
| **5** | ⬜ | **Frontend foundation.** Next.js app, design system with the four age-based layouts, landing page, sign-up / sign-in, onboarding, child mode. | `frontend/` | screens for items 1–4 |
| **6** | ⬜ | **Frontend MVP.** My Books and upload with progress, Create Practice, the student practice screen (including the picture-based one for Nursery–Class 2), basic progress. **The MVP works end to end here.** | `frontend/` | 14 Student practice interface |

## Phase 2

| Step | Status | What you get | Folders it fills |
|---|---|---|---|
| **7** | ⬜ | **Adaptive learning.** Mastery per topic, difficulty that follows performance, weak-topic detection, daily recommendations. | `backend/app/adaptive_learning` · `backend/app/analytics` |
| **8** | ⬜ | **Mock tests and study planner** (backend). Sectioned, timed tests with a result report; study plans that update with performance. | `backend/app/services` · `backend/app/api/v1` |
| **9** | ⬜ | **Parent dashboard, test and plan screens, the two assistants.** Parent AI Assistant and Student AI Tutor (hint first, answer last). | `frontend/` · `backend/app/api/v1` |

## Phase 3

| Step | Status | What you get | Folders it fills |
|---|---|---|---|
| **10** | ⬜ | **Previous-year paper analysis, misconception detection, JEE / NEET / CUET modes.** | `backend/app/analytics` · `backend/app/adaptive_learning` · `backend/app/question_generation` |
| **11** | ⬜ | **Languages, gamification, advanced analytics.** Hindi / Hinglish screens, structure for more Indian languages, streaks / XP / badges, richer charts. | `frontend/` · `backend/app/analytics` |
| **12** | ⬜ | **Production hardening.** Rate limiting, background workers on Redis, Docker images, CI, monitoring, a security review. | `infra/` · whole project |

Note: questions and explanations in **Hindi and Hinglish** already work from Step 4 (the language is
part of every request to the AI). Step 11 adds translated screens and further languages.

## How every step is delivered

1. You get one zip with the **whole project so far**. Extract it over your project folder.
2. Run `alembic upgrade head` in `backend/` to apply any new database changes.
3. Run `pytest` in `backend/` — everything should pass.
4. Commit to git (`git add -A && git commit -m "Step N"`), so each step is a clean checkpoint.

## What is inside Step 1

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
├── frontend/                  (Step 5)
└── backend/
    ├── .env.example           every setting, explained
    ├── requirements.txt       pinned versions
    ├── alembic/               database migrations
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
        ├── rag/               (Steps 2-3)
        ├── llm/               (Step 3)
        ├── question_generation/   (Step 4)
        ├── adaptive_learning/     (Step 7)
        ├── analytics/         (Steps 4, 9, 11)
        └── utils/
```

## What Step 2 added

```
backend/
├── alembic/versions/0002_…py     books, documents, chapters, topics, exercises, document_chunks
├── scripts/sample_data/           a sample chapter the seed script puts in "My Books"
└── app/
    ├── storage/                   FileStorage interface + local folder (uploads are private)
    ├── core/tasks.py              background TaskQueue (in-process now, Redis in Step 12)
    ├── core/middleware.py         + upload / request size limit
    ├── models/library.py          the six new tables
    ├── schemas/library.py         request / response shapes
    ├── services/library_service.py    books, chapters, exercises - and who may see them
    ├── services/document_service.py   upload, retry, remove, resume after a restart
    ├── api/v1/books.py · documents.py · chapters.py
    └── rag/
        ├── ocr.py                 OCRProvider + Tesseract adapter
        └── ingestion/             check file -> read text -> clean -> find structure -> chunks
```

After extracting: `pip install -r requirements-dev.txt` (new libraries), `alembic upgrade head`
(migration 0002), `pytest`, and optionally `python -m scripts.seed` for the sample book.

