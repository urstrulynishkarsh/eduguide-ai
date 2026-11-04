import { expect, test } from "@playwright/test";

import { PASSWORD, tap, uniqueEmail } from "./helpers";

test("a family uses the screens in Hindi, the child's in Hinglish, then switches to English", async ({
  page,
}) => {
  const email = uniqueEmail("hindi");

  // Before there is an account: the picker of the sign-up page.
  await page.goto("/register");
  await page.getByRole("combobox", { name: "Language" }).selectOption("hi");
  await expect(page.getByRole("heading", { name: "EduGuide AI में आपका स्वागत है 👋" })).toBeVisible();
  await tap(page, "अभिभावक");
  await page.getByLabel("आपका नाम").fill("सुनीता शर्मा");
  await page.getByLabel("ईमेल").fill(email);
  await page.getByLabel("पासवर्ड").fill(PASSWORD);
  await page.getByRole("button", { name: "खाता बनाएँ" }).click();

  // The account keeps Hindi. Classes are named in Hindi too; the child is explained to in Hinglish.
  await expect(page.getByRole("heading", { name: "बच्चा जोड़ें" })).toBeVisible();
  await tap(page, "कक्षा 4");
  await page.getByLabel("बच्चे का नाम").fill("Kabir");
  await page.getByRole("radio", { name: "Hinglish" }).check({ force: true });
  await page.getByRole("button", { name: "बच्चा जोड़ें" }).click();
  await expect(page.getByRole("heading", { name: "आज कौन पढ़ रहा है?" })).toBeVisible();

  // Child mode: the screens follow the child's language until a grown-up comes back.
  await page.getByRole("button", { name: /Kabir/ }).click();
  await expect(page).toHaveURL(/\/learn$/);
  await expect(page.getByText("Aaj aap kya karna chahenge?")).toBeVisible();
  await page.getByRole("link", { name: "Badon ke liye" }).click();
  await page.getByLabel("Parent ka password").fill(PASSWORD);
  await page.getByRole("button", { name: "Aage badhein" }).click();
  await expect(page.getByRole("heading", { name: "आज कौन पढ़ रहा है?" })).toBeVisible();

  await page.getByRole("link", { name: "अभिभावक का हिस्सा" }).click();
  await expect(page.getByText("कक्षा 4 · CBSE")).toBeVisible();

  // Settings: English, for this account on every device.
  await page.goto("/parent/settings");
  await page.getByRole("combobox", { name: "भाषा" }).selectOption("en");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByRole("combobox", { name: "Language" }).selectOption("hi");
  await page.getByLabel("ईमेल").fill(email);
  await page.getByLabel("पासवर्ड").fill(PASSWORD);
  await page.getByRole("button", { name: "साइन इन करें" }).click();
  await expect(page.getByRole("heading", { name: "Who is learning today?" })).toBeVisible();
});
