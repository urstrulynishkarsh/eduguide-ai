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

/**
 * Answers the youngest's question by trying each choice in turn: a wrong one only means "try again".
 * The UKG child learns in Hindi, so the buttons are in Hindi.
 */
async function answerByTrying(page: Page) {
  const card = page.locator("section[aria-busy]").filter({ visible: true });
  await expect(card).toBeVisible(); // the first question streams in after the page's loading screen
  const next = page.getByRole("button", { name: /अगला प्रश्न|नतीजे देखें/ });
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
      if (await settled(() => page.getByRole("button", { name: "जाँचें", exact: true }).click())) return;
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
  // Left for another page, the practice is found again on Create Practice.
  const practice = page.url();
  await page.goto("/parent/dashboard");
  await page.goto("/parent/practice");
  await page.getByRole("link", { name: /Not finished/ }).click();
  await expect(page).toHaveURL(practice);
  await page.getByRole("button", { name: `Start now with ${name}` }).click();
  await expect(page).toHaveURL(/\/learn\/practice\/[^/]+$/);

  // The child's screens are in their language (Hinglish). Help comes in order: a hint, then the steps.
  await page.getByRole("button", { name: /Hint/ }).click();
  await expect(page.getByText(/^💡 /).filter({ visible: true })).toBeVisible();
  await page.getByRole("button", { name: /Steps dikhaiye/ }).click();
  await expect(page.getByText("Concept:")).toBeVisible();

  for (let i = 0; i < 10; i++) {
    await page.locator("section button[aria-pressed]").filter({ visible: true }).first().click();
    await page.getByRole("button", { name: "Check karein", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: /Sahi!|Poori tarah sahi nahin/ })).toBeVisible();
    await page.getByRole("button", { name: /Agla question|Result dekhiye/ }).click();
    if (await page.getByRole("heading", { name: "Practice poori!" }).isVisible()) break;
  }
  await expect(page.getByRole("heading", { name: "Practice poori!" })).toBeVisible();
  await expect(page.getByText(/10 mein se \d+ pehli baar mein sahi/)).toBeVisible();
  await expect(page.getByText("🔥 1 din lagaataar")).toBeVisible(); // the streak has begun
  await expect(page.getByText("Aaj ka goal poora! 🎉")).toBeVisible(); // 10 answers: Class 7's goal

  await page.getByRole("link", { name: "Progress" }).filter({ visible: true }).first().click();
  await expect(page.getByText("Kiye gaye questions").locator("..")).toContainText("10");
  await expect(page.locator('[data-earned="true"]', { hasText: "Pehli practice" })).toBeVisible();
  const weeks = page.getByRole("group", { name: "Pichhle 12 hafte" }).filter({ visible: true });
  await expect(weeks.getByRole("img", { name: /10 kiye, \d+ pehli baar mein sahi$/ })).toBeVisible();

  await leaveChildMode(page);
});

test("a UKG child plays picture practice: try again, stars, no marks", async ({ page }) => {
  await signInDemoParent(page);
  const name = (child = await addTemporaryChild(page, "UKG", "Hindi · हिन्दी"));

  await practiseChapter(page, "Sample: UKG Picture Book");
  await page.getByRole("button", { name: `Start now with ${name}` }).click();
  await expect(page.locator('[data-ui-mode="playful"]').first()).toBeVisible();
  await expect(page.getByText(/प्रश्न \d+ \//)).toHaveCount(0); // no "Question 2 of 5" for the youngest

  for (let i = 0; i < 5; i++) {
    await answerByTrying(page);
    await page.getByRole("button", { name: /अगला प्रश्न|नतीजे देखें/ }).click();
    if (await page.getByRole("heading", { name: /तुमने कर दिखाया/ }).isVisible()) break;
  }
  await expect(page.getByRole("heading", { name: /तुमने कर दिखाया/ })).toBeVisible();
  await expect(page.getByText(/आपको \d+ (सितारा|सितारे) मिले!/)).toBeVisible();

  await page.getByRole("link", { name: "मेरे सितारे" }).filter({ visible: true }).first().click();
  await expect(page.getByRole("heading", { name: /मेरे सितारे/ })).toBeVisible();
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
  // The child's screens are in Hinglish.
  const grid = page.getByRole("navigation", { name: "Kisi question par jaiye" }).filter({ visible: true });
  for (let i = 1; i <= 8; i++) {
    await grid.getByRole("button", { name: String(i), exact: true }).click();
    await page.locator("section button[aria-pressed]").filter({ visible: true }).first().click();
  }
  await expect(page.getByText("15 mein se 8 kiye")).toBeVisible();
  await page.getByRole("button", { name: "Test submit karein" }).click();
  await expect(page.getByText("7 questions abhi baaki hain. Phir bhi submit karein?")).toBeVisible();
  await page.getByRole("button", { name: "Haan, submit karein" }).click();

  // The answers still on their way go first, then the marking: allow it a while on a busy server.
  const result = page.getByRole("heading", { name: /^Result: Chapter test/ });
  await expect(result).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("dt", { hasText: "Nahin kiya" }).locator("..")).toContainText("7");
  await page.reload(); // a submitted test stays submitted
  await expect(result).toBeVisible();
  await page.getByRole("link", { name: "← Saare tests" }).click();
  await expect(page.getByRole("button", { name: "Phir se dijiye" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Result dekhiye · \d+(\.5)? \/ 31/ })).toBeVisible();

  await leaveChildMode(page);
  await page.goto("/parent/tests");
  await page
    .getByRole("link", { name: /Chapter test · Chapter 4 Simple Equations/ })
    .filter({ visible: true })
    .click();
  await expect(page.getByRole("heading", { name: "Sittings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Every question" })).toBeVisible();
});
