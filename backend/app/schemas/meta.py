"""Schemas for the form options the frontend needs before anyone signs in."""

from pydantic import BaseModel

from app.class_profiles import UIMode
from app.core.enums import ClassLevel, Goal, LearningBand, Stream
from app.schemas.common import OptionItem


class LanguageOption(BaseModel):
    code: str
    label: str
    native_label: str


class ClassOption(BaseModel):
    """The parts of a class profile the child form needs."""

    class_level: ClassLevel
    label: str
    band: LearningBand
    age_range: str
    ui_mode: UIMode
    requires_stream: bool
    available_goals: list[Goal]
    default_goal: Goal
    suggested_subjects: list[str]
    suggested_subjects_by_stream: dict[Stream, list[str]] | None


class UploadLimits(BaseModel):
    """What the upload form accepts, so it can warn before sending a file."""

    accepted_types: list[str]
    accepted_extensions: list[str]
    max_file_mb: int
    max_pdf_pages: int
    max_files_per_book: int


class OnboardingOptions(BaseModel):
    classes: list[ClassOption]
    boards: list[OptionItem]
    streams: list[OptionItem]
    goals: list[OptionItem]
    languages: list[LanguageOption]
    mediums: list[LanguageOption]
    material_types: list[OptionItem]
    upload: UploadLimits
