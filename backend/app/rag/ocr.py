"""Reading text from page images (scanned books, photographed notes).

Business code depends only on `OCRProvider`. The first adapter uses Tesseract, a free program
that must be installed on the server (with the Hindi language pack). A cloud OCR service can be
added later as one more adapter and the `OCR_PROVIDER` setting.

With `OCR_PROVIDER=none` there is no OCR: scanned pages are skipped and a fully scanned
document fails with the error code `scanned_document`. Nothing is ever made up.
"""

import asyncio
import logging
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OCRPage:
    lines: list[str]


class OCRError(Exception):
    pass


class OCRProvider(Protocol):
    async def read_page(self, image_png: bytes, *, languages: Sequence[str]) -> OCRPage:
        """Read one page image. `languages` are Tesseract-style codes, e.g. ["hin", "eng"]."""


class TesseractOCR:
    """Runs the `tesseract` command line program. The page image goes in on stdin."""

    def __init__(self, command: str, timeout_seconds: float = 180) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds

    async def read_page(self, image_png: bytes, *, languages: Sequence[str]) -> OCRPage:
        process = await asyncio.create_subprocess_exec(
            self.command,
            "stdin",
            "stdout",
            "-l",
            "+".join(languages),
            "--psm",
            "3",  # fully automatic page layout
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(image_png), self.timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise OCRError("Tesseract took too long on one page.") from None
        if process.returncode != 0:
            # stderr names a missing language pack, for example; it never contains page text.
            raise OCRError(f"Tesseract failed: {stderr.decode(errors='replace')[:300]}")
        text = stdout.decode("utf-8", errors="replace")
        return OCRPage(lines=[line for line in text.splitlines() if line.strip()])


@lru_cache
def get_ocr_provider() -> OCRProvider | None:
    """The configured OCR provider, or None when OCR is switched off or not installed."""
    settings = get_settings()
    if settings.ocr_provider == "none":
        return None
    if shutil.which(settings.tesseract_cmd) is None:
        logger.error(
            "OCR_PROVIDER=tesseract but '%s' was not found. Scanned pages will be skipped. "
            "Install it (macOS: brew install tesseract tesseract-lang) or set TESSERACT_CMD.",
            settings.tesseract_cmd,
        )
        return None
    return TesseractOCR(settings.tesseract_cmd)


def ocr_languages_for(book_language: str) -> list[str]:
    """The book's own language first; Tesseract does better when the main language leads."""
    configured = [code for code in get_settings().ocr_languages.split("+") if code]
    preferred = {"hi": "hin", "en": "eng"}.get(book_language)
    if preferred and preferred in configured:
        configured.remove(preferred)
        configured.insert(0, preferred)
    return configured
