# Frontend

Next.js 16 (App Router, Cache Components) · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui.
Needs Node.js 22 or 24 LTS. Setup and commands are in the [root README](../README.md); the screens
and URLs are planned in [`docs/04-frontend-routes.md`](../docs/04-frontend-routes.md).

## How it fits together

| Where                                                                                           | What                                                                                                                                      |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `app/`                                                                                          | The screens. `(entry)/` sign-in, sign-up, onboarding and "Who is learning?"; `parent/` the parent area; `learn/` the student area         |
| `proxy.ts`                                                                                      | Runs before every page, Server Action and chat reply: renews an expired access token, sends each session to its area                      |
| `lib/session.ts`                                                                                | The two httpOnly session cookies and how they are written                                                                                 |
| `lib/backend.ts` · `lib/api.ts`                                                                 | Calls to the FastAPI backend. Only the Next.js server calls it, never the browser                                                         |
| `lib/actions/`                                                                                  | Server Actions behind every form and button (sign-in, Add Child, child mode, books, practice, tests, plans, conversations)                |
| `lib/copy.ts`                                                                                   | Every word on screen. Step 11 adds Hindi and Hinglish with the same shape                                                                 |
| `lib/navigation.ts`                                                                             | The parent menu and the student menu of each layout                                                                                       |
| `components/learner-profile-form.tsx`                                                           | The class-first form used for adding and editing a learner                                                                                |
| `components/practice-player.tsx`                                                                | The practice screen: help, explain; the picture version for Nursery–Class 2                                                               |
| `components/answer-input.tsx`                                                                   | Answering each question format (choices, numbers, blanks, written answers, matching): practice and tests share it                         |
| `components/book-uploader.tsx` · `app/api/books/[bookId]/documents`                             | Upload Book: the browser sends the file with a progress bar; the route streams it to the backend (outside `proxy.ts`)                     |
| `components/question-chooser.tsx`                                                               | Create Practice and Create Test: the place picker (a plain GET form: kind → book → chapter → exercise), then `question-settings-form.tsx` |
| `components/start-button.tsx`                                                                   | One button that makes a practice or a test from ready-made settings: a chapter, a recommendation, a task of the plan                      |
| `components/test-player.tsx` · `test-report.tsx`                                                | The test screen (sections, question grid, timer, answers saved as they are given) and the result report                                   |
| `components/plan-view.tsx` · `plan-form.tsx`                                                    | The study plan (summary, days, tasks with Start and ✓ Done) and Make a plan                                                               |
| `components/dashboard.tsx`                                                                      | The parent dashboard's week chart, Recommended (also on the learner's home) and recent tests                                              |
| `components/chat-box.tsx` · `chat-screen.tsx` · `app/api/chat/[chatId]/messages` · `lib/sse.ts` | The AI Assistant and the AI Tutor: the reply streams through the chat route and is read as Server-Sent Events                             |
| `components/ui/`                                                                                | shadcn/ui components (only the ones in use)                                                                                               |
| `tests/unit` · `tests/e2e`                                                                      | Vitest · Playwright (the practice journeys need the demo family: `python -m scripts.seed`)                                                |

## The four layouts

The student area sets `data-ui-mode` from the class profile's `ui_mode`. `app/globals.css` gives
each mode its colours, roundness and font, and Tailwind variants style the rest:
`playful:text-5xl`, `friendly:flex-col`, `standard:…`, `dense:gap-3`. Which menu items exist comes
from the profile's `features`, so no class numbers appear in the frontend.

## Good to know

- With Cache Components, a page that reads the session renders behind `app/loading.tsx`, and
  Next.js keeps recently visited pages mounted (hidden) for instant back-navigation. Browser tests
  therefore click only visible elements (`tests/e2e/helpers.ts`).
- The form options and class profiles are fetched on each request, so `npm run build` never
  needs the backend.
- A page kept mounted keeps its state, so what must start afresh resets itself: the new-conversation
  box after its first reply (it then opens the conversation's own address), Learn a Concept when it
  is opened for another plan task.
