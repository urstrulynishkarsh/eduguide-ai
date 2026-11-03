import { describe, expect, it } from "vitest";

import { homeFor, redirectFor } from "@/lib/routes";

describe("redirectFor", () => {
  it.each([
    // [path, role, where the proxy sends it (null = let through)]
    ["/", null, null],
    ["/", "parent", null],
    ["/login", null, null],
    ["/register", null, null],
    ["/login", "parent", "/who-is-learning"],
    ["/register", "student", "/learn"],
    ["/parent/children", null, "/login"],
    ["/who-is-learning", null, "/login"],
    ["/learn", null, "/login"],
    ["/onboarding/child", null, "/login"],
    ["/parent/children", "parent", null],
    ["/who-is-learning", "parent", null],
    ["/onboarding/child", "parent", null],
    // A student session (solo, or a child in child mode) never reaches the parent screens.
    ["/parent/children", "student", "/learn"],
    ["/parent/settings", "student", "/learn"],
    ["/who-is-learning", "student", "/learn"],
    ["/onboarding/child", "student", "/learn"],
    ["/learn", "student", null],
    ["/learn/exit", "student", null],
    ["/onboarding/profile", "student", null],
    // A parent picks a child first.
    ["/learn", "parent", "/who-is-learning"],
    ["/onboarding/profile", "parent", "/who-is-learning"],
    // Only whole path segments count.
    ["/parental-guide", null, null],
    ["/learning", null, null],
  ] as const)("%s as %s → %s", (path, role, target) => {
    expect(redirectFor(path, role)).toBe(target);
  });
});

it("homeFor sends parents to the profile picker and students to their home", () => {
  expect(homeFor("parent")).toBe("/who-is-learning");
  expect(homeFor("student")).toBe("/learn");
});
