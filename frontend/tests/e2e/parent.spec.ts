import { expect, test } from "@playwright/test";

import {
  chooseClass,
  choosePin,
  expectAccessible,
  expectLayout,
  formMessage,
  PASSWORD,
  signUp,
  tap,
  tapPin,
  uniqueEmail,
} from "./helpers";

test("a parent signs up, adds a child, hands over the device and takes it back", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Get Started" }).first().click();
  await expect(page).toHaveURL(/\/register$/);

  await signUp(page, "Parent", "Sunita Sharma", uniqueEmail("parent"));
  await expect(page).toHaveURL(/\/onboarding\/child$/);
  await expect(page.getByRole("heading", { name: "Add Child" })).toBeVisible();

  await chooseClass(page, "Class 7", "Aarav");
  await page.getByLabel("Age", { exact: true }).fill("12"); // not the language picker's "Language"
  await page.getByRole("button", { name: "Add child" }).click();

  // Who is learning? → the first hand-over asks for a parent PIN → child mode
  await expect(page).toHaveURL(/\/who-is-learning$/);
  await page.getByRole("button", { name: /Aarav/ }).click();
  await expect(page.getByRole("heading", { name: /Choose a parent PIN/ })).toBeVisible();
  await expectAccessible(page);
  await choosePin(page);
  await expect(page).toHaveURL(/\/learn$/);
  await expect(page.getByRole("heading", { name: "Hi Aarav 👋" })).toBeVisible();
  await expectLayout(page, "standard");

  // The child cannot wander into the parent area.
  await page.goto("/parent/children");
  await expect(page).toHaveURL(/\/learn$/);
  await page.goto("/who-is-learning");
  await expect(page).toHaveURL(/\/learn$/);

  // Nor sign out of child mode: that asks for the PIN too.
  await page.goto("/signout");
  await expect(page).toHaveURL(/\/learn\/exit$/);
  await page.getByRole("link", { name: /Back to learning/ }).click();

  // Leaving child mode needs the parent PIN, on a pad: no field for a saved password.
  await page.getByRole("link", { name: "Grown-ups" }).click();
  const pad = page.getByRole("group", { name: "Parent PIN" });
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await tapPin(pad, "1111");
  await expect(formMessage(page)).toContainText("not correct");
  await tapPin(pad);
  await expect(page).toHaveURL(/\/who-is-learning$/);

  // The PIN can be changed in Settings, with the password.
  await page.goto("/parent/settings");
  await page.getByLabel("Your password").fill(PASSWORD);
  await tapPin(page.getByRole("group", { name: "New PIN" }), "1357");
  await tapPin(page.getByRole("group", { name: "The PIN again" }), "1357");
  await page.getByRole("button", { name: "Save PIN" }).click();
  await expect(page.getByRole("status").filter({ hasText: "PIN saved." })).toBeVisible();
});

test("a parent edits and removes a child", async ({ page }) => {
  await signUp(page, "Parent", "Ravi Kumar", uniqueEmail("parent"));
  await chooseClass(page, "Class 9", "Meera");
  await page.getByRole("button", { name: "Add child" }).click();
  await expect(page).toHaveURL(/\/who-is-learning$/);

  await page.getByRole("link", { name: "Parent area" }).click();
  await expect(page.getByRole("heading", { name: "Children" })).toBeVisible();
  await expect(page.getByText("Class 9 · CBSE")).toBeVisible();

  await page.getByRole("link", { name: "Edit" }).click();
  await expect(page.getByLabel("Child's name")).toHaveValue("Meera");
  await tap(page, "Class 10");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page).toHaveURL(/\/parent\/children$/);
  await expect(page.getByText("Class 10 · CBSE")).toBeVisible();
  await expect(page.getByText("Goal: Board exams")).toBeVisible();

  await page.getByRole("link", { name: "Edit" }).click();
  await page.getByRole("button", { name: "Remove Meera" }).click();
  await page.getByRole("button", { name: "Yes, remove" }).click();
  await expect(page).toHaveURL(/\/parent\/children$/);
  await expect(page.getByText("Meera").filter({ visible: true })).toHaveCount(0);

  // With no children left, the profile picker asks for one.
  await page.goto("/who-is-learning");
  await expect(page).toHaveURL(/\/onboarding\/child$/);
});

test("Nursery – Class 2 get the playful layout without tests", async ({ page }) => {
  await signUp(page, "Parent", "Neha Gupta", uniqueEmail("parent"));
  await chooseClass(page, "UKG", "Anaya");
  await page.getByRole("button", { name: "Add child" }).click();
  await page.getByRole("button", { name: /Anaya/ }).click();
  await choosePin(page);

  await expectLayout(page, "playful");
  const menu = page.getByRole("navigation", { name: "Learning menu" });
  await expect(menu.getByText("Play & Learn")).toBeVisible();
  await expect(menu.getByText("My Stars")).toBeVisible();
  await expect(menu.getByText("Tests")).toHaveCount(0);
});

test("signing out ends the session", async ({ page }) => {
  await signUp(page, "Parent", "Arjun Mehta", uniqueEmail("parent"));
  await chooseClass(page, "Class 3", "Kiara");
  await page.getByRole("button", { name: "Add child" }).click();
  await page.goto("/parent/settings");
  await page.getByRole("button", { name: "Sign out" }).first().click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/parent/children");
  await expect(page).toHaveURL(/\/login$/);
});
