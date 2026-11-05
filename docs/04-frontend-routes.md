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
| `/parent/dashboard` | This week day by day (answered, right the first time, minutes), Recommended with **Start Recommended Practice**, **Streak and badges** (streak, level and XP, today's goal, the newest badges), strong areas and needs attention, **Understand Mistakes** (up to 3 mistakes the child keeps making, with what to remember and Practise this), today's study plan, recent tests — one call (`GET /students/{id}/dashboard`) | 6 basic · 9 full · 10 · 11 |
| `/parent/children` · `/parent/children/new` · `/parent/children/[studentId]` | List, add, edit children | 5 |
| `/parent/books` | My Learning Library: every family book, labelled with the child it is for | 6 |
| `/parent/books/upload` | Upload Book: the book's details, then the file with a progress bar | 6 |
| `/parent/books/[bookId]` | Chapters of a book, its files with the reading checklist (retry, remove), add a file, delete the book. A book of previous-year papers (Class 9–12) lists its papers and shows their analysis: **Analyse the papers**, where the marks go (chapters by marks a paper, in how many papers, rising or falling; **Practise**), topics asked most, kinds of questions, the latest paper's layout, **Make a test like these papers** — for the chosen child when in the papers' class | 6 · 10 |
| `/parent/books/[bookId]/chapters/[chapterId]` | Chapter page: **Learn · Practice · Exercise Questions · Generate Questions · Take Test** (a chapter test from Class 6, a practice test of the chapter in Class 3–5, none below) | 6 · 9 |
| `/parent/practice` | Create Practice: number, difficulty, type, source, language. `?book=&chapter=&exercise=` preselect the source | 6 |
| `/parent/practice/[sessionId]` | A practice the parent made: "getting ready", then its questions and **Start now with {child}** (child mode straight into it) | 6 |
| `/parent/tests` · `/parent/tests/new` · `/parent/tests/[testId]` | The chosen child's tests; Create Test (`?kind=&book=&chapter=`: the kinds and the time limit follow the class's `practice_tests`, `chapter_tests`, `full_mock_tests`, `timed_tests`; a JEE / NEET / CUET learner is told their tests follow the exam's pattern, with marks lost for a wrong answer); a test: "getting ready", **Start now with {child}** (child mode straight into the test), its sittings and the report of one (`?attempt=`) | 9 |
| `/parent/plans` · `/parent/plans/new` | The chosen child's study plan day by day (one per learner, API: `GET /students/{id}/study-plan`), and making a new one: exam date, minutes a day, target, chapters | 9 |
| `/parent/progress` | Numbers, by chapter and topic, recent practice, **Progress over time** (the last 12 weeks, test scores, by subject, by kind of question, by difficulty — each with "Show the numbers"), streak and every badge, Understand Mistakes (current and put right), recent tests | 6 basic · 9 · 10 · 11 |
| `/parent/assistant` · `/parent/assistant/[chatId]` | Parent AI Assistant about the chosen child: suggested questions, replies as they are written with the books they used, earlier conversations. A new conversation is made with its first message and then opens at its own address | 9 |
| `/parent/settings` | Account, the language of the screens (the picker; saved on the account), sign out | 5 · 11 |

A child switcher at the top of the parent area (Step 6, kept in the `eg_child` cookie) chooses whose
dashboard, practice and progress are shown. My Books always lists all of the family's books.

## 4.4 Student area

Navigation (spec §38): Home · Practice · Learn · Tests · Progress · Study Plan · AI Tutor

| URL | Screen | Step |
|---|---|---|
| `/learn` | Home: the streak, level and XP, today's goal (the class's usual practice length), the menu as tiles, **Recommended for You** (Start; a weak topic can be revised first), **Today's plan** (Start, ✓ Done), practice to continue | 6 · 9 · 11 |
| `/learn/practice` · `/learn/practice/[sessionId]` | Choose and do practice; **Hint → Show Steps → Show Answer**; "+10 XP" and a new badge after an answer, the streak and goal at the end. Nursery–Class 2: big "Play" tiles per chapter, one tap answers, a number pad for counting, "try again" instead of a wrong mark, stars and stickers at the end, no XP | 6 · 11 |
| `/learn/concepts` · `/learn/concepts/[chapterId]` | Learn a concept; "Explain simply / Like I'm 10 / in Hindi / in Hinglish". `?q=` fills in the question, `?task=` is a learn task of the plan (ticked off once explained) | 6 · 9 |
| `/learn/tests` · `/learn/tests/[attemptId]` | My tests (Start, Continue, See result, Take again) and Create Test; the test screen: sections, a question grid, the timer (when the test has a time limit), each answer saved as it is given, submit — by the button or when the time runs out — then the result report | 9 |
| `/learn/progress` | My progress; Progress over time (Class 6+; Class 3–5: the weeks and subjects); streak and badges (My stickers for Nursery–Class 2, with no charts); Mistakes to fix (Class 3+: Revise the idea first, Practise this) | 6 · 10 · 11 |
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
  (`/learn/exit`, "Grown-ups") asks for the parent's password, which signs the parent in again;
  the child-mode session is then signed out on the backend (Step 12). When the 12-hour child
  session ends, the device goes to sign-in.
- A session the backend refuses (say the child was removed) is ended through `/signout`.
- **Signing out** (Step 12): `/signout` first calls `POST /auth/logout` with the refresh token (in
  child mode the access token), so the session's tokens stop working everywhere, then deletes the
  cookies. Sign-in and sign-up pass the browser's address on (`X-Forwarded-For`) for the backend's
  rate limits.
- **Security headers** (Step 12, `next.config.ts`) on every page: a CSP that allows this site only
  (inline scripts too: nonces would make every page dynamic), no framing, HSTS, nosniff,
  Referrer-Policy and Permissions-Policy. The Docker image runs the standalone server
  (`NEXT_OUTPUT=standalone`).
- **Uploads** (Step 6) go from the browser to one route handler, `/api/books/[bookId]/documents`,
  which streams the file on to the backend with the cookie's token. It sits outside `proxy.ts`,
  because the proxy buffers request bodies only up to 10 MB. Progress screens (a book being read,
  practice or a test being prepared) reload their data every 2 seconds until it is done.
- **Replies of the assistant and the tutor** (Step 9) stream from the backend as Server-Sent Events
  through a second route handler, `/api/chat/[chatId]/messages`, which passes them on piece by piece
  (`lib/sse.ts` reads them in the browser). It runs behind `proxy.ts`, so an expired token is renewed
  first; only the upload route is left out of the proxy.
- **Screen language** (Step 11): English, Hindi or Hinglish, in the `eg_lang` cookie (not secret; it
  stays when the session ends). Sign-in and sign-up set it from the account (`users.preferred_language`;
  sign-up gives the account the language the screens were in); child mode sets it to the child's
  language (`primary_language`, which the AI uses too) until a grown-up signs back in. The
  **language picker** (each language in its own words) is on the landing page, the sign-in, sign-up
  and onboarding pages, parent Settings and a solo student's header; signed in, it saves the account's
  language too (`PATCH /auth/me`). Not in child mode.
- **Where the words live**: `frontend/lib/copy/` has one file per language with the same shape
  (`en.ts`, `hi.ts`, `hinglish.ts`; the `Copy` type checks every key). Pages, layouts and async server
  components call `await getCopy()`; synchronous server components take a `copy` prop; client
  components call `useCopy()`. Page titles come from `titled()`. The page is marked with its `lang`
  (`hi`, `hi-Latn` for Hinglish; `<html>` stays `en`, as Cache Components cannot wait for the cookie
  there). Hindi is shown in Noto Sans Devanagari. Words the backend sends are put into the screen
  language by their code: error messages (`FormMessage`), class / board / goal labels, and the reasons
  of recommendations and plan tasks. Book, chapter and exercise titles stay as the book prints them.
- **Another Indian language** later: a new file in `lib/copy/` (the type lists what to translate),
  one line in `lib/copy/index.ts`, and `content_enabled` in the backend's `app/core/languages.py`.

### Landing after sign-in

| Who | Goes to | Unless |
|---|---|---|
| Parent | `/who-is-learning` | no children yet → `/onboarding/child` |
| Solo student | `/learn` | no class details yet → `/onboarding/profile` |
| Child mode | `/learn` | |
