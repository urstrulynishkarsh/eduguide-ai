import { expect, test, type Page } from "@playwright/test";

import { expectAccessible, leaveChildMode, signInDemoParent, tap } from "./helpers";

/*
 * Every main screen passes axe's WCAG A and AA checks, in the layouts the demo accounts cover:
 * Classes 6 – 8 (Aarav), Nursery – Class 2 (Anaya) and 9 – 12 (Kabir). The practice and test
 * screens are checked inside their journeys (practice.spec.ts), where they have questions.
 */

// Each test checks many screens, while the other journeys may be keeping the API busy.
test.describe.configure({ timeout: 120_000 });

const PARENT_SCREENS = [
  "/parent/dashboard",
  "/parent/children",
  "/parent/books",
  "/parent/books/upload",
  "/parent/practice",
  "/parent/tests",
  "/parent/tests/new",
  "/parent/plans",
  "/parent/progress",
  "/parent/assistant",
  "/parent/settings",
];
const LEARNER_SCREENS = [
  "/learn",
  "/learn/plan",
  "/learn/practice",
  "/learn/progress",
  "/learn/concepts",
  "/learn/tutor",
];

async function expectScreensAccessible(page: Page, paths: string[]) {
  for (const path of paths) {
    await page.goto(path);
    await expectAccessible(page);
  }
}

test("the public screens", async ({ page }) => {
  await expectScreensAccessible(page, ["/", "/login"]);
  await page.goto("/register");
  await tap(page, "Parent"); // the fields come with the choice
  await expectAccessible(page);
});

test("the parent's screens", async ({ page }) => {
  await signInDemoParent(page);
  await expectAccessible(page); // Who is learning?
  await expectScreensAccessible(page, PARENT_SCREENS);
  await page.goto("/parent/children/new");
  await tap(page, "Class 7"); // the rest of the form comes with the class
  await expectAccessible(page);
});

test("a child's screens, in the Class 6 – 8 and Nursery – Class 2 layouts", async ({ page }) => {
  await signInDemoParent(page);
  for (const child of ["Aarav", "Anaya"]) {
    await page.getByRole("button", { name: new RegExp(child) }).click();
    await expect(page).toHaveURL(/\/learn$/);
    await expectScreensAccessible(page, [...LEARNER_SCREENS, "/learn/exit"]);
    await leaveChildMode(page);
  }
});

test("a student's screens, in the Class 9 – 12 layout", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("student@example.com");
  await page.getByLabel("Password").fill("DemoStudent123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/learn$/);
  await expectScreensAccessible(page, [...LEARNER_SCREENS, "/learn/tests", "/learn/books"]);
});
