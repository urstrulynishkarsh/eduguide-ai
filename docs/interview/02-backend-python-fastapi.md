# 2. Backend: Python, FastAPI and the patterns behind them

Each entry: **what it is → why it is used here → alternatives → what to say → likely follow-ups.**

---

## 2.1 Python 3.12

**What:** the backend language. 3.12 is used; 3.11+ works.

**Why here**
- The AI and document tools this project needs are strongest in Python: the official `anthropic`
  and `groq` SDKs, `fastembed` / ONNX Runtime for the local search model, `pypdfium2`,
  `python-docx`, Tesseract bindings, Pillow.
- **Pydantic** is the natural way to define the shape of every AI answer and validate it.
- `asyncio` handles many slow network calls (AI replies take seconds) without a thread per request.
- Modern typing (`X | None`, `Protocol`, generics, `Literal`) keeps a 15,000-line codebase readable.

**Alternatives**

| Alternative | Good at | Why not here |
|---|---|---|
| Node.js / TypeScript (Express, NestJS) | One language with the frontend; fast I/O | Weaker PDF, OCR and local-embedding ecosystem; no Pydantic-quality validation of AI output |
| Go | Speed, small binaries, simple concurrency | Few libraries for PDF structure, OCR and embeddings; more code for the same features |
| Java / Kotlin (Spring Boot) | Big-company standard, strong typing | Heavier to build with; the AI tooling arrives in Python first |

**Say it:** "Python because the AI and document-processing libraries I needed are Python-first, and
Pydantic gives me typed, validated AI output. Async Python handles the slow AI calls well."

**Follow-up: "Isn't Python slow?"** The slow parts here are network calls to the AI and the
database, not Python itself. The heavy computing (embeddings) runs in ONNX Runtime (C++), and PDF
parsing runs in PDFium (C++). CPU-bound work is moved off the event loop with `asyncio.to_thread`.

---

## 2.2 FastAPI

**What:** an async Python web framework built on Starlette (HTTP) and Pydantic (validation).
Version 0.142, fully async.

**Why here**
- **Async-native.** AI calls take seconds; while one waits, the same process serves other requests.
- **Pydantic validation built in.** Every request body and query parameter is validated before the
  handler runs. `Annotated[int, Query(ge=1, le=50)]` is all it takes.
- **Dependency injection.** Auth and rate limits are dependencies: `CurrentPrincipal` gives the
  verified caller, and `dependencies=[limit_account(AI_PER_MINUTE, AI_PER_DAY)]` limits a route.
- **Automatic OpenAPI docs** at `/docs` (turned off in production). A test walks the generated
  OpenAPI schema to check that every route needs a sign-in.
- **`StreamingResponse`** for Server-Sent Events (the tutor's replies).
- **`lifespan`** hook to resume unfinished background work when the app starts.

**Alternatives**

| Alternative | Good at | Why not here |
|---|---|---|
| Django + Django REST Framework | Admin, ORM, auth, a huge ecosystem | Async support is partial (ORM mostly sync); no admin role is needed; heavier than the API requires |
| Django Ninja | FastAPI-style on top of Django | Still carries Django's sync ORM and project structure |
| Flask | Small and simple | No built-in validation or async-first design; you assemble everything yourself |
| Litestar | Similar to FastAPI, fast, more built in | Smaller community and fewer examples |
| NestJS (Node) | Structured, decorators, TypeScript | Node instead of Python (see 2.1) |

**Say it:** "FastAPI because the app is I/O-bound: most time is spent waiting on the AI or the
database. Async lets one process serve many requests while it waits. Pydantic validation and
dependency injection give me input checks, auth and rate limits with very little code."

**Follow-ups**
- *"What happens if you call blocking code inside an async route?"* It freezes the event loop for
  every request. That's why embedding runs in `asyncio.to_thread` and the drivers are async
  (asyncpg, redis.asyncio, async SDKs).
- *"`def` or `async def` routes?"* FastAPI runs `def` routes in a thread pool. Here everything is
  `async def` because every call underneath is async.
- *"How do you version the API?"* All routes sit under `/api/v1`.

---

## 2.3 Uvicorn (the ASGI server)

**What:** the server that runs the FastAPI app. `uvicorn[standard]` adds uvloop (a faster event
loop) and httptools.

**Why here:** the standard, well-tested ASGI server for FastAPI. In production it runs with:
- `--proxy-headers` + `FORWARDED_ALLOW_IPS` so it trusts `X-Forwarded-For` **only from the
  frontend's network** (needed for per-address rate limits, and safe against spoofing);
- `--no-access-log`, because uvicorn's own log prints client addresses and full query strings.
  The app logs each request itself with ids only;
- `--no-server-header`, so the response doesn't say which server is running.

| Alternative | Why not here |
|---|---|
| Gunicorn with Uvicorn workers | Useful for managing several worker processes on one machine; here Docker restarts the container and scaling is done with more containers |
| Hypercorn | Supports HTTP/2 and HTTP/3; not needed behind Caddy |
| Granian (Rust) | Faster on paper; newer, and speed is not the bottleneck |

---

## 2.4 Pydantic v2 and pydantic-settings

**What:** data validation with Python type hints. The core is written in Rust (fast).
`pydantic-settings` reads settings from environment variables and `.env`.

**Why here**
- **Request and response shapes** (`app/schemas/`).
- **The shape of every AI answer.** The model has to fill a Pydantic model (`GeneratedQuestion`,
  `Review`, `Understanding`…). The Claude SDK validates it (`messages.parse(output_format=...)`).
  For Groq, the JSON schema comes from `model_json_schema()` and the answer is validated with the
  same model.
- **Settings checked at start-up.** The app refuses to start if `JWT_SECRET_KEY` is shorter than
  32 characters, or if `REDIS_URL` is missing in production.

| Alternative | Why not here |
|---|---|
| marshmallow | Older and slower; schemas separate from type hints |
| attrs / dataclasses + manual checks | No validation or JSON Schema out of the box |
| msgspec | Very fast, but FastAPI and the AI SDKs are built around Pydantic |

**Say it:** "Pydantic is the contract between my code and the AI. If the model returns something
that doesn't fit the schema, it never reaches the database or the screen."

---

## 2.5 How the backend is organised

| Folder | Job |
|---|---|
| `api/` | Thin routes: read the request → call a service → return the response |
| `services/` | Business logic, transactions and **data isolation** (who may see what) |
| `models/` | Database tables (SQLAlchemy) |
| `schemas/` | Request and response shapes (Pydantic) |
| `core/` | Settings, database, security, errors, middleware, task queue, rate limits, metrics |
| `auth/` | Sign-up, sign-in, tokens, child mode, "who is calling" |
| `class_profiles/` | The rules for each class |
| `rag/` | Reading books, OCR, embeddings, search, grounded explanations |
| `llm/` | The provider interface and the Claude and Groq adapters |
| `question_generation/` | Write → check → review; marking answers; test papers |
| `adaptive_learning/` | Mastery, difficulty, recommendations, study planner, misconceptions |
| `analytics/` | Progress, trends, previous-year paper analysis, streaks, XP, badges |
| `chat/` | The tutor's hint ladder and the parent assistant |

### Patterns worth naming in an interview

- **Layered architecture with thin controllers.** Routes hold no logic, so services can be tested
  without HTTP and reused by background jobs.
- **Services own the transaction.** A service that changes data commits before returning; anything
  not committed is rolled back when the session closes.
- **Ports and adapters (hexagonal).** `LLMProvider`, `EmbeddingProvider`, `OCRProvider`,
  `FileStorage` and `TaskQueue` are Python `Protocol`s. Business code never imports a vendor SDK.
  Changing provider = one adapter + an environment variable.
- **Structural typing with `Protocol`** instead of base classes: an adapter only has to have the
  right methods, and test doubles don't inherit anything.
- **One error format.** Every error is `{"error": {"code", "message", "details"}}`. The frontend
  words each `code` in the screen's language, so the backend never sends sentences for the UI.
- **Cursor pagination** for lists that grow: the cursor is the `(created_at, id)` of the last row,
  so rows added in between never shift the next page (offset pagination would).
- **Pure ASGI middleware** for the request id, timing, metrics and security headers. It passes
  streamed responses straight through. Request bodies have a size limit before they're read.
- **Request ids.** Every request gets an `X-Request-ID`; logs carry ids and counts, **never**
  children's names, answers or book text.

**Follow-up: "Why not put logic in the routes, it's simpler?"** Background jobs (preparing practice,
reading books) call the same services as the routes. Logic in routes would be duplicated or
untestable. And data isolation must live in one place to be trusted.
