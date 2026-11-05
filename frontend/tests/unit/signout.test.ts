// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/signout/route";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session";
import nextConfig from "@/next.config";

function request(cookies: Record<string, string>) {
  const cookie = Object.entries(cookies)
    .map(([name, value]) => `${name}=${value}`)
    .join("; ");
  return new NextRequest("http://localhost:3000/signout", { method: "POST", headers: { cookie } });
}

function mockBackend(response: () => Promise<Response>) {
  const fetchMock = vi.fn<(url: string, init: RequestInit) => Promise<Response>>(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("sign out", () => {
  it("ends the session on the backend with the refresh token, then forgets it here", async () => {
    const fetchMock = mockBackend(async () => new Response(null, { status: 204 }));
    const response = await POST(request({ [ACCESS_COOKIE]: "access", [REFRESH_COOKIE]: "refresh" }));

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/logout$/);
    expect(JSON.parse(String(init.body))).toEqual({ token: "refresh" });
    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
    const cleared = response.cookies.getAll().map((cookie) => [cookie.name, cookie.value]);
    expect(cleared).toEqual([
      [ACCESS_COOKIE, ""],
      [REFRESH_COOKIE, ""],
    ]);
  });

  it("uses the access token in child mode, and signs out here even when the backend is down", async () => {
    const fetchMock = mockBackend(async () => {
      throw new TypeError("fetch failed");
    });
    const response = await POST(request({ [ACCESS_COOKIE]: "child-access" }));

    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({ token: "child-access" });
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
  });

  it("asks nothing of the backend without a session", async () => {
    const fetchMock = mockBackend(async () => new Response());
    await POST(request({}));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("security headers", () => {
  it("are sent with every page, the policy allowing this site only and no framing", async () => {
    const [rule] = await nextConfig.headers!();
    expect(rule.source).toBe("/:path*");
    const headers = Object.fromEntries(rule.headers.map(({ key, value }) => [key, value]));
    expect(headers["Content-Security-Policy"]).toContain("default-src 'self'");
    expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
    expect(headers["Content-Security-Policy"]).toContain("object-src 'none'");
    expect(headers["Content-Security-Policy"]).not.toContain("unsafe-eval"); // development only
    expect(headers["X-Content-Type-Options"]).toBe("nosniff");
  });
});
