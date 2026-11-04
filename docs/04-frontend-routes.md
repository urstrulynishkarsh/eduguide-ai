# 4. Frontend routes

Built in Steps 5, 6 and 9 with Next.js (App Router), TypeScript, Tailwind CSS and shadcn/ui.

## 4.1 Three areas

| Area | URL prefix | For | Feel |
|---|---|---|---|
| Public | `/` | visitors | landing page, sign-in, sign-up |
| Parent | `/parent/…` | parents | calm dashboard, plain language |
| Student | `/learn/…` | the child (child mode) or a solo student | changes with the class — see 4.4 |

The frontend decides which area to show from `GET /auth/me` → `active_role`. A student session
that opens a `/parent/…` URL is sent back to `/learn`.

## 4.2 Public and onboarding

| URL | Screen | Notes |
|---|---|---|
| `/` | Landing page | Hero "Turn Your Child's Books Into a Personalized AI Tutor", buttons **Get Started** / **See How It Works**, the strip *Upload → Understand → Practice → Improve* |
| `/login` | Sign in | |
| `/register` | "Welcome to EduGuide AI 👋 — Who are you?" **Parent** / **Student** | then name, email, password |
| `/onboarding/child` | Add Child (parent) | **Class is the first field.** Stream, goals and subject suggestions appear from the class chosen, using `/meta/options` |
| `/onboarding/profile` | My class details (solo student) | same form without name / age |
| `/who-is-learning` | Profile picker | Parent taps a child → child mode starts → `/learn` |

## 4.3 Parent area

Navigation (spec §38): Dashboard · Children · My Books · Practice · Mock Tests · Study Plans · Progress · AI Assistant · Settings

| URL | Screen | Step |
|---|---|---|
| `/parent/dashboard` | This week day by day (answered, right the first time, minutes), strong areas and needs attention, **Understand Mistakes** (up to 3 mistakes the child keeps making, with what to remember and Practise this), Recommended with **Start Recommended Practice**, today's study plan, recent tests — one call (`GET /students/{id}/dashboard`) | 6 basic · 9 full · 10 |
| `/parent/children` · `/parent/children/new` · `/parent/children/[studentId]` | List, add, edit children | 5 |
| `/parent/books` | My Learning Library: every family book, labelled with the child it is for | 6 |
| `/parent/books/upload` | Upload Book: the book's details, then the file with a progress bar | 6 |
| `/parent/books/[bookId]` | Chapters of a book, its files with the reading checklist (retry, remove), add a file, delete the book. A book of previous-year papers (Class 9–12) lists its papers and shows their analysis: **Analyse the papers**, where the marks go (chapters by marks a paper, in how many papers, rising or falling; **Practise**), topics asked most, kinds of questions, the latest paper's layout, **Make a test like these papers** — for the chosen child when in the papers' class | 6 · 10 |
| `/parent/books/[bookId]/chapters/[chapterId]` | Chapter page: **Learn · Practice · Exercise Questions · Generate Questions · Take Test** (a chapter test from Class 6, a practice test of the chapter in Class 3–5, none below) | 6 · 9 |
| `/parent/practice` | Create Practice: number, difficulty, type, source, language. `?book=&chapter=&exercise=` preselect the source | 6 |
| `/parent/practice/[sessionId]` | A practice the parent made: "getting ready", then its questions and **Start now with {child}** (child mode straight into it) | 6 |
| `/parent/tests` · `/parent/tests/new` · `/parent/tests/[testId]` | The chosen child's tests; Create Test (`?kind=&book=&chapter=`: the kinds and the time limit follow the class's `practice_tests`, `chapter_tests`, `full_mock_tests`, `timed_tests`; a JEE / NEET / CUET learner is told their tests follow the exam's pattern, with marks lost for a wrong answer); a test: "getting ready", **Start now with {child}** (child mode straight into the test), its sittings and the report of one (`?attempt=`) | 9 |
| `/parent/plans` · `/parent/plans/new` | The chosen child's study plan day by day (one per learner, API: `GET /students/{id}/study-plan`), and making a new one: exam date, minutes a day, target, chapters | 9 |
| `/parent/progress` | Numbers, by chapter and topic, recent practice, Understand Mistakes (current and put right), recent tests | 6 basic · 9 · 10 · 11 |
| `/parent/assistant` · `/parent/assistant/[chatId]` | Parent AI Assistant about the chosen child: suggested questions, replies as they are written with the books they used, earlier conversations. A new conversation is made with its first message and then opens at its own address | 9 |
| `/parent/settings` | Account, language, sign out | 5 |

A child switcher at the top of the parent area (Step 6, kept in the `eg_child` cookie) chooses whose
dashboard, practice and progress are shown. My Books always lists all of the family's books.

## 4.4 Student area

Navigation (spec §38): Home · Practice · Learn · Tests · Progress · Study Plan · AI Tutor

| URL | Screen | Step |
|---|---|---|
| `/learn` | Home: the menu as tiles, **Recommended for You** (Start; a weak topic can be revised first), **Today's plan** (Start, ✓ Done), practice to continue. (Daily challenge and streak: Step 11) | 6 · 9 |
| `/learn/practice` · `/learn/practice/[sessionId]` | Choose and do practice; **Hint → Show Steps → Show Answer**. Nursery–Class 2: big "Play" tiles per chapter, one tap answers, a number pad for counting, "try again" instead of a wrong mark, stars at the end | 6 |
| `/learn/concepts` · `/learn/concepts/[chapterId]` | Learn a concept; "Explain simply / Like I'm 10 / in Hindi / in Hinglish". `?q=` fills in the question, `?task=` is a learn task of the plan (ticked off once explained) | 6 · 9 |
| `/learn/tests` · `/learn/tests/[attemptId]` | My tests (Start, Continue, See result, Take again) and Create Test; the test screen: sections, a question grid, the timer (when the test has a time limit), each answer saved as it is given, submit — by the button or when the time runs out — then the result report | 9 |
| `/learn/progress` | My progress; Mistakes to fix (Class 3+: Revise the idea first, Practise this) | 6 · 10 |
| `/learn/plan` · `/learn/plan/new` | Today's tasks from the study plan (Start, ✓ Done), then the days to come. A student who signed up alone makes their own plan; a child's is made by the parent | 9 |
| `/learn/tutor` · `/learn/tutor/[chatId]` | AI Tutor: hint first, answer last; each reply shows its rung (Hint 1 … Answer) and the books it used | 9 |

### One area, four layouts

The student area reads `ui_mode` from the class profile and switches layout. It is the same
routes and the same data — only the presentation changes.

| `ui_mode` | Classes | What the child sees | Navigation shown |
|---|---|---|---|
| `playful` | Nursery – Class 2 | Very large cards and buttons, pictures and emoji, very few words, always-encouraging feedback. **No marks, no timers, no test screens.** | Home · Play & Learn · My Stars |
| `friendly` | Class 3 – 5 | Roomy and colourful, short sentences, step-by-step explanations | Home · Practice · Learn · Progress |
| `standard` | Class 6 – 8 | Regular app layout, chapter tests, weak-topic cards | all seven items |
| `dense` | Class 9 – 12 | Academic dashboard: charts, tables, timers, exam countdown | all seven items |

Features are hidden using the `features` flags of the class profile (for example the timer exists
only when `timed_tests` is true), so the frontend contains no class numbers of its own.

## 4.5 Words we use with parents

The parent may not be technical (spec §47). These words never appear on a parent screen:
*embeddings, vector database, RAG, retrieval, chunking, LLM, tokens, indexing.*

| Say | Not |
|---|---|
| Upload Book | Ingest document |
| Find Chapter | Retrieve |
| Create Practice | Generate questions from context |
| Understand Mistakes | Error analysis |
| Track Progress | Analytics |

The upload progress checklist, in parent words (the technical stage names stay in the backend):

| What the backend is doing | What the parent reads |
|---|---|
| extracting text | ✓ Reading your book |
| detecting chapters | ✓ Finding the chapters |
| detecting exercises and questions | ✓ Finding exercises and questions |
| detecting topics | ✓ Understanding the topics |
| `make_chunks`, `embed_chunks` | ✓ Getting practice ready |

Error wording follows spec §45, for example: *"We couldn't process this document. Please try another PDF."*

## 4.6 Sessions in the browser

Built in Step 5 (`frontend/lib/session.ts`, `frontend/proxy.ts`).

- Tokens are kept in **two httpOnly cookies set by the Next.js server**, not in `localStorage`, so
  scripts on the page cannot read them: `eg_access` (the token sent to the backend) and
  `eg_refresh`. Only the Next.js server talks to the backend. Pages read data on the server;
  forms are **Server Actions**. (Two route handlers pass calls through: uploads, and the streamed
  replies of the assistant and the tutor — see below.)
- `proxy.ts` runs before every page. When the access token is about to expire it uses the refresh
  token silently; a refresh the backend refuses ends the session. It also sends each session to its
  area: signed out → `/login`, a student session on a parent URL → `/learn`, a parent on `/learn`
  → `/who-is-learning`. These redirects only choose a screen; the backend checks every call.
- **Child mode** replaces the access token with the child-session token **and deletes the parent's
  refresh token**, so nothing on the device can act as the parent. Leaving child mode
  (`/learn/exit`, "Grown-ups") asks for the parent's password, which signs the parent in again.
  When the 12-hour child session ends, the device goes to sign-in.
- A session the backend refuses (say the child was removed) is ended through `/signout`.
- **Uploads** (Step 6) go from the browser to one route handler, `/api/books/[bookId]/documents`,
  which streams the file on to the backend with the cookie's token. It sits outside `proxy.ts`,
  because the proxy buffers request bodies only up to 10 MB. Progress screens (a book being read,
  practice or a test being prepared) reload their data every 2 seconds until it is done.
- **Replies of the assistant and the tutor** (Step 9) stream from the backend as Server-Sent Events
  through a second route handler, `/api/chat/[chatId]/messages`, which passes them on piece by piece
  (`lib/sse.ts` reads them in the browser). It runs behind `proxy.ts`, so an expired token is renewed
  first; only the upload route is left out of the proxy.
- Screen language follows `users.preferred_language` (from Step 11; all wording is already in
  `frontend/lib/copy.ts`); content language follows the child's `primary_language`.

### Landing after sign-in

| Who | Goes to | Unless |
|---|---|---|
| Parent | `/who-is-learning` | no children yet → `/onboarding/child` |
| Solo student | `/learn` | no class details yet → `/onboarding/profile` |
| Child mode | `/learn` | |
