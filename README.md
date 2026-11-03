# EduGuide AI

**Turn your child's books into a personalized AI tutor.**
An AI personal tutor, practice generator, study planner and parent assistant for Indian students
from Nursery to Class 12.

> **Build status: Step 8 of 12 is complete.** The MVP works end to end: a parent signs up, adds a
> child, uploads a book, creates practice from a chapter or exercise and hands the device over;
> the child practises (with hints, steps and answers) in a layout made for their age, and both
> see the progress. The API also knows each child's mastery of every topic, moves the difficulty
> with their results and recommends what to do next (Step 7), and runs sectioned, timed mock tests
> with a result report and study plans that follow performance (Step 8). Their screens, the parent
> dashboard and the two AI assistants come next (Step 9).
> See [ROADMAP.md](ROADMAP.md) for the full plan.

## What works today

**In the browser** (<http://localhost:3000>)

- Landing page, sign-up ("Who are you? Parent / Student") and sign-in
- **Add Child** with the class first: stream, goals and subject suggestions follow the class
- **Who is learning today?** — the parent taps a child and hands over the device (child mode).
  Leaving child mode asks for the parent's password
- **My Books**: upload a PDF, Word or text file with a progress bar, then watch it being read
  (✓ Reading your book … ✓ Getting practice ready). Chapters, topics, and exercise questions exactly
  as printed, with page numbers
- **Chapter page**: Learn · Practice · Exercise Questions · Generate Questions (Take Test: Step 9)
- **Create Practice**: from all books, a book, a chapter or an exercise; number, difficulty,
  question type and language, limited by the child's class. Then **Start now with Aarav**
- **Practice screen**: one question at a time, every answer format, **Hint → Show Steps → Show
  Answer**, "Explain simply / like I'm 10 / in Hindi / in Hinglish", and where each generated
  question comes from. Nursery–Class 2: big picture cards, a number pad, "try again", stars and no marks
- **Learn a Concept** and **Progress** (My Stars for the youngest); a basic parent **Dashboard**
- A child switcher at the top of the parent area; Children and Settings as before
- The student area in **four layouts** chosen by the class: big and playful for Nursery–Class 2,
  roomy for Class 3–5, a regular app for Class 6–8, a compact academic one for Class 9–12. Works on
  phones, tablets and computers

**In the API**

- Sign-up and sign-in for **parents** and **students** (email + password)
- Parents add children; the **class is chosen first** and decides which streams and goals are allowed
- **Class-aware rules** for all 15 classes (Nursery, LKG, UKG, Class 1–12), served by the API
- **Child mode**: a parent hands the device to one child, who then sees only their own things
- Strict separation between families: one parent can never see another parent's children
- **My Books**: upload PDF, Word (.docx) and text files into a book. The file type is checked from
  the content; size, page count, passwords and duplicates are checked at once
- Books are read in the background with a progress checklist: text (with OCR for scanned pages
  when Tesseract is installed), **chapters, topics, worked examples, exercises and each exercise
  question**, summaries — in English and Hindi books — then cut into labelled pieces and made
  searchable by meaning (English, Hindi and Hinglish questions find English or Hindi text)
- Parents can rename chapters; exercise questions are listed exactly as printed, with book,
  chapter, exercise and page
- **Explain this** (`POST /api/v1/learn/explain`): explains a concept from the child's own books at
  the child's class level — normal, simpler, "like I'm 10", in Hindi or in Hinglish — with the book,
  chapter and page it used. When the books don't cover it, it says so instead of guessing
- **Create Practice** (`POST /api/v1/practice/sessions`): from an exercise, a topic, a chapter, a
  book or all of the child's books — number, difficulty (easy / medium / hard / mixed), type (MCQ, numerical,
  … or mixed) and language. Questions follow the class rules (picture questions for the youngest,
  board and JEE / NEET styles for the oldest), are checked by a second, independent AI solve before
  anyone sees them, are always marked "generated", and are saved and reused
- Doing practice: answers are marked (written answers by the AI tutor); **Hint → Show Steps → Show
  Answer**; "explain this simply / like I'm 10 / in Hindi / in Hinglish"; every answer is recorded
  with the time and help used
- **Progress** (`GET /api/v1/students/{id}/progress`): questions answered, accuracy, time, hints,
  accuracy by chapter and topic, recent sessions
- **Mastery** (`GET /api/v1/students/{id}/mastery`): for every topic practised, mastery, accuracy
  and confidence, *strong* / *learning* / *needs attention*, and the difficulty for the next practice,
  which goes up above 85 % right and down below 60 % (Class 6–12; gentle repetition for the youngest)
- **Recommended for You** (`GET /api/v1/students/{id}/recommendations`): up to three things to do
  today, each with its reason and a ready Create Practice request — strengthen a weak topic (revise,
  then easier questions), continue one, review one not practised for a week, or start a new chapter
- **Mock tests** (`POST /api/v1/mock-tests`): practice tests from Class 3, chapter tests from Class 6,
  full mock tests and time limits from Class 9. A paper in board-style sections (objective, numerical,
  short and long answers, with marks), answers saved as the child goes and changeable until submitted,
  then marked — written answers with part marks for the key points covered — and a **result report**:
  score, sections, the weakest chapters and topics, and every question with its solution. Test
  answers count towards progress and mastery
- **Study planner** (`POST /api/v1/study-plans`): from today to the exam within the minutes a day —
  weak topics first, new chapters (learn, then practise), more practice below the target score,
  reviews and a test of each book at the end. Planned again every morning from the latest mastery;
  finishing a practice or a test ticks its task off
- Database migrations, demo data (including a sample book), automatic API documentation, 324 automated tests

## Run it on your computer

You need **Docker Desktop**, **Python 3.11 or newer** and **Node.js 22 or 24 (LTS)**.

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

**3. Start the frontend** (in a second terminal, from the project folder):

```bash
cd frontend
npm install
cp .env.example .env.local        # where the API is; the default is fine
npm run dev
```

Open <http://localhost:3000> and sign in with a demo account (below), or create your own.

**4. Or explore the API directly:** <http://localhost:8000/docs>

Try it: run `POST /api/v1/auth/login` with a demo account, copy the `access_token`, press
**Authorize**, paste it, then call `GET /api/v1/students`.

To try a book: `GET /api/v1/books` shows the sample book; `POST /api/v1/books` creates a new one,
and `POST /api/v1/books/{book_id}/documents` (press **Try it out**, choose a PDF) uploads a file.
Follow it with `GET /api/v1/documents/{id}`, then open `GET /api/v1/books/{book_id}/chapters`.

### Switching on the AI (Groq or Claude)

Everything except **Explain this**, writing new practice questions and marking written answers
works without it (saved questions can still be practised). Choose one provider, add its two lines
to `backend/.env` and restart the API:

| Provider | Cost | Key from | Lines for `backend/.env` |
|---|---|---|---|
| **Groq** (open models: gpt-oss) | free plan, with low limits per minute and per day | https://console.groq.com/keys | `LLM_PROVIDER=groq` · `GROQ_API_KEY=gsk_...` |
| **Claude** | paid per use | https://platform.claude.com | `LLM_PROVIDER=anthropic` · `ANTHROPIC_API_KEY=sk-ant-...` |

The models are chosen for you (`LLM_MODEL_FAST` / `_DEFAULT` / `_STRONG` override them). Check that
your key works with `pytest -m live`. **On Groq's free plan, ask for 5 questions at a time:** the plan
allows 8,000 tokens a minute, so questions are written 3 at a time with waits in between - a practice
of 5 takes about 4 minutes, and a hard one may come back with fewer questions (the independent check
drops the wrong ones). When the day's allowance is used up, the app says "busy, try again".

The search model runs on your computer and needs no key. It is downloaded once (~1 GB, into
`backend/storage/models/`) the first time a book is read.

**Coming from Step 2?** After `alembic upgrade head`, run `python -m scripts.reembed` once so books
you uploaded before become searchable.

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
| `parent@example.com` | `DemoParent123` | Sunita Sharma — children: Aarav (Class 7, CBSE, a sample Maths chapter) and Anaya (UKG, a sample picture book in Hindi) |
| `student@example.com` | `DemoStudent123` | Kabir Verma — Class 12 Science, preparing for JEE |

These passwords are public; the seed script refuses to run when `ENVIRONMENT=production`.

**Practice without an AI key.** The seed also puts hand-written demo questions in the question
bank: 12 for Aarav's Maths chapter (Hinglish) and 10 picture, counting and matching questions for
Anaya's book (Hindi). A child is never given the same question twice, so they last for one or two
practices each; after that, new questions need the AI. Already seeded before Step 6? Run
`python -m scripts.seed` again: it adds only what is missing.

## Run the tests

From `backend/` with the virtual environment active:

```bash
pytest                 # everything (the database must be running); no AI calls, no model download
pytest tests/unit      # only the tests that need nothing running
pytest -m live         # real calls to Groq and/or Claude, whichever keys are in .env
ruff check .           # code style
```

The API tests use a separate database (`eduguide_test`), rebuild it from the migrations on every run,
and roll back after every test — your real data is never touched.

From `frontend/`:

```bash
npm test               # unit tests (nothing needs to be running)
npm run test:e2e       # whole journeys in a real browser: needs the database and the API running.
                       # First time only: npx playwright install chromium
npm run lint && npm run typecheck && npm run format:check
```

The browser tests sign up new accounts (`…@example.com`) in your development database each run.
The practice journeys use the demo family (run `python -m scripts.seed` once): each adds a
temporary child, practises with the demo questions, and removes the child again.

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
| `backend/app/adaptive_learning` | Mastery per topic, difficulty that follows results, daily recommendations |
| `frontend/app` | The screens (Next.js pages): public, onboarding, `parent/`, `learn/` |
| `frontend/components`, `frontend/lib` | Shared pieces, the wording of every screen (`lib/copy.ts`), sessions, calls to the API |

## Everyday commands (run inside `backend/`)

| I want to… | Command |
|---|---|
| Start the API | `uvicorn app.main:app --reload` |
| Apply database changes | `alembic upgrade head` |
| Create a migration after changing a model | `alembic revision --autogenerate -m "what changed" --rev-id 0007` (the next free number) |
| Undo the last migration | `alembic downgrade -1` |
| Make every book searchable again (after an upgrade or a search-model change) | `python -m scripts.reembed` |
| Measure search quality on the sample book | `python -m scripts.eval_retrieval` |
| Wipe all local data and start again | `docker compose down -v` then `docker compose up -d` (from the project folder) |

## If something goes wrong

| Problem | What to do |
|---|---|
| `JWT_SECRET_KEY is missing or shorter than 32 characters` | Run `python -m scripts.init_env` inside `backend/`. |
| `Connection refused` / cannot reach the database | Is Docker running? `docker compose ps` should show `db` as *healthy*. |
| Port 5432 is already in use | Another PostgreSQL is running. Change the port in `docker-compose.yml` (see the comment there) and in `backend/.env`. |
| A book stays `failed` with `scanned_document` | It has no text layer. Install Tesseract (see above), set `OCR_PROVIDER=tesseract`, restart, then `POST /api/v1/documents/{id}/retry` |
| Explain answers `503 ai_not_configured` | Switch on the AI (see above) and restart the API |
| Explain answers `503 ai_unavailable` | The log says why: a wrong key, no internet, or Claude busy (try again in a minute) |
| A practice stays `failed` with `generation_failed` | The AI could not write questions that passed the checks for that place; try another chapter or `mixed` type. The log shows the reasons |
| Create Practice says *"…writing new ones needs the AI, which is not switched on yet"* | The saved questions for that choice are used up (or there are none for a new book). Switch on the AI (see above), or try another chapter, fewer questions or `Mixed` |
| A browser practice test fails with *"You can add up to 10 children"* | Interrupted test runs left temporary children (`E2E…`) in the demo family: remove them in the parent area under Children |
| Create Practice answers `422 question_type_not_for_class` | That question type is not used for the child's class (e.g. numerical before Class 9); use `mixed` |
| Explain answers `422 insufficient_context` | The child's books for that class don't cover the question; upload the chapter, or choose the book with `book_id` |
| Upload answers `413` | The file is over `MAX_UPLOAD_MB` (50 MB). Split the book, e.g. one PDF per chapter — they can all go into the same book |
| `database "eduguide_test" does not exist` when running tests | The database volume was created before this project's init script existed. Run `docker compose down -v` and `docker compose up -d`. |
| The website says *"We can't reach EduGuide right now"* | The API is not running: start it with `uvicorn app.main:app --reload` in `backend/` |
| `npm install` or `npm run dev` fails on an old Node.js | Install Node.js 22 or 24 LTS from nodejs.org (`node --version` to check) |
| PowerShell refuses to run `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `cmd` with `activate.bat`. |

Not using Docker? A PostgreSQL you install yourself also works (this step was tested on
PostgreSQL 16): create a user `eduguide` with password `eduguide` and the databases `eduguide` and
`eduguide_test`. From Step 3 the server also needs the `pgvector` extension.
