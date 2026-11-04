import type { Role } from "@/lib/types";

/*
 * The session lives in two httpOnly cookies that only the Next.js server reads
 * (docs/04 §4.6):
 *
 *   eg_access   the token sent to the backend: a parent's, a solo student's, or a child-mode token
 *   eg_refresh  swaps an expired access token for a new one. Deleted in child mode, so nothing
 *               on the device can act as the parent until the parent's password is entered again.
 */
export const ACCESS_COOKIE = "eg_access";
export const REFRESH_COOKIE = "eg_refresh";
/** The device's screen language (lib/copy). Not secret; kept when the session ends. */
export const LANGUAGE_COOKIE = "eg_lang";

/** Renew a token this long before it runs out, so it can't expire on the way to the backend. */
const EXPIRY_MARGIN_MS = 30_000;

interface TokenClaims {
  role: Role;
  exp: number;
}

/**
 * Reads a token's role and expiry without checking its signature. Good enough to pick a
 * screen; the backend checks every token it receives.
 */
export function readClaims(token: string | undefined): TokenClaims | null {
  try {
    const claims = JSON.parse(Buffer.from(token!.split(".")[1], "base64url").toString());
    if ((claims.role === "parent" || claims.role === "student") && typeof claims.exp === "number") {
      return { role: claims.role, exp: claims.exp };
    }
  } catch {
    // Missing or damaged: treated as no token.
  }
  return null;
}

export function isFresh(claims: TokenClaims, now = Date.now()): boolean {
  return claims.exp * 1000 - now > EXPIRY_MARGIN_MS;
}

interface CookieOptions {
  httpOnly: boolean;
  sameSite: "lax";
  secure: boolean;
  path: string;
  expires: Date;
}

/** Either the cookies of a Server Action / Route Handler or of a proxy response. */
export interface CookieStore {
  set(name: string, value: string, options: CookieOptions): unknown;
  delete(name: string): unknown;
}

function cookieOptions(token: string): CookieOptions {
  return {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date((readClaims(token)?.exp ?? 0) * 1000),
  };
}

/** Saves a session. Without a refresh token (child mode) any stored one is deleted. */
export function storeTokens(store: CookieStore, accessToken: string, refreshToken: string | null): void {
  store.set(ACCESS_COOKIE, accessToken, cookieOptions(accessToken));
  if (refreshToken) store.set(REFRESH_COOKIE, refreshToken, cookieOptions(refreshToken));
  else store.delete(REFRESH_COOKIE);
}

/** Keeps the screen language for a year. Readers check the code (lib/copy `screenLanguage`). */
export function storeLanguage(store: CookieStore, language: string): void {
  store.set(LANGUAGE_COOKIE, language, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
  });
}

export function clearTokens(store: CookieStore): void {
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}
