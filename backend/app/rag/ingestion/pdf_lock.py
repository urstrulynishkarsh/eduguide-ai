"""PDFium (the PDF engine) is not thread-safe, so every call into it holds this lock."""

import threading

PDFIUM_LOCK = threading.RLock()
