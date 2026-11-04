"use client";

import { createContext, useContext } from "react";

import { copyFor, type Copy, type ScreenLanguage } from "@/lib/copy";

const CopyContext = createContext<Copy>(copyFor("en"));

/**
 * The screen language for client components (the root layout sets it from the cookie). The words
 * can't be sent from the server, as some are functions, so each client bundle has every language.
 */
export function CopyProvider({
  language,
  children,
}: {
  language: ScreenLanguage;
  children: React.ReactNode;
}) {
  return <CopyContext value={copyFor(language)}>{children}</CopyContext>;
}

/** The words of the screen language, in a client component. */
export function useCopy(): Copy {
  return useContext(CopyContext);
}
