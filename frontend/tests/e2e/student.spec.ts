import { expect, test } from "@playwright/test";

import { PASSWORD, chooseClass, expectLayout, formMessage, signUp, tap, uniqueEmail } from "./helpers";

test("a student signs up alone, fills in class details and lands in the Class 9–12 layout", async ({
  page,
}) => {
  await signUp(page, "Student", "Kabir Verma", uniqueEmail("student"));
  await expect(page).toHaveURL(/\/onboarding\/profile$/);

  // The backend's rule (Class 11–12 need a stream) is shown next to the field.
  await chooseClass(page, "Class 12");
  await page.getByRole("button", { name: "Save and start" }).click();
  await expect(formMessage(page)).toBeVisible();

  await tap(page, "Science");
  await tap(page, "JEE");
  await page.getByRole("button", { name: "Save and start" }).click();

  await expect(page).toHaveURL(/\/learn$/);
  await expect(page.getByRole("heading", { name: "Hi Kabir Verma 👋" })).toBeVisible();
  await expectLayout(page, "dense");
  const menu = page.getByRole("navigation", { name: "Learning menu" });
  for (const item of ["Home", "Practice", "Learn", "Tests", "Progress", "Study Plan", "AI Tutor"]) {
    await expect(menu.getByText(item, { exact: true })).toBeVisible();
  }

  // A student session never sees parent screens.
  await page.goto("/parent/children");
  await expect(page).toHaveURL(/\/learn$/);

  // Their own class details can be changed later.
  await page.getByRole("link", { name: "My class details" }).click();
  await expect(page.getByRole("radio", { name: "JEE" })).toBeChecked();
});

test("sign-in keeps the email after a wrong password, then signs in", async ({ page }) => {
  const email = uniqueEmail("student");
  await signUp(page, "Student", "Isha Rao", email);
  await expect(page).toHaveURL(/\/onboarding\/profile$/);
  await page.context().clearCookies();

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(formMessage(page)).toContainText("not correct");
  await expect(page.getByLabel("Email")).toHaveValue(email);

  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  // No class details yet, so the student is asked for them first.
  await expect(page).toHaveURL(/\/onboarding\/profile$/);
});

test("the landing page tells visitors what EduGuide does", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Turn Your Child's Books Into a Personalized AI Tutor" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "See How It Works" }).click();
  await expect(page.getByRole("heading", { name: "How it works" })).toBeInViewport();
});
