"""Turning uploaded books into something the AI can look things up in.

  ingestion/     Step 2 - check the file, read the text (OCR for scanned pages), find chapters,
                 topics, exercises, examples and questions, cut the book into labelled chunks,
                 embed them (Step 3)
  ocr.py         the OCR provider interface and the Tesseract adapter
  embeddings.py  the search-model interface and the local multilingual model
  indexing.py    re-embedding stale chunks
  retrieval.py   filtered vector + keyword search, context with [S1] tags
  answering.py   query understanding and grounded explanations

Design: docs/05-rag-pipeline.md
"""
