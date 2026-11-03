"""Stage 1 - check the file before anything else touches it.

* The real type is decided from the content, never from the file name or the browser's claim.
* Size, page count and (for DOCX) the unpacked size are limited.
* Password-protected and damaged files are refused with a clear message.

Runs in a worker thread (it does blocking file and PDF work).
"""

import codecs
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from lxml import etree

from app.core.enums import FileKind
from app.rag.ingestion.errors import UnsupportedFileError, UploadRejectedError
from app.rag.ingestion.pdf_lock import PDFIUM_LOCK

MIME_TYPES: dict[FileKind, str] = {
    FileKind.PDF: "application/pdf",
    FileKind.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FileKind.TXT: "text/plain",
}

_DOCX_MAIN_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
_MAX_DOCX_UNPACKED_BYTES = 300 * 1024 * 1024
_MAX_DOCX_ENTRIES = 5000


@dataclass(frozen=True, slots=True)
class CheckedFile:
    kind: FileKind
    mime_type: str
    page_count: int | None


def _pdf_page_count(path: Path, max_pages: int) -> int:
    try:
        with PDFIUM_LOCK:
            pdf = pdfium.PdfDocument(path)
            try:
                pages = len(pdf)
            finally:
                pdf.close()
    except pdfium.PdfiumError as exc:
        if getattr(exc, "err_code", None) == pdfium.raw.FPDF_ERR_PASSWORD:
            raise UploadRejectedError(
                "This PDF is protected with a password. Please upload a copy without a password.",
                code="password_protected",
            ) from None
        raise UploadRejectedError(
            "This PDF seems to be damaged. Please try another copy.", code="file_unreadable"
        ) from None
    if pages == 0:
        raise UploadRejectedError("This PDF has no pages.", code="empty_file")
    if pages > max_pages:
        raise UploadRejectedError(
            f"This PDF has {pages} pages. Books can have up to {max_pages} pages - "
            "please upload it in parts (for example one file per chapter).",
            code="too_many_pages",
        )
    return pages


def _check_docx(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if (
                len(entries) > _MAX_DOCX_ENTRIES
                or sum(e.file_size for e in entries) > _MAX_DOCX_UNPACKED_BYTES
            ):
                raise UploadRejectedError("This Word document is too large to read.", code="file_too_large")
            names = {entry.filename for entry in entries}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise UnsupportedFileError()
            # No entity expansion and no network access: an uploaded file is never trusted.
            parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
            content_types = etree.fromstring(archive.read("[Content_Types].xml"), parser)
    except (zipfile.BadZipFile, etree.XMLSyntaxError, OSError):
        raise UnsupportedFileError() from None
    main_types = {
        element.get("ContentType")
        for element in content_types
        if element.get("PartName") == "/word/document.xml"
    }
    # .docm (macros) and .dotx (templates) have a different main part; only plain .docx is accepted.
    if main_types != {_DOCX_MAIN_CONTENT_TYPE}:
        raise UnsupportedFileError()


def decode_text_file(data: bytes) -> str:
    """UTF-8 (with or without BOM) or UTF-16 with BOM. Anything else is refused."""
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")
    if b"\x00" in data:
        raise UnsupportedFileError()  # binary data, not text
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UploadRejectedError(
            "We couldn't read this text file. Please save it as UTF-8 and upload it again.",
            code="text_encoding_unsupported",
        ) from None


def _check_text(path: Path) -> None:
    text = decode_text_file(path.read_bytes())
    if not text.strip():
        raise UploadRejectedError("This file is empty.", code="empty_file")
    control = sum(1 for ch in text[:20000] if ord(ch) < 32 and ch not in "\n\r\t\f")
    if control > 20:
        raise UnsupportedFileError()


# Files people often try to upload by mistake, with a more helpful answer than "unsupported".
_KNOWN_OTHER_TYPES: tuple[tuple[bytes, str], ...] = (
    (
        b"\xd0\xcf\x11\xe0",
        "This is an old Word (.doc) file. Please save it as .docx or PDF and upload again.",
    ),
    (b"\x89PNG", "Photos of pages can't be uploaded directly yet. Please put them into a PDF first."),
    (b"\xff\xd8\xff", "Photos of pages can't be uploaded directly yet. Please put them into a PDF first."),
)


def sniff_kind(head: bytes) -> FileKind:
    """Guess the type from the first bytes. Text is only a guess here; `_check_text` confirms it."""
    for signature, message in _KNOWN_OTHER_TYPES:
        if head.startswith(signature):
            raise UnsupportedFileError(message)
    if b"%PDF-" in head[:1024]:
        return FileKind.PDF
    if head.startswith(b"PK\x03\x04"):
        return FileKind.DOCX  # any zip; `_check_docx` makes sure it really is a Word document
    return FileKind.TXT


def check_file(path: Path, *, max_pdf_pages: int) -> CheckedFile:
    """Decide the type and refuse anything we cannot or should not read."""
    if path.stat().st_size == 0:
        raise UploadRejectedError("This file is empty.", code="empty_file")
    with path.open("rb") as file:
        head = file.read(4096)

    kind = sniff_kind(head)
    page_count: int | None = None
    if kind is FileKind.PDF:
        page_count = _pdf_page_count(path, max_pdf_pages)
    elif kind is FileKind.DOCX:
        _check_docx(path)
    else:
        _check_text(path)
    return CheckedFile(kind=kind, mime_type=MIME_TYPES[kind], page_count=page_count)
