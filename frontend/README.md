# Frontend

Next.js 16 (App Router, Cache Components) · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui.
Needs Node.js 22 or 24 LTS. Setup and commands are in the [root README](../README.md); the screens
and URLs are planned in [`docs/04-frontend-routes.md`](../docs/04-frontend-routes.md).

## How it fits together

| Where                                 | What                                                                                                                              |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `app/`                                | The screens. `(entry)/` sign-in, sign-up, onboarding and "Who is learning?"; `parent/` the parent area; `learn/` the student area |
| `proxy.ts`                            | Runs before every page: renews an expired access token, sends each session to its area                                            |
| `lib/session.ts`                      | The two httpOnly session cookies and how they are written                                                                         |
| `lib/backend.ts` · `lib/api.ts`       | Calls to the FastAPI backend. Only the Next.js server calls it, never the browser                                                 |
| `lib/actions/`                        | Server Actions behind every form (sign-in, Add Child, child mode, …)                                                              |
| `lib/copy.ts`                         | Every word on screen. Step 11 adds Hindi and Hinglish with the same shape                                                         |
| `lib/navigation.ts`                   | The parent menu and the student menu of each layout                                                                               |
| `components/learner-profile-form.tsx` | The class-first form used for adding and editing a learner                                                                        |
| `components/ui/`                      | shadcn/ui components (only the ones in use)                                                                                       |
| `tests/unit` · `tests/e2e`            | Vitest · Playwright                                                                                                               |

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
