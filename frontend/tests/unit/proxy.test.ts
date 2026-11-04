// @vitest-environment node
import { unstable_doesMiddlewareMatch } from "next/experimental/testing/server";
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";
import { config, proxy } from "@/proxy";

import { fakeToken } from "./helpers";

function request(path: string, cookies: Record<string, string> = {}) {
  const cookie = Object.entries(cookies)
    .map(([name, value]) => `${name}=${value}`)
    .join("; ");
  return new NextRequest(`http://localhost:3000${path}`, { headers: cookie ? { cookie } : {} });
}

function mockRefresh(response: () => Promise<Response>) {
  const fetchMock = vi.fn<(url: string) => Promise<Response>>(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("proxy", () => {
  it("runs before pages and chat replies, never before a book upload or a static file", () => {
    const runs = (url: string) => unstable_doesMiddlewareMatch({ config, url });
    expect(runs("/parent/children")).toBe(true);
    expect(runs("/api/chat/c1/messages")).toBe(true); // a reply needs a fresh token
    expect(runs("/api/books/b1/documents")).toBe(false); // the proxy would hold a whole book in memory
    expect(runs("/_next/static/chunk.js")).toBe(false);
  });

  it("lets a fresh session through without touching its cookies", async () => {
    const fetchMock = mockRefresh(async () => new Response());
    const response = await proxy(request("/parent/children", { [ACCESS_COOKIE]: fakeToken("parent", 600) }));
    expect(response.headers.get("location")).toBeNull();
    expect(response.cookies.getAll()).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends a signed-out visitor of a private page to sign in", async () => {
    const response = await proxy(request("/parent/children"));
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
  });

  it("keeps a child in child mode out of the parent area", async () => {
    const response = await proxy(request("/parent/settings", { [ACCESS_COOKIE]: fakeToken("student", 600) }));
    expect(response.headers.get("location")).toBe("http://localhost:3000/learn");
  });

  it("renews an expired access token quietly", async () => {
    const tokens = { access_token: fakeToken("parent", 1800), refresh_token: fakeToken("parent", 86400) };
    const fetchMock = mockRefresh(async () => Response.json(tokens));
    const response = await proxy(
      request("/parent/children", {
        [ACCESS_COOKIE]: fakeToken("parent", -10),
        [REFRESH_COOKIE]: fakeToken("parent", 86400),
      }),
    );
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/auth\/refresh$/);
    expect(response.headers.get("location")).toBeNull();
    expect(response.cookies.get(ACCESS_COOKIE)?.value).toBe(tokens.access_token);
    expect(response.cookies.get(ACCESS_COOKIE)?.httpOnly).toBe(true);
    expect(response.cookies.get(REFRESH_COOKIE)?.value).toBe(tokens.refresh_token);
  });

  it("forgets a session the backend refuses to renew", async () => {
    mockRefresh(async () => Response.json({ error: { code: "invalid_token" } }, { status: 401 }));
    const response = await proxy(request("/learn", { [REFRESH_COOKIE]: fakeToken("student", 86400) }));
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
    expect(response.cookies.get(ACCESS_COOKIE)?.value).toBe("");
    expect(response.cookies.get(REFRESH_COOKIE)?.value).toBe("");
  });

  it("keeps the session when the backend can't be reached", async () => {
    mockRefresh(async () => {
      throw new TypeError("fetch failed");
    });
    const response = await proxy(request("/learn", { [REFRESH_COOKIE]: fakeToken("student", 86400) }));
    expect(response.cookies.getAll()).toEqual([]);
  });

  it("ends an expired child-mode session: there is no refresh token to renew it with", async () => {
    const fetchMock = mockRefresh(async () => new Response());
    const response = await proxy(request("/learn", { [ACCESS_COOKIE]: fakeToken("student", -10) }));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
    expect(response.cookies.get(ACCESS_COOKIE)?.value).toBe("");
  });
});
