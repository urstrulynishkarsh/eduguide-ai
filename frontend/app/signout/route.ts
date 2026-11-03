import { NextResponse, type NextRequest } from "next/server";

import { clearTokens } from "@/lib/session";

/**
 * Forgets the session and goes to sign-in. POST from the Sign out buttons; GET when the backend
 * refuses a session. 303 so the browser follows with a GET, whichever method came in.
 */
export function POST(request: NextRequest) {
  const response = NextResponse.redirect(new URL("/login", request.url), 303);
  clearTokens(response.cookies);
  return response;
}

export const GET = POST;
