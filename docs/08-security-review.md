# 8. Security review (Step 12)

A review of the whole project before it serves real families: what was checked, what was fixed in
Step 12, and what is still open. Reviewed on 2026-11-05, on the code at the end of Step 12. Read it
again before a public launch and after any change to sign-in, uploads or the AI.

**Method.** Each area below was read in the code and, where possible, proven by a test that keeps
it true. The dependencies were checked with `pip-audit` and `npm audit` (both now run in CI). The
production setup (`infra/docker-compose.production.yml`) was started on one computer and the sign-up
journeys were run through it over HTTPS.

## 8.1 Fixed in Step 12

| # | Finding | Risk | Fix |
|---|---|---|---|
| 1 | Nothing limited how often anyone could try a password, sign up, or use the AI | Password guessing; a family (or a stolen session) running up the AI bill | Rate limits (docs/03 §3.11): failed sign-ins per email and per address, sign-ups per address, the family's AI requests, practices / tests and uploads. Counted in Redis in production |
| 2 | Signing out only deleted the cookies; a copied token worked on (access 30 minutes, refresh 14 days) | A token taken from a shared device stays usable | Sessions (`auth_sessions`, `ses` claim) checked on every request; `POST /auth/logout`, called by Sign out and by leaving child mode |
| 3 | No security headers on the pages or the API | Clickjacking, content sniffing, injected scripts loading from elsewhere | `next.config.ts`: CSP (this site only, no framing, no plugins), HSTS, nosniff, Referrer-Policy, Permissions-Policy. API: nosniff, DENY, no-referrer, `no-store`, a `default-src 'none'` CSP, HSTS in production |
| 4 | The API's interactive docs and schema were served in production | A map of every endpoint for an attacker | `/docs`, `/redoc`, `/openapi.json` are off when `ENVIRONMENT=production` |
| 5 | `pillow` 12.3.0 had 39 known vulnerabilities | Pillow handles the page images of uploaded books | `pillow` 13.0.0, with `fastembed` 0.9.1 (the first to allow it; 12 days old when pinned, two short of the usual two weeks, because of the vulnerabilities) |
| 6 | A failed database query logged the query's values | Children's answers or names in the logs | `hide_parameters` in production (`core/database.py`) |
| 7 | uvicorn's own access log printed each client's address and full query string | Personal data in the logs, next to the app's own log that leaves it out | `--no-access-log` in the image; the app logs every request (method, path, status, time, request id) |
| 8 | Books were read inside the API process | A slow or hostile PDF holds up every family's requests | In production a separate worker reads books (`python -m app.worker`); the API only queues the job |
| 9 | A refused sign-up crashed the form instead of saying why (found by the browser journeys) | A broken page instead of a message | A `429` keeps `details` for fields only; the wait is in `Retry-After` |

Jobs reach the worker as a name and ids in JSON (never pickled objects), and only the jobs listed in
`app/worker.py` can run, so whoever can write to Redis still cannot make the worker run other code.

## 8.2 Checked and sound

| Area | What holds | Kept true by |
|---|---|---|
| Signing in is required | Every route answers `401` without a token, except 8 public ones (health, sign-up, sign-in, refresh, sign-out, the sign-up forms' options) | `tests/api/test_route_security.py` walks every route, so a new one is checked too |
| Each family sees only its own data | Every service checks ownership; another family's id answers `404`, the same as one that does not exist | "who may see it" tests of every step (`tests/api/test_*.py`) |
| Child mode | A child-mode token acts as one child only: no siblings, no parent screens, no account changes | `tests/api/test_child_mode.py` |
| Passwords | Argon2id; 8–128 characters; an unknown email and a wrong password get the same answer in the same time | `tests/unit/test_security.py`, `tests/api/test_auth.py` |
| Tokens | Signed (HS256, the algorithm fixed), the secret at least 32 characters or the app will not start, required claims and the token's kind checked | `tests/unit/test_security.py`, `tests/unit/test_config.py` |
| Uploads | Type from the content, not the name; size, page and per-book limits; a Word file's unpacked size is capped and XML entities are never resolved; stored under random names outside anything served | `tests/unit/test_file_checks.py`, `tests/api/test_documents.py` |
| SQL injection | Every query goes through the ORM; the only raw SQL is the readiness check's `SELECT 1` | code read |
| Scripts in pages (XSS) | React escapes all text, AI answers included; no page inserts HTML; the CSP refuses scripts from other sites | code read; the browser journeys run with the CSP on |
| Forged requests (CSRF) | Session cookies are httpOnly, `SameSite=Lax`, `Secure` in production; Server Actions check the origin; the CSP allows forms to post to this site only | `tests/unit/session.test.ts` |
| Words in books steering the AI (prompt injection) | Book text goes to the model as quoted passages; answers must fit a schema and are shown as text; the model cannot do anything (no tools); citations are checked against the passages | `tests/unit/test_answering.py`, `tests/unit/test_citations.py` |
| Secrets | Only in environment variables; `backend/.env` and `infra/production.env` are git-ignored and kept out of the images | `.gitignore`, `.dockerignore` |
| Containers | Never root; only Caddy is reachable from outside; PostgreSQL and Redis have passwords and no published port; metrics are on a port of their own, not published | `infra/docker-compose.production.yml` |
| Libraries | `pip-audit`: no known vulnerabilities. `npm audit`: 8 moderate, all in the lint tools (the `typescript-eslint` chain of `eslint-config-next`), none in what runs; CI fails on high or critical | CI (`.github/workflows/ci.yml`) |

## 8.3 Still open

In rough order of importance. None blocks a small pilot with families the team knows.

1. **India's data protection law (DPDP Act, 2023).** Verifiable parental consent before processing a
   child's data, and whether the learning analytics count as monitoring, need a lawyer's review
   (docs/01 §1.10). So do students under 18 signing up alone.
2. **No password reset, password change or email check.** When they are added, a reset must revoke
   every session of the account (`auth_sessions.revoked_at`).
3. **Backups.** The database and uploads volumes are not backed up by anything in this project. On a
   server, back up `pgdata` and `uploads` every day and practise a restore.
4. **The CSP allows inline scripts.** Nonces would make every page dynamic and switch off Cache
   Components' prebuilt pages. Look again if Next.js's hash-based option (SRI) supports Turbopack,
   or if the pages become dynamic anyway.
5. **Refresh tokens are not rotated.** Two pages renewing at the same moment would sign people out,
   so they are not. Signing out still ends the session. Rotation with a short grace period is
   possible later.
6. **Per-address limits trust the proxy.** The browser's address comes from Caddy's
   `X-Forwarded-For`. Without Caddy (or another proxy that sets it) in front of the frontend, the
   address can be faked; the per-email and per-account limits still hold.
7. **The limits let requests through while Redis is down**, so families are not locked out; the
   readiness check and the `ApiDown` alert show it.
8. **Sign-up says when an email already has an account** (`email_already_registered`). That is kept
   for clear screens; the sign-up limit slows anyone collecting emails this way.
9. **No check against passwords known from breaches.**
10. **Alerts go nowhere yet.** `infra/monitoring/alerts.yml` shows them in Prometheus; add an
    Alertmanager (email, chat) before relying on them.
