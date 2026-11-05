import { NextResponse, type NextRequest } from "next/server";

import { endSession } from "@/lib/backend";
import { ACCESS_COOKIE, REFRESH_COOKIE, clearTokens } from "@/lib/session";

/**
 * Signs the session out on the backend (its tokens stop working, also any copy of them), forgets
 * it here and goes to sign-in. POST from the Sign out buttons; GET when the backend refuses a
 * session. 303 so the browser follows with a GET, whichever method came in. The refresh token goes
 * first: this route is outside proxy.ts, so the access token may have run out.
 */
export async function POST(request: NextRequest) {
  const { cookies } = request;
  await endSession(cookies.get(REFRESH_COOKIE)?.value ?? cookies.get(ACCESS_COOKIE)?.value);
  const response = NextResponse.redirect(new URL("/login", request.url), 303);
  clearTokens(response.cookies);
  return response;
}

export const GET = POST;
