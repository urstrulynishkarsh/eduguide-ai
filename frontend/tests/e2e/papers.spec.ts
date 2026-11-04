import { expect, test } from "@playwright/test";

import { chooseClass, signUp, uniqueEmail } from "./helpers";

const PAPER = `CBSE Class X Mathematics 2023
Time Allowed: 3 hours Maximum Marks: 80
SECTION A
1. Which of these is a rational number? (a) pi (b) root 2 (c) 3/4 (d) e
2. The additive inverse of 2/3 is (a) 3/2 (b) -2/3 (c) 2/3 (d) 0
SECTION B
3. Solve 2x + 3 = 7. [2]
`;

test("a previous-year paper is read into its sections, and analysing it needs the AI", async ({ page }) => {
  test.setTimeout(120_000); // the first book of a run also loads the reading model
  await signUp(page, "Parent", "Ritu Menon", uniqueEmail("papers"));
  await chooseClass(page, "Class 10", "Kabir");
  await page.getByRole("button", { name: "Add child" }).click();
  await expect(page).toHaveURL(/\/who-is-learning$/);

  await page.goto("/parent/books/upload");
  await page.getByLabel("Book name").fill("Maths board papers");
  await page.getByLabel("Subject").fill("Mathematics");
  await page.getByLabel("What is it?").selectOption({ label: "Previous-year papers" });
  await page
    .getByLabel("File")
    .setInputFiles({ name: "maths-2023.txt", mimeType: "text/plain", buffer: Buffer.from(PAPER) });
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page).toHaveURL(/\/parent\/books\/[^/]+$/);
  await expect(page.getByText(/Found 1 chapter, 2 exercises and 3 questions/)).toBeVisible({
    timeout: 90_000,
  });

  // Analysing the papers needs the AI (switched off for these journeys), or starts reading them.
  await expect(page.getByRole("heading", { name: "Previous-year papers" })).toBeVisible();
  await expect(page.getByText("Not analysed yet")).toBeVisible();
  await page.getByRole("button", { name: "Analyse the papers" }).click();
  await expect(
    page.getByText(/Analysing papers needs the AI|Reading the papers/).filter({ visible: true }),
  ).toBeVisible();

  // The paper's sections, as printed.
  await page.getByRole("link", { name: /maths 2023/ }).click();
  await expect(page.getByRole("heading", { name: "Section A" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Section B" })).toBeVisible();
  await expect(page.getByText("3. Solve 2x + 3 = 7. [2]")).toBeVisible();
});
