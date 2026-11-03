"""Child / learner schemas."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, computed_field, field_validator

from app.class_profiles import get_class_profile
from app.core.enums import Board, ClassLevel, Goal, LearningBand, Stream
from app.core.languages import DEFAULT_LANGUAGE, is_content_language, is_medium

StudentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Age = Annotated[int, Field(ge=2, le=25)]

MAX_SUBJECTS = 15
MAX_SUBJECT_LENGTH = 60


class StudentProfileIn(BaseModel):
    """The "Add Child" form, minus name and age. `class_level` drives everything else."""

    class_level: ClassLevel
    board: Board
    board_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = Field(
        default=None, description='Name of the board when `board` is "state" or "other", e.g. "MP Board".'
    )
    medium: str = Field(default=DEFAULT_LANGUAGE, description="Medium of instruction at school.")
    primary_language: str = Field(
        default=DEFAULT_LANGUAGE, description="Language the AI should use with this learner."
    )
    stream: Stream | None = Field(
        default=None, description="Required for Class 11-12, not allowed otherwise."
    )
    goal: Goal | None = Field(default=None, description="Left empty, the default goal of the class is used.")
    subjects: list[str] = Field(default_factory=list, max_length=MAX_SUBJECTS)

    @field_validator("medium")
    @classmethod
    def _medium_must_be_known(cls, value: str) -> str:
        if not is_medium(value):
            raise ValueError("Unknown medium of instruction.")
        return value

    @field_validator("primary_language")
    @classmethod
    def _language_must_be_supported(cls, value: str) -> str:
        if not is_content_language(value):
            raise ValueError("This language is not available yet.")
        return value

    @field_validator("subjects")
    @classmethod
    def _clean_subjects(cls, value: list[str]) -> list[str]:
        """Trim, drop blanks and remove repeats (ignoring upper/lower case), keeping the order."""
        cleaned: list[str] = []
        seen: set[str] = set()
        for subject in value:
            name = " ".join(subject.split())
            if not name:
                continue
            if len(name) > MAX_SUBJECT_LENGTH:
                raise ValueError(f"A subject name can be at most {MAX_SUBJECT_LENGTH} characters.")
            if name.casefold() not in seen:
                seen.add(name.casefold())
                cleaned.append(name)
        return cleaned


class StudentCreate(BaseModel):
    name: StudentName
    age: Age | None = None
    profile: StudentProfileIn


class StudentUpdate(BaseModel):
    """Only the fields that are sent are changed."""

    name: StudentName | None = None
    age: Age | None = None

    @field_validator("name")
    @classmethod
    def _name_cannot_be_cleared(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("A name is required.")
        return value


class StudentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_level: ClassLevel
    board: Board
    board_name: str | None
    medium: str
    primary_language: str
    stream: Stream | None
    goal: Goal
    subjects: list[str]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def class_label(self) -> str:
        return self.class_level.label

    @computed_field  # type: ignore[prop-decorator]
    @property
    def band(self) -> LearningBand:
        return get_class_profile(self.class_level).band


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    age: int | None
    has_own_login: bool = Field(description="True for a student who signed up alone.")
    profile: StudentProfileOut | None = Field(description="Empty until class details are filled in.")
    created_at: datetime
    updated_at: datetime
