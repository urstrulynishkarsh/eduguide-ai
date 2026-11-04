import "server-only";

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { cache } from "react";

import { copyFor, screenLanguage, type Copy, type ScreenLanguage } from "@/lib/copy";
import { LANGUAGE_COOKIE } from "@/lib/session";

/** The screen language of this request: the device's (the account's from sign-in, the child's in child mode). */
export const currentLanguage = cache(async (): Promise<ScreenLanguage> =>
  screenLanguage((await cookies()).get(LANGUAGE_COOKIE)?.value),
);

/** The words of this request's screen language, for pages, layouts and async server components. */
export async function getCopy(): Promise<Copy> {
  return copyFor(await currentLanguage());
}

/** A page's `generateMetadata` that gives it a title in the screen language. */
export function titled(title: (copy: Copy) => string) {
  return async (): Promise<Metadata> => ({ title: title(await getCopy()) });
}
