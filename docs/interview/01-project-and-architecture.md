# 1. The project and its architecture

## 1.1 The problem

- Indian school students learn from **their own textbook** (NCERT, a state board, a private
  publisher). Generic practice apps don't match the book, the board or the child's level.
- Ages range from 3 (Nursery) to 18 (Class 12, JEE / NEET). A Nursery child and a JEE aspirant
  need completely different questions, explanations and screens.
- Families often **share one phone**, and young children have no email address.
- Books arrive as messy PDFs: scanned pages, old Hindi fonts that extract as gibberish, and one
  PDF per chapter (NCERT's format).
- Many families speak **Hinglish** (Hindi written in Latin letters) even when the book is in
  English or Hindi.

**The goal is not a chatbot.** It is a loop that runs for every child and improves each time:

```
LEARN → PRACTICE → ASSESS → ANALYZE → FIND WEAKNESS → PERSONALIZE → PRACTICE AGAIN
```

## 1.2 Who uses it

| User | How they use it |
|---|---|
| **Parent** | Signs up, adds children, uploads books, creates practice and tests, sees the dashboard, asks the AI assistant "how is my child doing?" |
| **Child** (no login) | Uses the app in **child mode**: the parent taps the child's profile and hands over the device. The session can only act as that child. Only the parent PIN ends it |
| **Solo student** | An older student who signs up alone and owns their own data |

There is no admin role on purpose: nobody at the company needs to read a family's data.

## 1.3 What it does (the short list)

- Upload a book → chapters, topics, worked examples, exercises and each exercise question, with
  page numbers, in English and Hindi.
- **Explain this**: explains a concept from the child's own books at their level, with sources.
  When the books don't cover it, it says so.
- **Create Practice** from a book, chapter, topic or exercise. Every question is checked by an
  independent AI solve and labelled "generated".
- Hint → Show Steps → Show Answer; "explain simply / like I'm 10 / in Hindi".
- **Mastery** per topic, difficulty that follows it, **Recommended for You**.
- **Mock tests** in board-style sections, timed from Class 9, with part marks for written answers.
- **Study plans** made again every morning from the latest mastery.
- **AI Tutor** (hint ladder) and **Parent AI Assistant**, with replies streamed as they are written.
- **Previous-year papers**: where the marks go, trends over years, a test like the papers.
- **Misconception detection**: the AI names a wrong idea the child keeps showing; code decides when
  it is fixed.
- **JEE / NEET / CUET modes** with negative marking.
- Streaks, XP, levels and badges; stars and stickers for the youngest.
- Every screen in **English, Hindi and Hinglish**, and **four layouts** chosen by class.

## 1.4 The architecture

```
 Browser
   │  HTTPS
   ▼
 Caddy (HTTPS, the only public port)
   │
   ▼
 Next.js server ──────────── the only caller of the API; holds tokens in httpOnly cookies
   │  JSON over HTTP
   ▼
 FastAPI app (modular monolith)
   api → services → domain modules (rag, question_generation, adaptive_learning, analytics, chat)
   │            │                         │
   │            ▼                         ▼
   │     PostgreSQL 16 + pgvector     LLMProvider → Claude or Groq
   │     (data, vectors, keyword index)
   ▼
 Redis 8 ──► worker (python -m app.worker): reads books, writes questions, analyses papers
```

### Why a modular monolith

**The need:** one developer, many features, the need to ship and debug fast, and the option to
split later.

**The choice:** one FastAPI application with strict internal modules. Modules call each other
through small interfaces, not through each other's tables. The one piece that needed its own
process (heavy background work) already runs separately as a worker from the same code.

| Alternative | Good at | Why not here |
|---|---|---|
| Microservices | Independent scaling and deploys, separate teams | One developer; adds network calls, distributed transactions, service discovery and many deploys for no gain at this size |
| Serverless functions (AWS Lambda, Vercel) | No servers, pay per call | The 1 GB search model must stay in memory; reading a book takes minutes; chat replies stream; uploads live on disk; cold starts |
| Backend-as-a-service (Supabase, Firebase) | Auth, database and storage out of the box | Child mode is a custom token idea; full control over children's data; Firebase has no relational joins or vector search with tight filters |

**Say it:** "I chose a modular monolith because it is the simplest thing to run and debug. The
modules only talk through interfaces, so the worker already runs as its own process from the
same code. Any module could become a service later without rewriting business logic."

### The seven rules of the codebase (and why each one matters)

| Rule | Why it matters |
|---|---|
| Calls go `api → services → domain modules → models`. Routes never query tables | Business logic and data isolation live in one testable place |
| Services own the transaction and call `commit()` before returning | Data is saved before the response leaves; no half-saved state |
| All family data is read through a service that filters by owner | One rule for isolation, checked by tests |
| External providers sit behind interfaces (LLM, embeddings, OCR, file storage) | Switching provider = one adapter class + an environment variable |
| AI output is data, not text: parsed into Pydantic and validated | The model's mistakes are caught before anyone sees them |
| Anything that depends on age reads the class profile | No `if class > 5` scattered through the code |
| No fake AI in the application; test doubles live only in `tests/` | What runs in production is what was tested |

## 1.5 Class-aware design (the class profile)

- One `ClassProfile` per class (15 of them), built from 6 groups in
  `backend/app/class_profiles/registry.py`.
- It is the **single source of truth** for: language and question complexity, explanation style,
  allowed question formats, maximum solution steps, MCQ option count, session size, which features
  exist (tests, timers, adaptive difficulty…), allowed goals and streams, the AI's guidelines for
  that age, and the screen layout (`ui_mode`).
- The frontend has **no class numbers of its own**: it reads `ui_mode` and feature flags from the API.
- Rules are **configuration, not data**: no migration is needed to change one, and tests check that
  complexity never goes down as the class goes up and that Nursery–Class 2 never gets exam features.

**Say it:** "Instead of `if class > 5` everywhere, there is one profile per class that every part of
the system reads: the prompt, the validator, the test builder and the frontend layout. Changing a
rule is one line, and the tests stop me from making an impossible combination."

## 1.6 Adaptive learning in one paragraph

After every answer, the numbers for that **area** (a topic, or the chapter) are worked out again
from the learner's **last 10 first answers** (retries never inflate them).

- **Accuracy** = share right. Above 85 % the level goes up, below 60 % it goes down and the area
  "needs attention", and in between it stays.
- The level only moves after **at least 5 answers since it last moved**, so it never jumps twice on
  the same evidence (hysteresis).
- **Mastery** (0–1) is a weighted average of credit: 1 for right with no help, minus 0.25 per hint,
  0.25 if the steps or answer were seen first, 0 for wrong. Recent answers count more (each is
  worth 0.85 of the next), and harder questions count more (easy 1, medium 1.5, hard 2).
- **Confidence** = answers ÷ 10, capped at 1.
- Nursery–Class 5 have no levels: they get gentle repetition instead.

**Why rules and not a machine-learning model?** There is no data yet to train on, and parents need
an explanation ("difficulty went down because 4 of the last 10 were right"). The constants sit at
the top of `mastery.py`, ready to tune with real data. Later options: Item Response Theory (IRT),
Bayesian Knowledge Tracing, or Elo-style ratings per question.

## 1.7 Key decisions and why

| Decision | Why |
|---|---|
| Children are profiles inside the parent's account (child mode) | Young children have no email, families share devices, and it gives the simplest strong isolation |
| Email + password first, phone OTP later | OTP needs an SMS provider and costs per message; `auth` is a separate module so it can be added |
| One book can be made of several files | NCERT publishes one PDF per chapter |
| Search model runs on the server | No cost per book, no API key, works for Hindi and Hinglish, children's books never leave the server for embedding |
| No reranker yet | The evaluation already finds the right passage first in 17 of 18 questions; add one when real books show a need |
| Questions are saved per family and reused | A learner never gets the same question twice, siblings reuse checked questions, and AI calls are saved |
| Practice is prepared in the background | Writing and checking 10 questions can take a minute or two; the screen shows "preparing" |
| Nursery–Class 2 never see "wrong" | The class guidelines say: always an invitation to try again |
| Timestamps come from the application clock | PostgreSQL's `now()` is frozen inside a transaction, which broke "order added" |
| Another family's data answers 404, not 403 | Nobody can even learn that a record exists |
| Backend sends codes, not sentences | The screens word every message in any of the three languages |

## 1.8 Hard problems I solved (use these as stories)

Tell each one as **situation → what I did → result**.

1. **Children without logins on a shared phone.**
   Child mode issues a token with the parent's account (`sub`) but the role `student` and the
   child's id (`sid`). It can only act as that one child. Chrome kept auto-filling the parent's
   saved password on the "leave child mode" screen, so a child could get out. I replaced the
   password with a **4-digit parent PIN typed on an on-screen number pad** (buttons, no text field,
   so no password manager can fill it), rate-limited to 5 wrong tries per 15 minutes and 20 a day.

2. **Trusting AI-written questions.**
   A model can write a question with the wrong answer. Each batch goes through deterministic checks
   (format allowed for the class, option count, exactly one correct option, sentence length), then a
   **separate reviewer call solves each question from scratch without seeing the proposed answer**.
   If the two disagree, the reason goes back to the writer for a replacement. After two extra
   rounds, failures are dropped: fewer questions rather than a wrong one.

3. **Hindi PDFs that extract as nonsense.**
   Old Hindi fonts (non-Unicode) produce Latin gibberish when text is extracted. The extractor
   checks script statistics on each page; a page that looks like a legacy font, or has fewer than
   25 letters, is treated as scanned and sent to OCR (Tesseract with the Hindi pack).

4. **No data leaks through vector search.**
   A separate vector store would need its own copy of "who owns what", kept in sync, and filters
   on an approximate index can be applied after the neighbours are found. Here the `ChunkFilter`
   dataclass **requires** the family's id, so a search without it cannot even be written, and the
   filter sits in the same SQL statement as the ranking. Tests try every endpoint as a second family.

5. **A free AI plan with 8,000 tokens a minute.**
   On Groq's free plan, writing 10 questions in one call was refused (HTTP 413). Each provider now
   declares a `RequestSize` (book text and questions per call: Claude 6,000 tokens and 10 questions,
   Groq 1,500 and 3), replies are capped, and the SDK waits out each 429. I measured it: a
   5-question hard practice took 8 requests and about 4 minutes, which the README tells users.

6. **Long work without blocking requests.**
   Reading a 300-page book takes minutes. Uploads return at once; a job reads the book and writes
   its progress on the document row, which the screen shows as a checklist. Jobs take ids only and
   are safe to re-run. If the server stops, unfinished work is queued again at start-up.

7. **Streaming replies through three layers.**
   Tutor replies stream from FastAPI as Server-Sent Events, through a Next.js route handler, then
   Caddy, to the browser. Each layer could buffer the stream: I set `X-Accel-Buffering: no`, used
   pure ASGI middleware (not `BaseHTTPMiddleware`) and Caddy's `flush_interval -1`. A fast model
   sends a whole reply in under a second, so the chat box types it out at a steady pace.

## 1.9 What I would do next

- A pilot with real families, after a native speaker reviews the Hindi and Hinglish wording and a
  lawyer reviews DPDP Act compliance (parental consent, analytics on children).
- Password reset and email verification (a reset must revoke every session).
- Automated daily backups of the database and uploads, with a practised restore.
- Object storage (S3-compatible) for uploads: one new `FileStorage` adapter.
- Alertmanager so alerts reach a person.
- The server submitting tests whose time ran out (today the browser does).
- Tune the mastery and rate-limit constants with real usage data; consider IRT for difficulty.
