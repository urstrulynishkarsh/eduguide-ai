"use client";

import { Languages } from "lucide-react";
import { useTransition } from "react";

import { useCopy } from "@/components/copy-provider";
import { chooseLanguage } from "@/lib/actions/auth";
import { copyFor, SCREEN_LANGUAGES } from "@/lib/copy";

/** "🌐 हिन्दी ▾" — the language of the screens, each named in its own words. */
export function LanguagePicker() {
  const copy = useCopy();
  const [pending, startTransition] = useTransition();
  return (
    <label className="flex items-center gap-1.5 text-sm">
      <Languages aria-hidden className="size-4 text-muted-foreground" />
      <span className="sr-only">{copy.languagePicker}</span>
      <select
        value={copy.language.code}
        disabled={pending}
        onChange={(event) => startTransition(() => chooseLanguage(event.target.value))}
        className="h-9 rounded-md border bg-card px-2 font-medium shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {SCREEN_LANGUAGES.map((language) => (
          <option key={language} value={language}>
            {copyFor(language).language.name}
          </option>
        ))}
      </select>
    </label>
  );
}
