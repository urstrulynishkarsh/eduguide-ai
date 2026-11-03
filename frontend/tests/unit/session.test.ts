import { describe, expect, it, vi } from "vitest";

import { ACCESS_COOKIE, REFRESH_COOKIE, clearTokens, isFresh, readClaims, storeTokens } from "@/lib/session";

import { fakeToken } from "./helpers";

function fakeStore() {
  return { set: vi.fn(), delete: vi.fn() };
}

describe("readClaims", () => {
  it("reads the role and expiry", () => {
    expect(readClaims(fakeToken("parent", 60))).toMatchObject({ role: "parent", exp: expect.any(Number) });
  });

  it.each([
    undefined,
    "",
    "not-a-token",
    "a.b.c",
    `x.${Buffer.from('{"role":"admin","exp":1}').toString("base64url")}.y`,
  ])("treats %s as no token", (token) => {
    expect(readClaims(token)).toBeNull();
  });
});

describe("isFresh", () => {
  it("is false within 30 seconds of expiry, so a token can't run out on the way", () => {
    expect(isFresh(readClaims(fakeToken("parent", 600))!)).toBe(true);
    expect(isFresh(readClaims(fakeToken("parent", 20))!)).toBe(false);
    expect(isFresh(readClaims(fakeToken("parent", -5))!)).toBe(false);
  });
});

describe("storeTokens", () => {
  it("keeps both tokens in httpOnly cookies that expire with the token", () => {
    const store = fakeStore();
    const access = fakeToken("parent", 1800);
    storeTokens(store, access, fakeToken("parent", 3600));

    expect(store.set).toHaveBeenCalledTimes(2);
    const [name, value, options] = store.set.mock.calls[0];
    expect([name, value]).toEqual([ACCESS_COOKIE, access]);
    expect(options).toMatchObject({ httpOnly: true, sameSite: "lax", path: "/" });
    expect(options.expires.getTime()).toBe(readClaims(access)!.exp * 1000);
  });

  it("drops the parent's refresh token in child mode", () => {
    const store = fakeStore();
    storeTokens(store, fakeToken("student", 43200), null);
    expect(store.set).toHaveBeenCalledOnce();
    expect(store.delete).toHaveBeenCalledWith(REFRESH_COOKIE);
  });
});

it("clearTokens forgets the whole session", () => {
  const store = fakeStore();
  clearTokens(store);
  expect(store.delete.mock.calls.flat()).toEqual([ACCESS_COOKIE, REFRESH_COOKIE]);
});
