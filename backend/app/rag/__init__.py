"""Turning uploaded books into something the AI can look things up in.

  ingestion/  Step 2 - check the file, read the text (OCR for scanned pages), find chapters,
              topics, exercises, examples and questions, cut the book into labelled chunks
  ocr.py      Step 2 - the OCR provider interface and the Tesseract adapter
  (Step 3)    embeddings, the vector index, filtered retrieval, reranking, context building

Design: docs/05-rag-pipeline.md
"""
