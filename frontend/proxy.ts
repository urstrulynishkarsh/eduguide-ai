import { NextResponse, type NextRequest } from "next/server";

import { ApiError, callBackend } from "@/lib/backend";
import { redirectFor } from "@/lib/routes";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  clearTokens,
  isFresh,
  readClaims,
  storeTokens,
  type CookieStore,
} from "@/lib/session";
import type { Role, TokenPair } from "@/lib/types";

/**
 * Runs before every page and Server Action: renews an expired access token with the refresh
 * token, then sends the request to the area that fits the session (signed out → /login,
 * child mode → /learn, …).
 */
export async function proxy(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  const access = readClaims(accessToken);
  const refresh = readClaims(refreshToken);

  let role: Role | null = access && isFresh(access) ? access.role : null;
  let tokens: TokenPair | null = null;
  let unreachable = false;
  if (!role && refreshToken && refresh && isFresh(refresh)) {
    try {
      tokens = await callBackend<TokenPair>("/auth/refresh", {
        method: "POST",
        body: { refresh_token: refreshToken },
      });
      role = readClaims(tokens.access_token)?.role ?? null;
    } catch (error) {
      unreachable = error instanceof ApiError && error.status === 0;
    }
  }
  // A dead session is forgotten. One the backend could not check (it is down) is kept.
  const forget = !role && !unreachable && Boolean(accessToken || refreshToken);
  const save = (store: CookieStore) => {
    if (tokens) storeTokens(store, tokens.access_token, tokens.refresh_token);
    else if (forget) clearTokens(store);
  };

  // The page rendered for this request must see the same cookies the browser will keep.
  save({
    set: (name, value) => request.cookies.set(name, value),
    delete: (name) => request.cookies.delete(name),
  });
  const target = redirectFor(request.nextUrl.pathname, role);
  const response = target
    ? NextResponse.redirect(new URL(target, request.url))
    : NextResponse.next({ request: { headers: request.headers } });
  save(response.cookies);
  return response;
}

export const config = {
  // Pages, Server Actions and the chat route (a reply needs a fresh token too). Not static files, not
  // /signout (it clears the cookies itself), and not the upload route (the proxy would buffer a whole
  // book in memory).
  matcher: ["/((?!_next/|api/books/|signout|favicon\\.ico|.*\\.[a-z0-9]+$).*)"],
};
