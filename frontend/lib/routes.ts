import type { Role } from "@/lib/types";

/** Where a signed-in session starts. Those pages send unfinished onboarding on to the right form. */
export function homeFor(role: Role): string {
  return role === "parent" ? "/who-is-learning" : "/learn";
}

const GUEST_ONLY = ["/login", "/register"];
const PARENT_ONLY = ["/parent", "/who-is-learning", "/onboarding/child"];
const STUDENT_ONLY = ["/learn", "/onboarding/profile"];

function isUnder(pathname: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

/**
 * Where the proxy sends a request, or null to let it through. `role` is the role of the
 * session's access token (a parent in child mode is a "student"), or null when signed out.
 * This only picks the right screen; the backend still checks every call.
 */
export function redirectFor(pathname: string, role: Role | null): string | null {
  if (isUnder(pathname, GUEST_ONLY)) return role ? homeFor(role) : null;

  const parentOnly = isUnder(pathname, PARENT_ONLY);
  const studentOnly = isUnder(pathname, STUDENT_ONLY);
  if (!parentOnly && !studentOnly) return null;
  if (!role) return "/login";
  if ((parentOnly && role !== "parent") || (studentOnly && role !== "student")) return homeFor(role);
  return null;
}
