import { expect, test, type Page } from "@playwright/test";

import { chooseClass, signUp, uniqueEmail, uploadSampleBook } from "./helpers";

/** A date `days` from today, as a date field takes it (YYYY-MM-DD). */
function daysFromNow(days: number): string {
  return new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);
}

/** With the AI off, the screen says so; with it on, the conversation opens under its first question. */
function aiOffOrConversation(page: Page, aiOff: string, question: string) {
  return page.getByText(aiOff).or(page.getByRole("link", { name: question }));
}

test("a parent makes a study plan, the child starts today's tasks, and both ask the AI", async ({ page }) => {
  test.setTimeout(180_000); // a book is read first
  await signUp(page, "Parent", "Meena Joshi", uniqueEmail("plan"));
  await chooseClass(page, "Class 7", "Riya");
  await page.getByRole("button", { name: "Add child" }).click();
  await expect(page).toHaveURL(/\/who-is-learning$/);
  await uploadSampleBook(page);

  await page.goto("/parent/plans");
  await expect(page.getByText(/Riya has no study plan yet/)).toBeVisible();
  await page.getByRole("link", { name: "Make a plan" }).click();
  await page.getByLabel("Exam date").fill(daysFromNow(14));
  await page.getByLabel("Minutes a day").fill("60");
  await page.getByRole("button", { name: "Make plan" }).click();
  await expect(page).toHaveURL(/\/parent\/plans$/);
  await expect(page.getByText(/days to the exam/)).toBeVisible();
  await expect(page.getByText(/Learn: Chapter 4 Simple Equations/).first()).toBeVisible();

  // The dashboard: today's plan, and Start Recommended Practice (written by the AI for a new book).
  await page.goto("/parent/dashboard");
  await expect(page.getByRole("heading", { name: "Today's plan" })).toBeVisible();
  await page.getByRole("button", { name: /^Start Recommended Practice/ }).click();
  await expect(
    page
      .getByText(/not switched on yet|Getting your questions ready|Ready for Riya/)
      .filter({ visible: true }),
  ).toBeVisible();

  await page.goto("/parent/assistant");
  await page.getByRole("button", { name: "How is my child doing this week?" }).click();
  await expect(
    aiOffOrConversation(
      page,
      "The assistant needs the AI, which is not switched on yet.",
      "How is my child doing this week?",
    ),
  ).toBeVisible({ timeout: 60_000 });

  // Riya's screen: a learn task opens Learn a Concept with its question, and is ticked off.
  await page.goto("/who-is-learning");
  await page.getByRole("button", { name: /Riya/ }).click();
  await expect(page).toHaveURL(/\/learn$/);
  const learnTask = () =>
    page
      .getByRole("listitem")
      .filter({ hasText: "Learn: Chapter 4 Simple Equations" })
      .filter({ visible: true })
      .first();
  await learnTask()
    .getByRole("link", { name: /^Start/ })
    .click();
  await expect(page).toHaveURL(/\/learn\/concepts\/[^/?]+\?q=.+&task=/);
  await expect(page.getByLabel("What would you like to understand?")).toHaveValue(
    "Chapter 4 Simple Equations",
  );

  await page.goto("/learn/plan");
  await learnTask().getByRole("button", { name: "✓ Done" }).click();
  await expect(learnTask().getByRole("button", { name: "Undo" })).toBeVisible();

  await page.getByRole("link", { name: "AI Tutor" }).filter({ visible: true }).first().click();
  await page.getByLabel("Type your question or problem…").fill("What is an equation?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(
    aiOffOrConversation(
      page,
      "The tutor needs the AI, which is not switched on yet.",
      "What is an equation?",
    ),
  ).toBeVisible({ timeout: 60_000 });
});
