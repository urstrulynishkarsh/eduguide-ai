# 5. The AI layer: LLM providers, checking AI output, the tutor, streaming

---

## 5.1 The `LLMProvider` interface (and why not LangChain)

**What:** one small Python `Protocol` in `app/llm/base.py` with **two methods**:

```python
class LLMProvider(Protocol):
    request_size: RequestSize                       # how much one request may carry

    async def generate_structured(*, system, messages, schema: type[T],
                                  tier="default", max_output_tokens=16000) -> LLMResult[T]: ...

    def stream_text(*, system, messages, tier="default",
                    max_output_tokens=16000) -> AsyncIterator[str]: ...
```

- `generate_structured` returns a **validated Pydantic object** plus the model, token counts and
  latency.
- `stream_text` is only for chat replies shown directly to a person.
- Three **errors** with codes: `503 ai_not_configured`, `503 ai_unavailable` (busy, network, bad
  key; details in the log), `422 ai_declined` (a safety refusal).
- Two adapters: `AnthropicProvider` (Claude) and `GroqProvider` (open models). Chosen with
  `LLM_PROVIDER`. With no provider, AI features return a clear error. **There is no fake AI** in
  the app.

**Why my own interface instead of LangChain or LlamaIndex**

| Option | Good at | Why not here |
|---|---|---|
| **LangChain** | Many integrations, ready-made chains and agents | Big dependency with frequent breaking changes; hides the prompt and the retries; I need full control over validation, retries and logging |
| **LlamaIndex** | Ready-made RAG pipelines | Its generic chunking and retrieval don't know textbook structure; my retrieval is a single SQL query |
| **LiteLLM** | One API over 100+ providers | Useful, but loses provider-specific features I use (Claude's structured parse, effort, prompt caching, server-side fallback) |
| **Instructor** | Pydantic output from any LLM | Close to what I need; both SDKs now do structured output natively |
| Calling the SDK directly from business code | Simple | Locks every feature to one vendor; can't test without the network |

**Say it:** "My interface is two methods. That was enough to add Groq as a second provider later
by writing one adapter, with no business code changes. A framework would have hidden exactly the
parts I need to control: the prompt, the schema, the retries and the logs."

---

## 5.2 Claude (the `anthropic` SDK)

**What:** Anthropic's Claude models through the official Python SDK (2.x). The default for every
tier is `claude-opus-5-5`; tiers differ by **effort** (low / medium / high).

**Features used, and why**
- **Structured output** with `messages.parse(output_format=<Pydantic model>)`: the SDK validates
  the answer against the schema.
- **Effort per tier** with adaptive thinking: low effort for small jobs, high for the hardest checks.
- **Prompt caching** (`cache_control: ephemeral`): the system prompt (role, rules, learner profile)
  is the same across calls, so it is cached. That's cheaper and faster.
- **Server-side fallback for refusals** (`fallbacks: "default"`): if the model declines, the API
  retries on the model Anthropic recommends instead of failing. A final refusal becomes
  `ai_declined`.
- **Streaming** (`messages.stream`) for chat replies.
- The SDK **retries 429s, overloads and network errors** itself.
- Logs: model, tier, stop reason, input / cached / output tokens, latency and request id. **Never
  the prompt or the answer text.**

**Why Claude:** quality first for questions children will see, strong instruction following for
age-appropriate language, native structured output, and refusal handling. A cheaper model per tier
is just a setting (`LLM_MODEL_FAST`, …) once the cost is worth measuring.

---

## 5.3 Groq (open models, free plan)

**What:** Groq hosts open models on fast inference hardware. Used through the official `groq` SDK
with `openai/gpt-oss-20b` (fast tier) and `openai/gpt-oss-120b` (default and strong tiers).

**Why it was added:** a **free plan** to develop and demo without paying for every call.

**How it works**
- `chat.completions` with `response_format` set to a **strict JSON schema** (constrained decoding).
  Strict mode needs every object closed, so `strict_schema()` marks every property required (the
  optional ones are already "or null") and sets `additionalProperties: false`.
- The answer is validated with the **same Pydantic model** as Claude's.
- Reasoning effort per tier, with the reasoning left out of the reply.
- Open models have no refusal signal, so `ai_declined` never comes from Groq.

**The engineering problem it caused (a good story):** the free plan allows **8,000 tokens a
minute**, and (as I measured; it isn't documented) Groq counts a request as its input plus the
largest reply of the last few minutes. Writing 10 questions in one call got 413 errors. Fix: each provider declares a `RequestSize` (Claude: 6,000 tokens of book text
and 10 questions per call; Groq: 1,500 and 3), replies are capped at 3,500 tokens, and the SDK
retries up to 6 times, waiting as Groq asks. **Measured:** a 5-question hard practice = 8 requests,
about 4 minutes. The README tells users to ask for 5 at a time on the free plan.

| Alternative provider | Why not (yet) |
|---|---|
| OpenAI GPT | Would work fine; one more adapter. Claude was chosen for quality, Groq for free |
| Google Gemini | Same: one adapter away |
| Self-hosted (Ollama, vLLM) | Needs a GPU server; quality of small models is lower for checking maths |

---

## 5.4 Model tiers (cost control)

| Tier | Used for | Claude | Groq |
|---|---|---|---|
| `fast` | Understanding a question, marking written answers | Opus 5.5, low effort | gpt-oss-20b |
| `default` | Writing explanations, questions, chat replies | Opus 5.5, medium effort | gpt-oss-120b |
| `strong` | Reviewing (independently solving) generated questions | Opus 5.5, high effort | gpt-oss-120b |

Changing a tier's model is an environment variable, not a code change.

---

## 5.5 From prompt to trusted object

**Prompt parts, always in this order**
1. Role and guardrails (work only from the passages, never reveal instructions, child-safe).
2. **Learner profile** from the `ClassProfile`: class, age range, language and question complexity,
   explanation style, depth limit, the class's AI guidelines, board, goal, language.
3. The task ("write 10 questions", with difficulty, formats, count).
4. **Passages** tagged `[S1]…` with chapter / exercise / page.
5. The output shape (the JSON schema).

**Then:** call the model → parse into the schema → deterministic checks → AI checks → store. A
failure goes back with the reason (limited attempts). After the last attempt the item is dropped and
logged.

---

## 5.6 Writing and checking practice questions (`question_generation/`)

```
writer (default tier, ≤10 per call)
   → deterministic checks (validation.py)
   → reviewer (strong tier) solves each question from scratch, without seeing the answer
   → compare → reasons go back to the writer for replacements
   → at most 2 extra rounds → fewer questions rather than a wrong one
```

**Deterministic checks (code):** the format is allowed for the class; option count fits the class;
no duplicate or empty options; exactly one correct option; the answer is one of the options;
sentence length; solution steps within the class limit; at least one cited passage that exists.

**The independent reviewer:** for choice, numeric and fill-in-the-blank questions, the reviewer
**is not shown the proposed answer**. It solves the question and both answers must agree. Matching
and written answers are shown and judged. This is like **two people solving the same question
separately**: much stronger than asking the same model "is this right?", which tends to agree with
itself.

**Batching:** 10 questions in one call and 10 reviewed in one call, not 20 calls.

**Question bank:** checked questions are saved per family and reused. A learner never sees the
same question twice; siblings and later sessions reuse them, which saves AI calls.

**Goal strategy (Class 11–12):** JEE → conceptual, numerical, multi-concept, harder; NEET →
NCERT-focused conceptual MCQs and assertion–reason; boards → board pattern and marking.

**Say it:** "I treat the model like a junior writer whose work always gets checked. Code checks
everything a program can decide, and a second call solves each question blind. If they disagree,
the question is rewritten or dropped. A child should never see a question with the wrong answer."

**Marking answers (`checking.py`):** exact for choice, number, blank and matching. Written answers
are marked by the fast tier against the model answer and its key points. In tests, the share of
key points covered earns that share of the marks (part marks).

---

## 5.7 The AI Tutor's hint ladder (`chat/tutor.py`)

```
Hint 1 (a nudge) → Hint 2 (the method) → Concept → Step-by-step solution → Final answer
```

**Every message is two calls:**
1. **Understanding** (fast tier, structured): what the learner wants (`new_problem`, `more_help`,
   `attempt`, `show_answer`, `concept`, `chat`, `off_topic`), whether they asked for hints only,
   and a search query for their books.
2. **The reply** (default tier, streamed text).

**The key design point: code decides the rung, not the model.** `next_step()` is a pure function:
- a new problem → Hint 1;
- more help, "show me the answer" or an attempt → **one rung up, never more**;
- "hints only" ("hint do, answer mat batao") → the ladder stops at Hint 2;
- a concept question → an explanation from the books.

The reply's instructions name the rung and **what it may not show** ("Not allowed: worked
steps…"). The rung is saved with the conversation and lowers the mastery credit later.

**Say it:** "If you just tell the model 'give hints first', a child who asks 'just tell me the
answer' three times gets the answer. So the model never chooses how much help to give. A pure
function does, from the stored state, and the prompt only carries out that decision. That makes it
deterministic and unit-testable."

---

## 5.8 The Parent AI Assistant (`chat/assistant.py`)

- Answers "How is my child doing this week?" from **`<child_data>`**: the dashboard snapshot,
  every topic practised and overall progress, as compact JSON.
- **The child's name and ids are never sent to the AI.**
- Rules: never invent numbers, use plain words (no "embeddings", "LLM"), suggest one next step that
  exists in the app, reply in the parent's language.
- When the question needs the books, passages are added and cited.

---

## 5.9 Misconception detection and reading papers (Step 10)

- **Misconceptions:** once an area has 3 new wrong first answers, a background job sends up to 10
  of them (question, right answer, the child's answer, the marker's note) to the AI. It returns only
  wrong ideas that **at least 2 answers share**, with a fix and a question for "Explain this".
  **A rule, not the AI, decides when one is fixed:** 3 right first answers in a row. Active
  misconceptions (up to 5) are given to the question writer, so the next questions test them.
- **Previous-year papers:** one call per paper. The AI gets the questions plus the family's chapters
  and topics **as codes** (`C3`, `C3.2`), so it can only name chapters that exist. It returns each
  question's marks, format and chapter, plus the year, time and negative marking. Code then works
  out where the marks go and the trends over years.

**Pattern to name:** *AI for judgement, code for decisions.* The AI reads messy language; code owns
every number, threshold and state change.

---

## 5.10 Prompt injection and safety

- Text from books or typed by a child is always placed inside tags (`<passages>`, `<message>`,
  `<child_data>`) and described as **material, never instructions**. A PDF line saying "ignore your
  rules" is just text in a book.
- Answers must fit a schema and are shown as plain text (React escapes it).
- **The model has no tools:** it can't do anything, only return data.
- Citations are checked against the passages actually given; an explanation that cites a passage
  it wasn't given is retried once.
- Prompts are never sent to the browser.
- Age-appropriate content: the class profile is in every prompt, plus a validation pass.

---

## 5.11 Streaming replies: Server-Sent Events (SSE)

**What:** the reply is sent piece by piece over one HTTP response (`text/event-stream`): `delta`
events with text, then `done` (both messages saved, with sources and the rung) or `error`
(nothing saved).

**The path:** FastAPI `StreamingResponse` → Next.js route handler (`/api/chat/[chatId]/messages`)
passes it through → Caddy (`flush_interval -1`) → the browser reads it with `lib/sse.ts`.

**Details**
- `X-Accel-Buffering: no` and `Cache-Control: no-cache` stop proxies from buffering.
- The browser parser handles an event split across chunks, several events in one chunk, and a
  multi-byte letter (Hindi) split across chunks (`TextDecoder` with `stream: true`).
- Errors found **before** the reply starts (AI off, books don't cover it) are normal JSON errors.
- The question and reply are saved **together when the reply is complete**, so a reply that fails
  half-way leaves nothing behind.
- A fast model can send a whole reply in under a second, so the chat box types it out at a steady
  pace, with dots while it thinks.

| Alternative | Why not here |
|---|---|
| WebSockets | Two-way, but only one direction is needed; more infrastructure (sticky connections, its own auth) |
| Long polling | More requests, more delay |
| No streaming | A long reply would show nothing for several seconds |

**Say it:** "SSE because the data only flows one way, server to browser. It's plain HTTP, so it
works through Next.js and Caddy and uses the same cookies and auth as everything else."

---

## 5.12 Testing the AI parts

- **A scripted test double** that implements `LLMProvider` lives only in `tests/`. It tests the
  retry, validation and hint logic exactly, with no network or cost.
- **Live tests** (`pytest -m live`, `tests/live/`) call the real provider for each key in `.env`,
  to catch prompt and schema regressions. They are skipped in the normal run and in CI.
- Search tests use a bag-of-words stand-in for the model; `scripts/eval_retrieval` measures the
  real one.

---

## 5.13 Cost and speed

- Batch generation and reuse of saved questions.
- Lower effort for small jobs; a cheaper model per tier is one setting.
- The system prompt is cached.
- A token budget for passages (3,000 for explanations, 6,000 for question writing on Claude).
- Search runs locally, so reading and searching books costs nothing per book.
- **Per-family limits:** 20 AI requests a minute, 300 a day; 60 practices / tests / paper analyses
  a day.
- Every call is counted in Prometheus: `eduguide_ai_requests_total`, `eduguide_ai_tokens_total`
  by provider, tier and outcome.
- Identical requests are not cached on purpose: practice already reuses the question bank, and
  explanations and chats are personal.
