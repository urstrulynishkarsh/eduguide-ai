"use server";

import { refresh } from "next/cache";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { startChildMode, type HandOver } from "@/lib/actions/students";
import { api, saveLanguage, saveSession } from "@/lib/api";
import { callBackend } from "@/lib/backend";
import { screenLanguage } from "@/lib/copy";
import { currentLanguage } from "@/lib/copy/server";
import { formError, formText, type FormState } from "@/lib/forms";
import { homeFor } from "@/lib/routes";
import type { AuthResponse, Role } from "@/lib/types";

/** The browser's address as this server received it, passed on to the backend's limits. */
async function browserAddress(): Promise<string | null> {
  return (await headers()).get("x-forwarded-for");
}

export async function signIn(_: FormState, formData: FormData): Promise<FormState> {
  const email = formText(formData, "email");
  let role: Role;
  try {
    const { user, tokens } = await callBackend<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email, password: String(formData.get("password") ?? "") },
      forwardedFor: await browserAddress(),
    });
    await saveSession(tokens.access_token, tokens.refresh_token, user.preferred_language);
    role = user.role;
  } catch (error) {
    return { ...formError(error), values: { email } };
  }
  redirect(homeFor(role));
}

export async function register(_: FormState, formData: FormData): Promise<FormState> {
  const values = {
    role: formText(formData, "role"),
    full_name: formText(formData, "full_name"),
    email: formText(formData, "email"),
  };
  let role: Role;
  try {
    const { user, tokens } = await callBackend<AuthResponse>("/auth/register", {
      method: "POST",
      // The account keeps the language the screens were in when it was made.
      body: {
        ...values,
        password: String(formData.get("password") ?? ""),
        preferred_language: await currentLanguage(),
      },
      forwardedFor: await browserAddress(),
    });
    await saveSession(tokens.access_token, tokens.refresh_token, user.preferred_language);
    role = user.role;
  } catch (error) {
    return { ...formError(error), values };
  }
  redirect(role === "parent" ? "/onboarding/child" : "/onboarding/profile");
}

/** The language picker: the screens in another language (saved on the account when signed in). */
export async function chooseLanguage(language: string): Promise<void> {
  await saveLanguage(screenLanguage(language));
  refresh();
}

/**
 * Leaves child mode with the parent PIN (typed on the number pad: nothing a browser fills in). The
 * backend ends child mode and signs the parent in again, on a session of their own.
 */
export async function leaveChildMode(_: FormState, formData: FormData): Promise<FormState> {
  try {
    const { user, tokens } = await api<AuthResponse>("/auth/child-mode/leave", {
      method: "POST",
      body: { pin: formText(formData, "pin") },
    });
    await saveSession(tokens.access_token, tokens.refresh_token, user.preferred_language);
  } catch (error) {
    return formError(error);
  }
  redirect("/who-is-learning");
}

/** The PIN form's state: a refusal, or that the PIN was saved. */
export type PinState = FormState & { saved?: boolean };

/**
 * Sets or changes the parent PIN, typed twice on the number pad; the backend checks the password.
 * Before the first hand-over (`handOver`), child mode then starts as the parent asked.
 */
export async function setPin(handOver: HandOver | null, _: PinState, formData: FormData): Promise<PinState> {
  const pin = formText(formData, "pin");
  if (pin !== formText(formData, "pin_again")) return { code: "pins_differ" };
  try {
    await api("/auth/pin", {
      method: "PUT",
      body: { password: String(formData.get("password") ?? ""), pin },
    });
  } catch (error) {
    return formError(error);
  }
  if (handOver) await startChildMode(handOver.child, handOver);
  refresh();
  return { saved: true };
}
