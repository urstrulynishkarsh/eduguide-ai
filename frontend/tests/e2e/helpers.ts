import { expect, type Page } from "@playwright/test";

export const PASSWORD = "Secret-pass-123";

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

export async function expectLayout(page: Page, uiMode: string) {
  await expect(page.locator(`[data-ui-mode="${uiMode}"]`).first()).toBeVisible();
}
