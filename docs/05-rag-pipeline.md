# 5. RAG pipeline

RAG ("retrieval-augmented generation") means: before the AI writes anything, we look up the right
passages in the child's own books and give the AI only those. The whole PDF is **never** sent to
the model. Built in Steps 2 and 3.

There are two pipelines:

- **Reading a book** (once per upload): file → labelled pieces of text that can be searched.
- **Answering** (every request): request → the right pieces → AI → checked result with sources.

## 5.1 Reading a book

```
upload → check file → extract text → detect structure → make chunks → embed → index → ready
```

| # | Stage | What happens | Step |
|---|---|---|---|
| 1 | **Check file** | Real file type by content (not by extension), size and page limits, duplicate check by hash. Stored privately under a random name. | 2 |
| 2 | **Extract text** | Page by page, keeping page numbers and font sizes (headings are found through them). DOCX uses heading styles. Pages with no usable text go to OCR. | 2 |
| 3 | **Detect structure** | Chapters, topics, examples, exercises, individual questions, summaries — see 5.2. | 2 |
| 4 | **Make chunks** | Cut into pieces that follow the structure — see 5.3. | 2 |
| 5 | **Embed** | Each chunk becomes a vector, in batches. | 3 |
| 6 | **Index** | Vector index plus a keyword index. | 3 |

Each stage writes its progress on the `documents` row; the frontend shows it as a checklist. A
stage that fails records an error code and a parent-friendly message, and can be retried without
uploading again. Re-running a stage first removes what that stage produced before.

## 5.2 Detecting structure

Target shape (spec §14):

```
Book → Chapter → Topic / Concept / Example / Exercise → Question
                                                  └── Summary
```

Three sources of evidence, cheapest first:

1. **The PDF's own outline** (bookmarks), when it has one.
2. **Layout and patterns:** larger or bold lines, and patterns such as `Chapter 4`, `EXERCISE 2.3`,
   `Example 5`, numbered questions `1.` `(i)` `(a)`, and their Hindi forms (`अध्याय`, `प्रश्नावली`, `उदाहरण`).
3. **AI assistance only when 1 and 2 are unsure:** the model sees a list of candidate heading lines
   with page numbers (a few hundred tokens), not the book, and returns the outline as structured data.

The parent can correct the result (rename a chapter, fix a page range) on the book page. Getting
this right matters more than anything later: "Generate questions from Exercise 2.3" can only work
if we know where Exercise 2.3 is.

## 5.3 Chunking rules

- A chunk never crosses a chapter or exercise boundary.
- **One exercise question = one chunk. One worked example = one chunk.** They are never split and
  never merged with neighbours.
- Explanatory text is cut at paragraph boundaries into pieces of roughly 300–500 tokens, with a
  small overlap so a sentence cut in two is still found.
- Every chunk has a `content_type`: `concept`, `example`, `exercise_question`, `summary`, `other`.
- The text sent for embedding starts with a one-line label, e.g.
  `Class 8 · Mathematics · Chapter 2 Linear Equations · Exercise 2.3`, which makes short pieces
  (like a bare equation) findable.

Metadata stored with every chunk (spec §14, §35):

```json
{
  "document_id": "…", "book_id": "…", "owner_user_id": "…",
  "class_level": "class_8", "board": "cbse", "subject": "Mathematics",
  "chapter": "Linear Equations", "topic": "Solving equations", "exercise": "2.3",
  "content_type": "example", "page_start": 45, "page_end": 45, "language": "en"
}
```

## 5.4 Answering

The stages of spec §15 and what each one does here:

| # | Stage | What we do |
|---|---|---|
| 1 | Query understanding | Button actions ("practise Exercise 2.3") already carry exact filters — no AI needed. Free-text chat goes through a small, fast model that returns intent, subject / chapter / exercise if mentioned, and a clean search query. |
| 2 | Class / board / subject filter | Starts from the child's profile. **The owner filter is always added by the server** and cannot be widened by any request. |
| 3 | Query embedding | Same embedding model as the chunks. |
| 4 | Vector search | Nearest chunks **inside the filtered set**. |
| 5 | Metadata filtering | Class, board, subject, book, chapter, exercise, topic, content type — applied in the same SQL statement as the ranking, so nothing from another class or book can enter. |
| 6 | Top-K | About 30 candidates from vector search plus about 30 from keyword search, merged by rank. Keyword search catches exact things like "2.3" or a formula name. |
| 7 | Reranking | A reranker re-orders the candidates against the question and keeps the best 6–10. Optional (`none` = keep the merged order). |
| 8 | Context construction | Remove duplicates, join neighbours, restore book order, stay inside a token budget, tag each passage `[S1]`, `[S2]` with book / chapter / exercise / page. |
| 9 | LLM | Prompt = role and guardrails + class profile + task + passages. |
| 10 | Structured output | The model must answer in a JSON shape defined by a Pydantic model. |
| 11 | Validation | Shape, grounding in the passages, class-appropriateness, correctness — see [doc 6](06-llm-interfaces.md). Failed items are regenerated. |
| 12 | Final response | Result + `source` (chapter, exercise, page) + whether each question is original or generated. |

### Two ways to retrieve

Not every lookup needs vectors.

| Mode | Used for | How |
|---|---|---|
| **By place** | "10 questions from Exercise 2.3", "test on Chapters 1–3" | Plain filter on chapter / exercise, plus the concept and example chunks of the same topics. Exact and cheap. |
| **By meaning** | "Why do we flip the sign?", tutor and parent-assistant chat | Vector + keyword search inside the filtered set. |

Because filters are tight (one family, usually one chapter), the candidate set is small, so an
exact comparison is fast and perfectly accurate. An approximate vector index is only needed for
wide searches across many books; it is added for those, not relied on for correctness.

### When the books do not have the answer

If nothing is retrieved, or the best match is below a threshold, generation is **skipped** and the
response is: *"I couldn't find enough information in your uploaded material to answer this
reliably."* The AI is never asked to answer from memory and present it as the textbook.

## 5.5 Things that go wrong with Indian school PDFs

| Problem | Effect | Plan |
|---|---|---|
| Scanned books and photographed notes | No text at all | OCR per page (English + Hindi), only for pages that need it |
| Hindi PDFs made with old non-Unicode fonts | Text extracts as nonsense Latin characters | Detect by script statistics → treat the page as scanned → OCR |
| Maths: fractions, powers, roots, geometry figures | Extracted text loses the layout (`x2` instead of x²) | Flag maths-heavy pages; optional vision-model reading for them; keep the page image reference so the UI can show the original |
| One PDF per chapter (NCERT) | A "book" arrives as many files | Several documents per book; chapter number from file name and first page |
| Two-column pages, headers, footers, watermarks | Mixed-up reading order, noise in every chunk | Column-aware ordering; drop lines that repeat on most pages |
| Question in Hinglish, book in English or Hindi | The words do not match | Stage 1 rewrites the query in the book's language; a multilingual embedding model is used |
| Answer keys at the back of the book | Answers separated from questions | Link "Answers" sections to exercises by number when detected |

Library choice note for Step 2: the PDF reader sits behind an interface. Prefer permissively
licensed libraries (for example `pypdfium2`, `pdfplumber`). **PyMuPDF is AGPL-licensed** — fine for
experiments, but a closed-source commercial product needs its paid licence.

## 5.6 Measuring quality

Changing a chunk size or a model without measuring is guessing. From Step 3 the repository carries
a small evaluation set built from a sample book:

- **Retrieval:** for about 50 questions with known source pages — is the right chunk in the top 5? (recall@5, MRR)
- **Filtering:** requests for one exercise never return chunks from another exercise or class (must be 100%).
- **Generation (Step 4):** share of questions that pass validation first time; share judged correct by a human spot-check.

Each run of a request logs retrieval latency, number of candidates, scores, LLM latency and token
use (spec §44) — with ids only, never the child's text.
