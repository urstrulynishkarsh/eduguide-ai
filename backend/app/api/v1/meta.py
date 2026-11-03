"""Form options and class profiles. Public: needed before anyone has an account."""

from fastapi import APIRouter

from app.class_profiles import ClassProfile, all_class_profiles, get_class_profile
from app.core.enums import BOARD_LABELS, GOAL_LABELS, STREAM_LABELS, ClassLevel
from app.core.languages import Language, content_languages, medium_options
from app.schemas.common import OptionItem
from app.schemas.meta import ClassOption, LanguageOption, OnboardingOptions

router = APIRouter(prefix="/meta", tags=["Meta"])


def _language_option(language: Language) -> LanguageOption:
    return LanguageOption(code=language.code, label=language.label, native_label=language.native_label)


@router.get("/options", response_model=OnboardingOptions, summary="Everything the sign-up forms need")
async def onboarding_options() -> OnboardingOptions:
    """Classes (with the rules that depend on them), boards, streams, goals and languages."""
    return OnboardingOptions(
        classes=[ClassOption.model_validate(profile.model_dump()) for profile in all_class_profiles()],
        boards=[OptionItem(code=board.value, label=label) for board, label in BOARD_LABELS.items()],
        streams=[OptionItem(code=stream.value, label=label) for stream, label in STREAM_LABELS.items()],
        goals=[OptionItem(code=goal.value, label=label) for goal, label in GOAL_LABELS.items()],
        languages=[_language_option(language) for language in content_languages()],
        mediums=[_language_option(language) for language in medium_options()],
    )


@router.get(
    "/classes/{class_level}",
    response_model=ClassProfile,
    summary="The full class profile (AI and UI rules) for one class",
)
async def class_profile(class_level: ClassLevel) -> ClassProfile:
    return get_class_profile(class_level)
