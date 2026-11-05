import { NextResponse, type NextRequest } from "next/server";

import { API_BASE_URL, UNREACHABLE } from "@/lib/backend";
import { ACCESS_COOKIE, REFRESH_COOKIE, renewSession, storeTokens } from "@/lib/session";

/**
 * "Upload Book": passes the browser's file on to the backend as it arrives, so a 50 MB book never
 * sits in memory here, and the browser can show how much has been sent. The backend checks the
 * session, the book and the file. This route is outside proxy.ts, which would buffer the body, so it
 * renews an access token that ran out while the page was open (the file is not read for that).
 */
export async function POST(request: NextRequest, { params }: RouteContext<"/api/books/[bookId]/documents">) {
  const { bookId } = await params;
  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  const { tokens } = await renewSession(accessToken, request.cookies.get(REFRESH_COOKIE)?.value);
  const token = tokens?.access_token ?? accessToken;
  const headers = new Headers({ "Content-Type": request.headers.get("content-type") ?? "" });
  const length = request.headers.get("content-length");
  if (length) headers.set("Content-Length", length);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const reply = (response: NextResponse) => {
    if (tokens) storeTokens(response.cookies, tokens.access_token, tokens.refresh_token);
    return response;
  };
  try {
    const response = await fetch(`${API_BASE_URL}/books/${encodeURIComponent(bookId)}/documents`, {
      method: "POST",
      headers,
      body: request.body,
      duplex: "half",
    } as RequestInit & { duplex: "half" });
    return reply(
      new NextResponse(response.body, {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  } catch {
    return reply(NextResponse.json({ error: UNREACHABLE }, { status: 502 }));
  }
}
