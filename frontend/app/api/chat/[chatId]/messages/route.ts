import { cookies } from "next/headers";
import type { NextRequest } from "next/server";

import { API_BASE_URL, UNREACHABLE } from "@/lib/backend";
import { ACCESS_COOKIE } from "@/lib/session";

/**
 * A message to the assistant or the tutor. The reply streams back from the backend as Server-Sent
 * Events and is passed on piece by piece (lib/sse.ts reads it in the browser). Errors found before
 * the reply starts are JSON, as from any backend call. proxy.ts renews the token first.
 */
export async function POST(request: NextRequest, { params }: RouteContext<"/api/chat/[chatId]/messages">) {
  const { chatId } = await params;
  const token = (await cookies()).get(ACCESS_COOKIE)?.value;
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  try {
    const response = await fetch(`${API_BASE_URL}/chat/sessions/${encodeURIComponent(chatId)}/messages`, {
      method: "POST",
      headers,
      body: await request.text(),
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
        // no-transform: never compressed, which would hold the pieces back.
        "Cache-Control": "no-cache, no-transform",
      },
    });
  } catch {
    return Response.json({ error: UNREACHABLE }, { status: 502 });
  }
}
