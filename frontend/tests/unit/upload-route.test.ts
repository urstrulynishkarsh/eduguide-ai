// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/books/[bookId]/documents/route";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";

import { fakeToken } from "./helpers";

function upload(cookies: Record<string, string>) {
  const cookie = Object.entries(cookies)
    .map(([name, value]) => `${name}=${value}`)
    .join("; ");
  const request = new NextRequest("http://localhost:3000/api/books/b1/documents", {
    method: "POST",
    headers: { cookie, "content-type": "multipart/form-data; boundary=x" },
    body: "--x--",
  });
  return POST(request, { params: Promise.resolve({ bookId: "b1" }) });
}

/** The backend: new tokens for /auth/refresh, the file accepted for anything else. */
function mockBackend(tokens?: { access_token: string; refresh_token: string }) {
  const fetchMock = vi.fn<(url: string, init: RequestInit) => Promise<Response>>(async (url) =>
    url.endsWith("/auth/refresh") ? Response.json(tokens) : Response.json({ id: "d1" }, { status: 202 }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const sentWith = (init: RequestInit) => new Headers(init.headers).get("Authorization");

afterEach(() => vi.unstubAllGlobals());

describe("the upload route (outside proxy.ts)", () => {
  it("renews an access token that ran out while the page was open, then sends the file", async () => {
    const tokens = { access_token: fakeToken("parent", 1800), refresh_token: fakeToken("parent", 86400) };
    const fetchMock = mockBackend(tokens);

    const response = await upload({
      [ACCESS_COOKIE]: fakeToken("parent", -10),
      [REFRESH_COOKIE]: fakeToken("parent", 86400),
    });

    expect(response.status).toBe(202);
    const [refresh, file] = fetchMock.mock.calls;
    expect(refresh[0]).toMatch(/\/auth\/refresh$/);
    expect(file[0]).toMatch(/\/books\/b1\/documents$/);
    expect(sentWith(file[1])).toBe(`Bearer ${tokens.access_token}`);
    expect(response.cookies.get(ACCESS_COOKIE)?.value).toBe(tokens.access_token);
    expect(response.cookies.get(REFRESH_COOKIE)?.value).toBe(tokens.refresh_token);
  });

  it("sends a fresh session's token as it is", async () => {
    const access = fakeToken("parent", 600);
    const fetchMock = mockBackend();

    const response = await upload({ [ACCESS_COOKIE]: access, [REFRESH_COOKIE]: fakeToken("parent", 86400) });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(sentWith(fetchMock.mock.calls[0][1])).toBe(`Bearer ${access}`);
    expect(response.cookies.getAll()).toEqual([]);
  });
});
