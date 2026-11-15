import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page } from "@playwright/test";

export const PASSWORD = "Secret-pass-123";
/** The parent PIN of the journeys' parents, and of the demo parent (backend/scripts/seed.py). */
export const PIN = "2468";
export const SAMPLE_BOOK = path.resolve(
  __dirname,
  "../../../backend/scripts/sample_data/class7-maths-sample.txt",
);

/** A new email for every test run, so runs never collide with each other or the demo accounts. */
export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

export async function signUp(page: Page, role: "Parent" | "Student", name: string, email: string) {
  await page.goto("/register");
  await tap(page, role);
  await page.getByLabel("Your name").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
}

/**
 * Taps a choice chip or card by its text. Only visible ones count: with Cache Components the
 * previous page stays mounted, hidden, so its form may still be in the document.
 */
export async function tap(page: Page, text: string) {
  await page.getByText(text, { exact: true }).filter({ visible: true }).click();
}

/** Fills the class-first form: the class, then (for a child) the name. */
export async function chooseClass(page: Page, classLabel: string, childName?: string) {
  await tap(page, classLabel);
  if (childName) await page.getByLabel("Child's name").fill(childName);
}

/** The message of a refused form (not Next.js's own route announcer, which is also an alert). */
export function formMessage(page: Page) {
  return page.locator("form").getByRole("alert");
}

/**
 * The screen as it is now breaks none of the WCAG 2.2 A and AA rules axe can check: labels,
 * contrast on the cream theme, `autocomplete` values, ARIA… Screens kept mounted but hidden (Cache
 * Components) are not looked at. A soft check: the journey goes on, so one run lists every screen's
 * problems, each with axe's reason (for contrast: the colours and the ratio).
 */
export async function expectAccessible(page: Page) {
  await page.waitForLoadState("networkidle");
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const found = violations.flatMap(({ id, nodes }) =>
    nodes.map((node) => `${id}: ${node.target} – ${node.any[0]?.message ?? node.failureSummary}`),
  );
  expect.soft(found, `on ${page.url()}`).toEqual([]);
}

export async function expectLayout(page: Page, uiMode: string) {
  await expect(page.locator(`[data-ui-mode="${uiMode}"]`).first()).toBeVisible();
}

/*
 * The demo family (python -m scripts.seed): the practice journeys use its sample books and their
 * demo questions, so they run without an AI key. Each journey adds its own temporary child, so
 * Aarav's and Anaya's questions are never used up, and removes it at the end.
 */
export async function signInDemoParent(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill("parent@example.com");
  await page.getByLabel("Password").fill("DemoParent123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/who-is-learning$/);
}

/** Adds a child with a unique name and makes them the parent area's chosen child. */
export async function addTemporaryChild(page: Page, classLabel: string, language: string): Promise<string> {
  const name = `E2E${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`;
  await page.goto("/parent/children/new");
  await chooseClass(page, classLabel, name);
  await page.getByRole("radio", { name: language }).check({ force: true });
  await page.getByRole("button", { name: "Add child" }).click();
  await expect(page).toHaveURL(/\/parent\/children$/);
  await page.getByLabel("Showing").selectOption({ label: `${name} · ${classLabel}` });
  await expect(page.getByLabel("Showing")).toBeEnabled(); // disabled while the choice is being saved
  await page.waitForLoadState("networkidle");
  return name;
}

export async function removeChild(page: Page, name: string) {
  await page.goto("/parent/children");
  await page
    .getByRole("listitem")
    .filter({ hasText: name })
    .filter({ visible: true })
    .getByRole("link", { name: "Edit" })
    .click();
  await page.getByRole("button", { name: `Remove ${name}` }).click();
  await page.getByRole("button", { name: "Yes, remove" }).click();
  await expect(page).toHaveURL(/\/parent\/children$/);
}

/** From the parent area: open a sample book's first chapter. */
export async function openFirstChapter(page: Page, bookTitle: string) {
  await page.goto("/parent/books");
  await page
    .getByRole("link", { name: new RegExp(bookTitle) })
    .first()
    .click();
  await page.locator('a[href*="/chapters/"]').filter({ visible: true }).first().click();
}

/** From the parent area: start practice on a sample book's first chapter. */
export async function practiseChapter(page: Page, bookTitle: string) {
  await openFirstChapter(page, bookTitle);
  await page.getByRole("button", { name: "✏️ Practice", exact: true }).click();
  await expect(page).toHaveURL(/\/parent\/practice\/[^/?]+$/);
}

/** Taps a PIN on a number pad. Its buttons are digits in every language. */
export async function tapPin(pad: Locator, pin = PIN) {
  for (const digit of pin) await pad.getByRole("button", { name: digit, exact: true }).click();
}

/** A new parent's first hand-over: the parent PIN is chosen, then child mode starts. */
export async function choosePin(page: Page) {
  await expect(page).toHaveURL(/\/who-is-learning\/pin\?/);
  await page.getByLabel("Your password").fill(PASSWORD);
  await tapPin(page.getByRole("group", { name: "New PIN" }));
  await tapPin(page.getByRole("group", { name: "The PIN again" }));
  await page.getByRole("button", { name: "Save PIN and start" }).click();
}

/** Leaves child mode with the parent PIN. Its screens are in the child's language: the pad's are digits. */
export async function leaveChildMode(page: Page) {
  await page.goto("/learn/exit");
  await tapPin(page.locator("main form").filter({ visible: true }));
  await expect(page).toHaveURL(/\/who-is-learning$/);
}

/** Upload Book from My Books: the sample Class 7 chapter, for the chosen child, read to the end. */
export async function uploadSampleBook(page: Page) {
  await page.goto("/parent/books");
  await page
    .getByRole("link", { name: /Upload Book/ })
    .first()
    .click();
  await page.getByLabel("Book name").fill("Class 7 Mathematics");
  await page.getByLabel("Subject").fill("Mathematics");
  await page.getByLabel("File").setInputFiles(SAMPLE_BOOK);
  await page.getByRole("button", { name: "Upload" }).click();

  // The checklist is in parent words, and the page follows it until the book is read.
  await expect(page).toHaveURL(/\/parent\/books\/[^/]+$/);
  await expect(page.getByText("Reading your book")).toBeVisible();
  await expect(page.getByText(/Found 1 chapter, 2 exercises/)).toBeVisible({ timeout: 90_000 });
}
