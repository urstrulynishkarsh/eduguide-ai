"""Stage 1: the real file type comes from the content, and bad files are refused clearly."""

import io
import zipfile
from pathlib import Path

import pytest
from reportlab.lib import pdfencrypt
from reportlab.pdfgen import canvas

from app.core.enums import FileKind
from app.rag.ingestion.errors import UnsupportedFileError, UploadRejectedError
from app.rag.ingestion.file_checks import check_file, decode_text_file
from tests.samples import NOTES_TEXT, make_docx, make_pdf


def _write(tmp_path: Path, data: bytes, name: str = "upload.bin") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_pdf_is_recognised_by_content_and_pages_are_counted(tmp_path: Path):
    checked = check_file(_write(tmp_path, make_pdf(), "notes.txt"), max_pdf_pages=100)  # wrong extension
    assert checked.kind is FileKind.PDF
    assert checked.mime_type == "application/pdf"
    assert checked.page_count == 4


def test_docx_and_text_files_are_accepted(tmp_path: Path):
    assert check_file(_write(tmp_path, make_docx()), max_pdf_pages=100).kind is FileKind.DOCX
    text = check_file(_write(tmp_path, NOTES_TEXT.encode("utf-8")), max_pdf_pages=100)
    assert text.kind is FileKind.TXT
    assert text.page_count is None


def test_pdf_with_too_many_pages_is_refused(tmp_path: Path):
    with pytest.raises(UploadRejectedError) as error:
        check_file(_write(tmp_path, make_pdf()), max_pdf_pages=3)
    assert error.value.code == "too_many_pages"
    assert "4 pages" in error.value.message


def test_password_protected_pdf_is_refused(tmp_path: Path):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, encrypt=pdfencrypt.StandardEncryption("secret"))
    pdf.drawString(72, 750, "Secret page")
    pdf.showPage()
    pdf.save()

    with pytest.raises(UploadRejectedError) as error:
        check_file(_write(tmp_path, buffer.getvalue()), max_pdf_pages=100)
    assert error.value.code == "password_protected"


def test_damaged_pdf_is_refused(tmp_path: Path):
    with pytest.raises(UploadRejectedError) as error:
        check_file(_write(tmp_path, b"%PDF-1.7\nthis is not really a pdf"), max_pdf_pages=100)
    assert error.value.code == "file_unreadable"


def test_zip_that_is_not_a_word_document_is_refused(tmp_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "hello")
    with pytest.raises(UnsupportedFileError):
        check_file(_write(tmp_path, buffer.getvalue()), max_pdf_pages=100)


@pytest.mark.parametrize(
    ("data", "hint"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, "PDF"),
        (b"\xff\xd8\xff\xe0" + b"\x00" * 20, "PDF"),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 20, ".docx"),
    ],
)
def test_common_wrong_files_get_a_helpful_message(tmp_path: Path, data: bytes, hint: str):
    with pytest.raises(UnsupportedFileError) as error:
        check_file(_write(tmp_path, data), max_pdf_pages=100)
    assert hint in error.value.message


def test_binary_data_is_not_text(tmp_path: Path):
    with pytest.raises(UnsupportedFileError):
        check_file(_write(tmp_path, b"abc\x00\x01\x02def" * 10), max_pdf_pages=100)


def test_empty_file_is_refused(tmp_path: Path):
    with pytest.raises(UploadRejectedError) as error:
        check_file(_write(tmp_path, b""), max_pdf_pages=100)
    assert error.value.code == "empty_file"


def test_text_encodings():
    assert decode_text_file("भिन्न".encode()) == "भिन्न"
    assert decode_text_file("﻿hello".encode()) == "hello"  # UTF-8 with BOM
    assert decode_text_file("नमस्ते".encode("utf-16")) == "नमस्ते"  # UTF-16 with BOM
    with pytest.raises(UploadRejectedError) as error:
        decode_text_file("café".encode("latin-1"))
    assert error.value.code == "text_encoding_unsupported"
