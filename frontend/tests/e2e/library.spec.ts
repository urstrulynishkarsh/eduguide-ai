import { expect, test } from "@playwright/test";

import { chooseClass, signUp, uniqueEmail, uploadSampleBook } from "./helpers";

test("a parent uploads a book, watches it being read, and opens a chapter", async ({ page }) => {
  test.setTimeout(120_000); // the first book of a run also loads the reading model
  await signUp(page, "Parent", "Pooja Iyer", uniqueEmail("library"));
  await chooseClass(page, "Class 7", "Dev");
  await page.getByRole("button", { name: "Add child" }).click();
  await expect(page).toHaveURL(/\/who-is-learning$/);

  await page.goto("/parent/books");
  await expect(page.getByText(/No books yet/)).toBeVisible();
  await uploadSampleBook(page);
  await expect(page.locator("main").filter({ visible: true })).not.toContainText(/chunk|embedding/i);

  await page.getByRole("link", { name: /Chapter 4 Simple Equations/ }).click();
  for (const action of ["Learn", "Practice", "Exercise Questions", "Generate Questions", "Take Test"]) {
    await expect(page.getByText(action, { exact: false }).first()).toBeVisible();
  }
  await expect(page.getByText("Solve the following equations and check your answers.").first()).toBeVisible();
  await expect(page.getByText("1. x + 5 = 12")).toBeVisible();

  // Learn explains from the book, or says plainly that the AI is not switched on.
  await page.getByLabel("What would you like to understand?").fill("How do I solve 2x + 4 = 10?");
  await page.getByRole("button", { name: "Explain", exact: true }).click();
  await expect(page.getByText(/Based on:|Explanations need the AI/)).toBeVisible({ timeout: 60_000 });

  // A new family has no saved questions: practice needs the AI, or is prepared by it.
  await page.getByRole("link", { name: /Generate Questions/ }).click();
  await expect(page.getByLabel("Chapter")).toHaveValue(/.+/);
  await page.getByRole("button", { name: "Create Practice" }).click();
  await expect(
    page
      .getByText(/not switched on yet|Getting your questions ready|Ready for Dev/)
      .filter({ visible: true }),
  ).toBeVisible();
});
