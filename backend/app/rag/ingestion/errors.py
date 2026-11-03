"""What can go wrong while checking and reading a file, in words a parent understands.

Upload problems are answered at once with an HTTP error. Problems found later, while the book is
being read in the background, are stored on the document as `error_code`; the API turns the code
into the message below.
"""

from app.core.errors import AppError


class UploadRejectedError(AppError):
    status_code = 422
    code = "upload_rejected"
    message = "We couldn't accept this file."


class UnsupportedFileError(UploadRejectedError):
    status_code = 415
    code = "unsupported_file_type"
    message = "Please upload a PDF, a Word document (.docx) or a text file (.txt)."


class FileTooLargeError(UploadRejectedError):
    status_code = 413
    code = "file_too_large"
    message = "This file is too large."


class ProcessingError(Exception):
    """Reading the document failed in a way we understand. `code` is stored on the document."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_TRY_ANOTHER = "We couldn't process this document. Please try another PDF."

PROCESSING_ERROR_MESSAGES: dict[str, str] = {
    "no_text_found": "We couldn't find any text in this document. Please try another PDF.",
    "scanned_document": (
        "This looks like a scanned or photographed book, and reading those is not switched on yet. "
        "Please try a PDF where you can select the text."
    ),
    "file_missing": "The uploaded file could not be found. Please upload it again.",
}


def processing_error_message(code: str) -> str:
    """Anything not listed (file_unreadable, processing_failed...) gets the general message."""
    return PROCESSING_ERROR_MESSAGES.get(code, _TRY_ANOTHER)
