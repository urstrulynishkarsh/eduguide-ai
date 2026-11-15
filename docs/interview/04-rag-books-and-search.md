# 4. Reading books and searching them (RAG)

---

## 4.1 RAG in one minute

**RAG (retrieval-augmented generation):** before the AI writes anything, look up the right
passages in the child's own books and give the AI **only those**. The whole PDF is never sent.

**Why RAG here**
- **Grounding:** explanations and questions match *this* child's book, chapter and page, with
  citations (`[S1]` → book, chapter, page).
- **No made-up textbook facts.** If search finds nothing good enough, the app answers
  *"I couldn't find enough information in your uploaded material"* instead of guessing.
- **Cost:** a few thousand tokens of passages instead of a 300-page book in every request.
- **Privacy:** only the passages needed go to the AI provider.

| Alternative | Why not here |
|---|---|
| Send the whole book in a long-context model | Expensive on every request; slower; harder to cite pages; more of the book leaves the server |
| Fine-tune a model on the books | Every family has different books; fine-tuning is slow and costly and still makes things up |
| No retrieval (the model's own knowledge) | Doesn't match the child's book or board; can't cite pages; makes things up |

There are **two pipelines**:
- **Reading a book** (once per upload): file → labelled, searchable chunks.
- **Answering** (every request): request → right chunks → AI → checked result with sources.

---

## 4.2 Reading a book: the stages

```
upload → check file → extract text → detect structure → make chunks → embed → index → ready
```

Each stage writes its progress on the `documents` row. The parent sees it as a checklist in plain
words ("✓ Reading your book", "✓ Finding the chapters"…). A failed stage records an error code and
a friendly message, and can be retried without uploading again. Re-running a stage first removes
what it produced before, so stages are **idempotent**.

### Stage 1: checking the file (`rag/ingestion/file_checks.py`)

- **The real type from the content, not the extension:** PDF header, DOCX = a zip with a Word main
  part, text = valid UTF-8 / UTF-16.
- Refuses password-protected, damaged, empty, oversized (50 MB) and over-long files, with a message
  that says what to do ("save it as .docx", "put the photos into a PDF").
- **DOCX safety:** the unpacked size is limited (zip bombs), and the XML is parsed **without
  entities or network access** (XXE and "billion laughs" attacks).
- **Duplicates by hash:** the same file can't be added twice to one book.
- Stored privately **under a random name**, outside anything the web server serves.

---

## 4.3 pypdfium2 (reading PDFs)

**What:** Python bindings for **PDFium**, the PDF engine inside Google Chrome. BSD / Apache licence.

**Why here**
- Text **line by line with font size and boldness**: that is how headings are found (larger or bold
  lines).
- The PDF's **outline (bookmarks)**, the best evidence for chapters when it exists.
- **Renders pages as images** for OCR.
- Fast (C++) and **permissively licensed**.

| Alternative | Good at | Why not here |
|---|---|---|
| **PyMuPDF (fitz)** | Fast, very capable | **AGPL licence**: a closed-source commercial product would need a paid licence |
| pdfplumber (pdfminer.six) | Precise layout and tables, MIT | Pure Python, slower on big books; no page rendering for OCR |
| pypdf | Pure Python, simple | Weaker text extraction, no font details |
| Unstructured / LlamaParse / cloud document AI | Clever layout parsing | Cost per page; sends children's books to a third party |

**Say it:** "I picked pypdfium2 over PyMuPDF because of licensing: PyMuPDF is AGPL. pypdfium2 gives
me font sizes for finding headings and page images for OCR, under a BSD licence."

---

## 4.4 python-docx and lxml (Word files)

- **python-docx** reads `.docx` files: paragraphs with their **heading styles** (Heading 1 → a
  chapter) and tables.
- **lxml** parses XML safely. It is configured to **never resolve entities or load anything from
  the network**, which blocks XXE (reading server files through XML) and entity-expansion bombs.

| Alternative | Why not here |
|---|---|
| docx2txt / mammoth | Lose the heading styles that show the structure |
| Converting with LibreOffice | A large system dependency and a slow subprocess |

Plain text files are read directly: Markdown `#` lines are headings, and a form feed starts a new page.

---

## 4.5 Tesseract OCR (+ Pillow)

**What:** a free, open-source OCR engine with language packs (English + Hindi here). Pillow handles
the page images.

**Why here**
- Scanned books and photographed notes have **no text layer**.
- **Old non-Unicode Hindi fonts** extract as Latin gibberish. The extractor checks script statistics
  on each page; a page with fewer than 25 letters, or one that looks like a legacy font, goes to OCR.
- **Only the pages that need it** go to OCR (it is slow), rendered at 300 dpi, book language first.
- Free, offline, and children's books never leave the server.
- **Off by default** (`OCR_PROVIDER=none`): Tesseract is a system program, not a Python package.
  Without it, a scanned book gets a clear message instead of empty results. The Docker image
  installs it with the Hindi pack.

| Alternative | Good at | Why not here |
|---|---|---|
| Google Cloud Vision / AWS Textract / Azure Document Intelligence | Higher accuracy, handwriting, tables | Cost per page; children's material sent to a cloud |
| PaddleOCR / EasyOCR | Good accuracy, many languages | Heavy deep-learning dependencies (PyTorch / Paddle) |
| A vision LLM (Claude, GPT) | Reads maths and layout well | Cost per page; planned only for maths-heavy pages |

It sits behind `OCRProvider`, so a cloud OCR is one adapter away.

---

## 4.6 Finding the structure (`structure.py`)

Target: **Book → Chapter → Topic / Example / Exercise → Question**, plus summaries.

Evidence, cheapest first:
1. **The PDF's own outline** (bookmarks).
2. **Layout and patterns:** large or bold lines; `Chapter 4`, `EXERCISE 2.3`, `Example 5`, `1.`,
   `(i)`, `(a)`, and the Hindi forms (`अध्याय`, `प्रश्नावली`, `उदाहरण`).
3. **The file name** for NCERT books (`jemh102.pdf` → chapter 2).

Clean-up: lines that repeat at the top or bottom of at least 40 % of pages (running headers and
footers) and bare page numbers are removed. Contents pages and answer keys are skipped.

**Previous-year papers** are read differently: one file = one paper; `SECTION A`, `Part A –
Physics`, `खण्ड अ` are sections; every numbered question is kept with its section's instructions.

**Why this matters:** "practise Exercise 2.3" only works if the app knows exactly where Exercise 2.3
is. The parent can also fix a chapter's name or page range.

---

## 4.7 Chunking

**Rules**
- A chunk **never crosses a chapter or exercise boundary**.
- **One exercise question = one chunk. One worked example = one chunk.** Never split, never merged.
- Explanations are cut at paragraph boundaries into **about 300–500 tokens with a small overlap**,
  so a sentence cut in two is still found.
- Every chunk has a `content_type`: `concept`, `example`, `exercise_question`, `summary`, `other`.
- The text sent for embedding starts with a **label line**, e.g.
  `Class 8 · Mathematics · Chapter 2 Linear Equations · Exercise 2.3`. This makes short pieces (a
  bare equation) findable.
- Metadata on each chunk: owner, book, class, board, subject, chapter, topic, exercise, content
  type, pages, language.

**Why structure-aware chunking instead of fixed-size chunks?** Fixed windows cut questions in half
and mix two exercises in one chunk, which breaks "practise Exercise 2.3" and gives the AI half a
question. Following the book's structure keeps each unit whole and citable.

| Alternative | Why not here |
|---|---|
| Fixed-size chunks (e.g. 512 tokens) | Splits questions and examples; mixes exercises |
| Semantic chunking (split where embeddings change) | Costs an embedding per sentence; ignores the book's own structure, which is the best signal |
| LangChain / LlamaIndex text splitters | Generic; don't know what "Exercise 2.3" or `प्रश्नावली` is |

---

## 4.8 Embeddings: multilingual-e5-base via fastembed (ONNX)

**What:** `intfloat/multilingual-e5-base` turns text into a **768-number vector**; similar meanings
give nearby vectors. MIT licence, reads up to 512 tokens, about 1 GB. **fastembed** runs it through
**ONNX Runtime**, with no PyTorch.

**Why here**
- **Multilingual:** an English, Hindi or **Hinglish** question finds English or Hindi passages.
- **Runs on the server:** no API key, **no cost per book**, and children's books aren't sent out for
  embedding.
- **ONNX, not PyTorch:** a far smaller install, fits a laptop with 8 GB of memory, CPU is enough.
- E5 models expect `"query: "` before questions and `"passage: "` before stored text, and the code
  adds them.
- The model is loaded lazily, once, behind an `asyncio.Lock`, and embedding runs in
  `asyncio.to_thread` so it never blocks the event loop.

| Alternative | Good at | Why not here |
|---|---|---|
| OpenAI `text-embedding-3` | High quality, simple API | Cost per book; a key; book text goes to a third party |
| Cohere `embed-multilingual` | Strong multilingual quality | Same: paid and external |
| BGE-M3 | Better multilingual quality, 8k tokens | Needs PyTorch and about 2.3 GB; too heavy for an 8 GB laptop |
| all-MiniLM-L6 (sentence-transformers) | Tiny and fast | English only: Hindi and Hinglish fail |
| sentence-transformers (any model) | The usual library | Pulls in PyTorch (GBs); fastembed's ONNX path is lighter |

**Say it:** "Hindi and Hinglish support ruled out English-only models, and privacy plus cost ruled
out embedding APIs. multilingual-e5-base through ONNX runs on a normal server CPU with no per-book
cost, and I measured it on Hindi and Hinglish questions before committing."

**Follow-up: "What is the similarity threshold?"** 0.76. e5 scores cluster high (even unrelated
text scores about 0.72), so I tuned it with the evaluation: the lowest covered question scored 0.766
and the highest off-topic one 0.752. It separates them, though narrowly on a small sample. Below
the threshold the answer is `insufficient_context`.

---

## 4.9 Hybrid search and reciprocal rank fusion (`rag/retrieval.py`)

**Two ways to retrieve:**

| Mode | Used for | How |
|---|---|---|
| **By place** | "10 questions from Exercise 2.3", "a test on Chapter 4" | A plain filter on chapter / exercise, in book order. Exact and cheap. If it's over the token budget, chunks are taken evenly across the chapter |
| **By meaning** | "Why do we flip the sign?", tutor and assistant chat | Vector + keyword search inside the filtered set |

**Search by meaning, step by step**
1. **Query understanding** (fast AI tier): is it on topic? Rewrite it as a clean search query **in
   the books' language** (a Hinglish question becomes English or Hindi).
2. **Filter** (always includes the family's id, added by the server).
3. **Vector search:** top 30 by cosine distance.
4. **Keyword search:** top 30 by `ts_rank`.
5. **Reciprocal rank fusion (RRF):** each chunk scores `Σ 1 / (60 + rank)` over both lists.
6. **Context building:** drop duplicates, stay inside **3,000 tokens**, put passages back **in book
   order**, tag them `[S1]`, `[S2]`…
7. If the best similarity is under 0.76 → `insufficient_context`, and the AI isn't called.

**Why RRF?** Cosine similarity and `ts_rank` are on different scales and can't simply be added.
RRF uses only the **rank** in each list, so no score normalisation or tuning is needed. k = 60 is
the standard constant from the original paper (Cormack et al., 2009).

| Alternative | Why not here |
|---|---|
| Vector search only | Misses exact things: "2.3", formula names, rare terms |
| Keyword search only | Misses meaning and cross-language questions (Hinglish → English) |
| Weighted sum of normalised scores | Needs tuning and breaks when score ranges shift |
| A cross-encoder reranker (e.g. bge-reranker, Cohere Rerank) | More latency and cost; the evaluation shows no need yet. It would slot in after fusion |

---

## 4.10 Measuring search quality

`python -m scripts.eval_retrieval` runs **18 questions** (English, Hinglish, Hindi) with a known
answering passage, plus **4 off-topic** ones, on the sample chapter.

- **Recall@5 = 1.00:** the right passage is always in the top 5.
- **MRR = 0.96** (mean reciprocal rank): it is first in 17 of 18.
- **Filtering:** a request for one exercise must never return another exercise's or class's chunks
  (must be 100 %).

**Say it:** "I don't change chunk size or models without measuring. There's a small evaluation set;
recall@5 is 1.00 and MRR is 0.96. That's why there's no reranker yet. The honest weakness is that
the set is small, and it needs to grow with real books."

**Follow-up: "How would you improve retrieval?"** Grow the evaluation set from real usage first.
Then, in order: a reranker; better maths extraction (`x2` instead of x²) with a vision model for
maths-heavy pages; reading order for two-column pages; linking answer keys to exercises.
