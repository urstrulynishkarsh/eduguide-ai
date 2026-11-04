import { expect, test, type Page } from "@playwright/test";

import {
  addTemporaryChild,
  leaveChildMode,
  openFirstChapter,
  practiseChapter,
  removeChild,
  signInDemoParent,
} from "./helpers";

// A whole practice or test is many answers, each checked by the server.
test.describe.configure({ timeout: 120_000 });

/** The temporary child of the running test; removed afterwards even when the test fails. */
let child: string | undefined;

test.afterEach(async ({ browser }) => {
  if (!child) return;
  const page = await browser.newPage();
  await signInDemoParent(page);
  await removeChild(page, child);
  await page.close();
  child = undefined;
});

/** Answers the youngest's question by trying each choice in turn: a wrong one only means "try again". */
async function answerByTrying(page: Page) {
  const card = page.locator("section[aria-busy]").filter({ visible: true });
  await expect(card).toBeVisible(); // the first question streams in after the page's loading screen
  const next = page.getByRole("button", { name: /Next question|See results/ });
  /** One answer: wait for the server's reply and the card to settle, then say whether it was right. */
  const settled = async (answer: () => Promise<void>) => {
    const reply = page.waitForResponse((response) => response.request().method() === "POST");
    await answer();
    await reply;
    await expect(card).toHaveAttribute("aria-busy", "false");
    return next.isVisible();
  };
  const groups = card.getByRole("group");
  if (await groups.count()) {
    // Matching: every way of pairing three items, until one is right.
    for (const order of [
      [0, 1, 2],
      [0, 2, 1],
      [1, 0, 2],
      [1, 2, 0],
      [2, 0, 1],
      [2, 1, 0],
    ]) {
      for (const [i, j] of order.entries()) await groups.nth(i).getByRole("button").nth(j).click();
      if (await settled(() => page.getByRole("button", { name: "Check", exact: true }).click())) return;
    }
  }
  const choices = card.locator("button[aria-pressed], .grid-cols-4 button");
  for (let i = 0; i < (await choices.count()); i++) {
    if (await settled(() => choices.nth(i).click())) return;
  }
  throw new Error("No choice was right");
}

test("a parent prepares chapter practice, and a Class 7 child does all of it", async ({ page }) => {
  await signInDemoParent(page);
  const name = (child = await addTemporaryChild(page, "Class 7", "Hinglish"));

  await practiseChapter(page, "Sample: Class 7 Mathematics");
  await expect(page.getByRole("heading", { name: `✅ Ready for ${name}` })).toBeVisible();
  await expect(
    page.getByText(/Generated from concepts in: Sample: Class 7 Mathematics/).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: `Start now with ${name}` }).click();
  await expect(page).toHaveURL(/\/learn\/practice\/[^/]+$/);

  // Help comes in order: a hint, then the worked steps.
  await page.getByRole("button", { name: /Hint/ }).click();
  await expect(page.getByText(/^💡 /).filter({ visible: true })).toBeVisible();
  await page.getByRole("button", { name: /Show Steps/ }).click();
  await expect(page.getByText("Concept:")).toBeVisible();

  for (let i = 0; i < 10; i++) {
    await page.locator("section button[aria-pressed]").filter({ visible: true }).first().click();
    await page.getByRole("button", { name: "Check", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: /Correct|Not quite/ })).toBeVisible();
    await page.getByRole("button", { name: /Next question|See results/ }).click();
    if (await page.getByRole("heading", { name: "Practice complete!" }).isVisible()) break;
  }
  await expect(page.getByRole("heading", { name: "Practice complete!" })).toBeVisible();
  await expect(page.getByText(/of 10 correct the first time/)).toBeVisible();

  await page.getByRole("link", { name: "Progress" }).filter({ visible: true }).first().click();
  await expect(page.getByText("Questions answered").locator("..")).toContainText("10");

  await leaveChildMode(page);
});

test("a UKG child plays picture practice: try again, stars, no marks", async ({ page }) => {
  await signInDemoParent(page);
  const name = (child = await addTemporaryChild(page, "UKG", "Hindi · हिन्दी"));

  await practiseChapter(page, "Sample: UKG Picture Book");
  await page.getByRole("button", { name: `Start now with ${name}` }).click();
  await expect(page.locator('[data-ui-mode="playful"]').first()).toBeVisible();
  await expect(page.getByText(/Question \d+ of/)).toHaveCount(0);

  for (let i = 0; i < 5; i++) {
    await answerByTrying(page);
    await page.getByRole("button", { name: /Next question|See results/ }).click();
    if (await page.getByRole("heading", { name: /You did it/ }).isVisible()) break;
  }
  await expect(page.getByRole("heading", { name: /You did it/ })).toBeVisible();
  await expect(page.getByText(/You earned \d+ stars?!/)).toBeVisible();

  await page.getByRole("link", { name: "My Stars" }).filter({ visible: true }).first().click();
  await expect(page.getByRole("heading", { name: /My Stars/ })).toBeVisible();
  await expect(page.locator("main").filter({ visible: true })).not.toContainText("%");

  await leaveChildMode(page);
});

test("a parent makes a chapter test, the Class 7 child takes it, and both see the report", async ({
  page,
}) => {
  await signInDemoParent(page);
  const name = (child = await addTemporaryChild(page, "Class 7", "Hinglish"));

  // Create Test offers the kinds of Class 7: no full mock test, no time limit before Class 9.
  await page.goto("/parent/tests/new");
  const kind = page.getByLabel("Kind of test").filter({ visible: true });
  await expect(kind.locator("option")).toHaveText(["Practice test", "Chapter test"]);
  await expect(page.getByLabel("Time limit in minutes")).toHaveCount(0);
  await kind.selectOption({ label: "Chapter test" });
  await expect(page.getByText("Choose a chapter for a chapter test.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Create Test" })).toBeDisabled();

  await openFirstChapter(page, "Sample: Class 7 Mathematics");
  await page.getByRole("button", { name: "📝 Take Test" }).click();
  await expect(page).toHaveURL(/\/parent\/tests\/[^/?]+$/);
  await expect(
    page.getByRole("heading", { name: "Chapter test · Chapter 4 Simple Equations" }),
  ).toBeVisible();
  await expect(page.getByText(/15 questions · 31 marks · No time limit/)).toBeVisible();
  await page.getByRole("button", { name: `Start now with ${name}` }).click();
  await expect(page).toHaveURL(/\/learn\/tests\/[^/]+$/);

  // Written answers are marked by the AI, so only section A (8 objective questions) is answered.
  const grid = page.getByRole("navigation", { name: "Go to a question" }).filter({ visible: true });
  for (let i = 1; i <= 8; i++) {
    await grid.getByRole("button", { name: String(i), exact: true }).click();
    await page.locator("section button[aria-pressed]").filter({ visible: true }).first().click();
  }
  await expect(page.getByText("8 of 15 answered")).toBeVisible();
  await page.getByRole("button", { name: "Submit test" }).click();
  await expect(page.getByText("7 questions not answered yet. Submit anyway?")).toBeVisible();
  await page.getByRole("button", { name: "Yes, submit" }).click();

  // The answers still on their way go first, then the marking: allow it a while on a busy server.
  const result = page.getByRole("heading", { name: /^Result: Chapter test/ });
  await expect(result).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("dt", { hasText: "Not answered" }).locator("..")).toContainText("7");
  await page.reload(); // a submitted test stays submitted
  await expect(result).toBeVisible();
  await page.getByRole("link", { name: "← All tests" }).click();
  await expect(page.getByRole("button", { name: "Take again" })).toBeVisible();
  await expect(page.getByRole("link", { name: /See result · \d+(\.5)? \/ 31/ })).toBeVisible();

  await leaveChildMode(page);
  await page.goto("/parent/tests");
  await page
    .getByRole("link", { name: /Chapter test · Chapter 4 Simple Equations/ })
    .filter({ visible: true })
    .click();
  await expect(page.getByRole("heading", { name: "Sittings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Every question" })).toBeVisible();
});
