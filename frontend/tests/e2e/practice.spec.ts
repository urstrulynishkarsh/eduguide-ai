import { expect, test, type Page } from "@playwright/test";

import { addTemporaryChild, leaveChildMode, practiseChapter, removeChild, signInDemoParent } from "./helpers";

// A whole practice is many answers, each checked by the server.
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
