import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Joins class names; later Tailwind classes win over earlier ones. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** A date as people in India read it ("4 Nov"), in India time like the backend's days. */
export function formatDay(
  iso: string,
  options: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" },
) {
  return new Date(iso).toLocaleDateString("en-IN", { ...options, timeZone: "Asia/Kolkata" });
}

/** One search param of a page (`?q=…`); a repeated or missing one counts as none. */
export function searchParam(query: Record<string, string | string[] | undefined>, name: string) {
  const value = query[name];
  return typeof value === "string" ? value : undefined;
}
