# EduGuide AI

**Turn your child's books into a personalized AI tutor.**
An AI personal tutor, practice generator, study planner and parent assistant for Indian students
from Nursery to Class 12.

> **Build status: Step 2 of 12 is complete** — the blueprint, the backend foundation, and
> uploading and reading books.
> See [ROADMAP.md](ROADMAP.md) for the full plan.

## What works today

- Sign-up and sign-in for **parents** and **students** (email + password)
- Parents add children; the **class is chosen first** and decides which streams and goals are allowed
- **Class-aware rules** for all 15 classes (Nursery, LKG, UKG, Class 1–12), served by the API
- **Child mode**: a parent hands the device to one child, who then sees only their own things
- Strict separation between families: one parent can never see another parent's children
- **My Books**: upload PDF, Word (.docx) and text files into a book. The file type is checked from
  the content; size, page count, passwords and duplicates are checked at once
- Books are read in the background with a progress checklist: text (with OCR for scanned pages
  when Tesseract is installed), **chapters, topics, worked examples, exercises and each exercise
  question**, summaries — in English and Hindi books — then cut into labelled pieces ready for
  search in Step 3
- Parents can rename chapters; exercise questions are listed exactly as printed, with book,
  chapter, exercise and page
- Database migrations, demo data (including a sample book), automatic API documentation, 188 automated tests

## Run it on your computer

You need **Docker Desktop** and **Python 3.11 or newer**.

**1. Start the database** (from the project folder):

```bash
docker compose up -d
```

**2. Set up the backend:**

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment —

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

Then:

```bash
pip install -r requirements-dev.txt
python -m scripts.init_env        # creates backend/.env with a random secret
alembic upgrade head              # creates the database tables
python -m scripts.seed            # optional: demo accounts
uvicorn app.main:app --reload
```

**3. Open the API documentation:** <http://localhost:8000/docs>

Try it: run `POST /api/v1/auth/login` with a demo account, copy the `access_token`, press
**Authorize**, paste it, then call `GET /api/v1/students`.

To try a book: `GET /api/v1/books` shows the sample book; `POST /api/v1/books` creates a new one,
and `POST /api/v1/books/{book_id}/documents` (press **Try it out**, choose a PDF) uploads a file.
Follow it with `GET /api/v1/documents/{id}`, then open `GET /api/v1/books/{book_id}/chapters`.

### Optional: reading scanned books (OCR)

Text PDFs, Word and text files work without this. For scanned or photographed books, install the
free Tesseract program with the Hindi language pack, then set `OCR_PROVIDER=tesseract` in
`backend/.env` and restart the API:

```bash
brew install tesseract tesseract-lang                 # macOS
sudo apt install tesseract-ocr tesseract-ocr-hin      # Ubuntu / Debian
```

Without it, a fully scanned book shows the message *"This looks like a scanned or photographed
book…"* instead of empty results.

### Demo accounts (created by `python -m scripts.seed`)

| Email | Password | Who |
|---|---|---|
| `parent@example.com` | `DemoParent123` | Sunita Sharma — children: Aarav (Class 7, CBSE) and Anaya (UKG) |
| `student@example.com` | `DemoStudent123` | Kabir Verma — Class 12 Science, preparing for JEE |

These passwords are public; the seed script refuses to run when `ENVIRONMENT=production`.

## Run the tests

From `backend/` with the virtual environment active:

```bash
pytest                 # everything (the database must be running)
pytest tests/unit      # only the tests that need nothing running
ruff check .           # code style
```

The API tests use a separate database (`eduguide_test`), rebuild it from the migrations on every run,
and roll back after every test — your real data is never touched.

## Where things are

| Folder | What is in it |
|---|---|
| [`docs/`](docs/) | The blueprint: architecture, database, API, screens, RAG pipeline, LLM interfaces, class rules |
| `backend/app/core` | Settings, database connection, security, error format, shared vocabulary |
| `backend/app/models` | Database tables |
| `backend/app/schemas` | Shapes of API requests and responses |
| `backend/app/auth` | Sign-up, sign-in, tokens, child mode |
| `backend/app/class_profiles` | The rules for each class — the heart of "class-aware AI" |
| `backend/app/services` | Business logic; the only place that reads or writes family data |
| `backend/app/rag/ingestion` | Reading books: file checks, text, OCR, structure, chunks |
| `backend/app/storage` | Where uploaded files are kept (private folder `backend/storage/`, git-ignored) |
| `backend/app/api` | HTTP routes |
| `backend/alembic` | Database migrations |
| `backend/tests` | Automated tests |
| `backend/app/llm`, `question_generation`, `adaptive_learning`, `analytics` | Empty until their step (see the roadmap) |
| `frontend/` | Empty until Step 5 |

## Everyday commands (run inside `backend/`)

| I want to… | Command |
|---|---|
| Start the API | `uvicorn app.main:app --reload` |
| Apply database changes | `alembic upgrade head` |
| Create a migration after changing a model | `alembic revision --autogenerate -m "what changed" --rev-id 0002` |
| Undo the last migration | `alembic downgrade -1` |
| Wipe all local data and start again | `docker compose down -v` then `docker compose up -d` (from the project folder) |

## If something goes wrong

| Problem | What to do |
|---|---|
| `JWT_SECRET_KEY is missing or shorter than 32 characters` | Run `python -m scripts.init_env` inside `backend/`. |
| `Connection refused` / cannot reach the database | Is Docker running? `docker compose ps` should show `db` as *healthy*. |
| Port 5432 is already in use | Another PostgreSQL is running. Change the port in `docker-compose.yml` (see the comment there) and in `backend/.env`. |
| A book stays `failed` with `scanned_document` | It has no text layer. Install Tesseract (see above), set `OCR_PROVIDER=tesseract`, restart, then `POST /api/v1/documents/{id}/retry` |
| Upload answers `413` | The file is over `MAX_UPLOAD_MB` (50 MB). Split the book, e.g. one PDF per chapter — they can all go into the same book |
| `database "eduguide_test" does not exist` when running tests | The database volume was created before this project's init script existed. Run `docker compose down -v` and `docker compose up -d`. |
| PowerShell refuses to run `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `cmd` with `activate.bat`. |

Not using Docker? A PostgreSQL you install yourself also works (this step was tested on
PostgreSQL 16): create a user `eduguide` with password `eduguide` and the databases `eduguide` and
`eduguide_test`. From Step 3 the server also needs the `pgvector` extension.
