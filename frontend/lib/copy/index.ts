import { en, type Copy } from "@/lib/copy/en";
import { hi } from "@/lib/copy/hi";
import { hinglish } from "@/lib/copy/hinglish";
import type { Reason } from "@/lib/types";

/*
 * The languages of the screens. The words of each are in a file of their own with the same shape as
 * en.ts. To add one (say Marathi): write mr.ts, add it here, and switch it on in the backend
 * (`content_enabled` in app/core/languages.py), which checks the language an account may choose.
 */
const DICTIONARIES = { en, hi, hinglish } satisfies Record<string, Copy>;

export type ScreenLanguage = keyof typeof DICTIONARIES;
export type { Copy };

export const SCREEN_LANGUAGES = Object.keys(DICTIONARIES) as ScreenLanguage[];

/** The brand is not translated. */
export const APP_NAME = "EduGuide AI";

/** A language code as a screen language: English for anything the screens don't have. */
export function screenLanguage(code: string | null | undefined): ScreenLanguage {
  return code && code in DICTIONARIES ? (code as ScreenLanguage) : "en";
}

export function copyFor(language: ScreenLanguage): Copy {
  return DICTIONARIES[language];
}

/** Something the backend says in English, by its code: in the screen language where it has words for it. */
export function said(words: Record<string, string>, code: string, english: string): string {
  return words[code] ?? english;
}

/** A learner's or a book's class in words ("Class 7", "कक्षा 7"). */
export function classLabel(copy: Copy, of: { class_level: string; class_label: string }): string {
  return said(copy.options.classes, of.class_level, of.class_label);
}

/** Why a recommendation or a plan task was chosen, in words. */
export function reasonText(copy: Copy, reason: Reason): string {
  return (copy.reasons[reason.code] ?? copy.reasons.planned)(reason);
}
