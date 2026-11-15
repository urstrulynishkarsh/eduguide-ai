# 6. Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui

---

## 6.1 Next.js 16 (App Router)

**What:** a React framework with server rendering, file-based routes, Server Components, Server
Actions and route handlers. Version 16.4, with **Cache Components** on. In Next.js 16 the old
`middleware.ts` is now `proxy.ts`.

**Why here**
- **The browser never talks to the API. Only the Next.js server does** (the backend-for-frontend,
  or BFF, pattern). Tokens live in **httpOnly cookies** that page scripts can't read, which is much
  safer than `localStorage`.
- **Server Components** fetch data on the server: less JavaScript sent to the phone, no loading
  spinners for the first view, and no API base URL or tokens in the browser.
- **Server Actions** handle every form: no client-side API layer, built-in origin checks (CSRF
  protection), and forms work even before JavaScript loads.
- **`proxy.ts`** runs before every page: it renews tokens and sends each session to its area.
- **Route handlers** for the two things Server Actions can't do well: **streaming a book upload**
  to the backend, and **streaming chat replies** (SSE).
- A public **landing page** that is server-rendered (good for search engines and a fast first view).
- **Cache Components**: static parts of pages are prebuilt, and dynamic parts stream in.

**Alternatives**

| Alternative | Good at | Why not here |
|---|---|---|
| React SPA with Vite | Simple, fast builds, no server | Tokens would live in the browser (`localStorage` or readable cookies); no server rendering for the landing page; more JavaScript on cheap phones |
| Remix / React Router 7 | Loaders and actions, web standards | Close in design; Next.js has the bigger ecosystem and Server Components |
| SvelteKit / Nuxt (Vue) | Small bundles, nice developer experience | Smaller hiring pool and ecosystem than React; shadcn/ui and Radix are React |
| Angular | Large enterprise apps | Heavier; less suited to a small team moving fast |

**Say it:** "I used Next.js as a backend-for-frontend. The browser only talks to the Next.js
server, which holds the tokens in httpOnly cookies and calls FastAPI. Pages load their data in
Server Components and forms are Server Actions, so there is almost no client-side API code and no
token ever reaches page scripts."

### `proxy.ts`: before every page

- Reads the role and expiry from the access token **without checking its signature**. That is
  good enough to **choose a screen**; the backend checks every token it receives.
- If the access token expires within 30 seconds, it renews it with the refresh token and writes
  the new cookies on **both the request** (so the page rendered now sees them) **and the response**.
- Sends each session to its area: signed out → `/login`; a student on a parent URL → `/learn`;
  a parent on `/learn` → `/who-is-learning`.
- If the backend is **down**, the session is kept (not thrown away).
- **Not run on the upload route**, because the proxy buffers request bodies (up to 10 MB) and a
  book can be 50 MB. That route renews the token itself with the same `renewSession` function.

**Follow-up: "Isn't redirecting in the proxy a security check?"** No. It only picks a screen.
Every API call is checked by the backend: role, ownership, session. The proxy could be wrong and
nothing would leak.

### Cache Components and the CSP trade-off

- Cache Components prebuild a static shell for each page; dynamic parts (anything reading cookies)
  stream in inside `<Suspense>`.
- A strict CSP with **nonces** would make every page dynamic and switch prebuilding off. So the
  CSP allows inline scripts but **only from this site**. This trade-off is written down as an open
  item in the security review.
- The root `<html lang>` stays `en` because Cache Components can't wait for the language cookie
  there; each page sets `lang` (`hi`, `hi-Latn` for Hinglish) on its own wrapper.

### Every data page has a `loading.tsx`

Without it, moving between pages waits on the server with no sign of life. That's a project rule.

---

## 6.2 React 19

**What:** the UI library. Version 19 brings Server Components, Actions, `useActionState` and
`useFormStatus` as stable features.

**Why here**
- **Server Components** by default; `"use client"` only where there's interaction (the practice
  player, the PIN pad, the chat box, the uploader).
- **`useActionState`** connects forms to Server Actions and shows their errors and pending state.
- **Suspense** streams slow parts of a page.
- **Safe by default:** React escapes all text, AI answers included. No page inserts raw HTML.

| Alternative | Why not here |
|---|---|
| Vue / Svelte / Solid | See 6.1: React has the largest ecosystem and the libraries used here |
| Preact | Smaller, but no Server Components |

---

## 6.3 TypeScript 5.9

**Why here**
- One set of types for API responses (`lib/types.ts`), checked across 41 screens.
- **Missing translations fail the build.** `type Copy = typeof en`, and `hi` and `hinglish` must
  satisfy `Copy`. Forget one key in Hindi and `tsc` refuses.
- `next typegen` generates types for routes and layout props (`LayoutProps<"/">`).
- Strict mode, plus `tsc --noEmit` in CI.

| Alternative | Why not here |
|---|---|
| Plain JavaScript | No compile-time safety on a 11,000-line frontend |
| JSDoc types | Weaker; awkward for generics |

**Possible improvement to mention:** generating the TypeScript types from FastAPI's OpenAPI schema
(`openapi-typescript`) so frontend and backend types can never drift apart.

---

## 6.4 Tailwind CSS 4

**What:** utility-first CSS. Version 4 has a new engine (Oxide, written in Rust), configuration in
CSS (`@theme`) instead of a JS file, and a Turbopack loader.

**Why here**
- **Design tokens in CSS** (`@theme inline` in `app/globals.css`): the light cream theme, and one
  main colour per age layout (orange for the youngest, teal, blue, deeper blue), all from tokens.
  Text keeps a **4.5:1 contrast ratio** (WCAG AA).
- No runtime CSS: works with Server Components (runtime CSS-in-JS libraries struggle there).
- Fast to build mobile-first, responsive layouts (phones, tablets, computers).

| Alternative | Good at | Why not here |
|---|---|---|
| CSS Modules | Scoped plain CSS | Slower to build with; tokens and responsive variants by hand |
| styled-components / Emotion | Components with styles | Runtime CSS-in-JS doesn't fit Server Components well |
| MUI / Chakra UI | Full component kits | Heavier; their look is hard to bend into four age-based layouts |
| Bootstrap | Familiar | Generic look; less control |

---

## 6.5 shadcn/ui + Radix UI + lucide-react

**What:**
- **shadcn/ui** isn't a dependency. It **copies component source into your repo** (`components/ui/`),
  so you own and edit it. Only the ones in use are kept: Button, Input, Label.
- **Radix UI** gives unstyled, **accessible** primitives (focus handling, ARIA, keyboard).
- **class-variance-authority**, **clsx** and **tailwind-merge** handle component variants and
  class merging. **lucide-react** provides the icons.

**Why here:** accessibility matters (children, parents on cheap phones, the axe checks in the
browser tests), and owning the source means the four layouts can restyle components freely.

| Alternative | Why not here |
|---|---|
| MUI / Ant Design | Big bundles, strong default look, harder to theme per age group |
| Headless UI | Similar idea to Radix, with fewer primitives |
| Writing everything from scratch | Accessibility is easy to get wrong (focus traps, ARIA) |

---

## 6.6 Three languages without an i18n library

**How it works**
- `frontend/lib/copy/` has **one file per language**: `en.ts`, `hi.ts`, `hinglish.ts`, all the
  same shape, checked by the `Copy` type.
- Server pages call `await getCopy()`, synchronous server components take a `copy` prop, and client
  components call `useCopy()`.
- The language is in the `eg_lang` cookie (not secret; it stays after sign-out) and saved on the
  account. **Child mode switches to the child's language.**
- **The backend sends codes, not sentences** (`insufficient_context`, `daily_limit_reached`…), and
  each screen words the code in its language.
- Book, chapter and exercise titles stay as the book prints them.
- Hindi uses **Noto Sans Devanagari**, loaded only on pages that show Hindi (`preload: false`).
- Adding a language = one new file (the type lists what to translate) + one line + a backend flag.

| Alternative | Good at | Why not here |
|---|---|---|
| next-intl | Routing per locale, ICU messages, plurals | Hinglish isn't a standard locale; I wanted a compile-time check that every key exists in every language; three languages didn't need more |
| react-i18next | Widely used | JSON files with no type checking by default; missing keys show up at runtime |
| Lingui / FormatJS | Message extraction, ICU | More tooling than needed |

**Honest trade-off:** no ICU plural rules or locale-aware number formats yet. If more languages
come, moving to next-intl with typed messages would be reasonable.

---

## 6.7 Four layouts from one set of routes

| `ui_mode` | Classes | Feel |
|---|---|---|
| `playful` | Nursery – Class 2 | Big picture cards, emoji, very few words, a number pad for counting, "try again", stars and stickers. **No marks, no timers, no tests** |
| `friendly` | Class 3 – 5 | Roomy and colourful, short sentences, step-by-step |
| `standard` | Class 6 – 8 | A normal app: chapter tests, weak-topic cards |
| `dense` | Class 9 – 12 | Academic: charts, tables, timers, exam countdown |

The same routes and data, only the presentation changes. The layout comes from the class profile's
`ui_mode`, and features are hidden by its `features` flags. **The frontend contains no class
numbers of its own.**

---

## 6.8 Other frontend details worth mentioning

- **Uploads with a progress bar:** the browser sends the file to `/api/books/[bookId]/documents`,
  which **streams** it to the backend with the cookie's token, without holding 50 MB in memory.
- **Progress screens poll every 2 seconds** (a book being read, practice being prepared) until
  done. Polling is fine here: a few users, short waits, and no extra infrastructure.
- **Child mode** replaces the parent's cookies with child-mode tokens, so nothing on the device can
  act as the parent until the PIN is entered on an **on-screen number pad**.
- **Forms:** a shared `Field` component sets `autoComplete` correctly (`"email"`,
  `"current-password"`…). A field is only called `name` if it holds the signed-in person's name,
  because Chrome fills the parent's name into any field called `name`.
- **Security headers** on every page from `next.config.ts`: CSP, HSTS, `nosniff`,
  `X-Frame-Options: DENY`, Referrer-Policy and Permissions-Policy (camera, microphone, location,
  payment all off).
- **Docker:** the standalone output (`NEXT_OUTPUT=standalone`) gives a small production server.
- **Node.js 22 / 24 LTS.** All package versions are pinned exactly in `package.json`.
