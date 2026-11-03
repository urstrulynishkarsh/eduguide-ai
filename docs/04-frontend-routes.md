# 4. Frontend routes

Built in Steps 5, 6 and 9 with Next.js (App Router), TypeScript, Tailwind CSS and shadcn/ui.
This is the plan those steps follow.

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
| `/parent/dashboard` | Weekly progress, strong areas, needs attention, AI recommendation with **Start Recommended Practice** | 6 basic · 9 full |
| `/parent/children` · `/parent/children/new` · `/parent/children/[studentId]` | List, add, edit children | 5 |
| `/parent/books` | My Learning Library | 6 |
| `/parent/books/upload` | Upload Book with the progress checklist | 6 |
| `/parent/books/[bookId]` | Chapters of a book | 6 |
| `/parent/books/[bookId]/chapters/[chapterId]` | Chapter page: **Learn · Practice · Exercise Questions · Generate Questions · Take Test** | 6 |
| `/parent/practice` | Create Practice: number, difficulty, type, source, language | 6 |
| `/parent/tests` · `/parent/tests/new` · `/parent/tests/[testId]/report` | Mock tests and their reports | 9 |
| `/parent/plans` · `/parent/plans/new` · `/parent/plans/[planId]` | Study plans | 9 |
| `/parent/progress` | Charts by subject, chapter, topic; mistakes explained | 6 basic · 9 · 11 |
| `/parent/assistant` | Parent AI Assistant | 9 |
| `/parent/settings` | Account, language, sign out | 5 |

A child switcher at the top of the parent area chooses whose data every screen shows.

## 4.4 Student area

Navigation (spec §38): Home · Practice · Learn · Tests · Progress · Study Plan · AI Tutor

| URL | Screen | Step |
|---|---|---|
| `/learn` | Home: today's goal, Practice / Mock Test / Learn a Concept / Daily Challenge, streak, "Recommended for You" | 6 |
| `/learn/practice` · `/learn/practice/[sessionId]` | Choose and do practice; **Hint → Show Steps → Show Answer** | 6 |
| `/learn/concepts` · `/learn/concepts/[chapterId]` | Learn a concept; "Explain simply / Like I'm 10 / in Hindi / in Hinglish" | 6 |
| `/learn/tests` · `/learn/tests/[attemptId]` | Take a test, see the result | 9 |
| `/learn/progress` | My progress | 6 basic · 9 |
| `/learn/plan` | Today's tasks from the study plan | 9 |
| `/learn/tutor` | AI Tutor | 9 |

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

- Tokens are kept in **httpOnly cookies set by the Next.js server**, not in `localStorage`, so
  scripts on the page cannot read them. Next.js route handlers forward calls to the backend.
- Child mode replaces the active token with the child-session token. Leaving child mode asks for
  the parent's password again, so a child cannot wander into the parent area.
- When an access token expires, the Next.js server uses the refresh token silently.
- Screen language follows `users.preferred_language`; content language follows the child's
  `primary_language`.
