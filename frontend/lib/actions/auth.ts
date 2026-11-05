"use server";

import { refresh } from "next/cache";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

import { api, saveLanguage, saveSession } from "@/lib/api";
import { callBackend, endSession } from "@/lib/backend";
import { screenLanguage } from "@/lib/copy";
import { currentLanguage } from "@/lib/copy/server";
import { formError, formText, type FormState } from "@/lib/forms";
import { homeFor } from "@/lib/routes";
import { ACCESS_COOKIE } from "@/lib/session";
import type { AuthResponse, Me, Role } from "@/lib/types";

/** The browser's address as this server received it, passed on to the backend's limits. */
async function browserAddress(): Promise<string | null> {
  return (await headers()).get("x-forwarded-for");
}

async function signInWith(email: string, password: string): Promise<Role> {
  const { user, tokens } = await callBackend<AuthResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
    forwardedFor: await browserAddress(),
  });
  await saveSession(tokens.access_token, tokens.refresh_token, user.preferred_language);
  return user.role;
}

export async function signIn(_: FormState, formData: FormData): Promise<FormState> {
  const email = formText(formData, "email");
  let role: Role;
  try {
    role = await signInWith(email, String(formData.get("password") ?? ""));
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
 * Leaves child mode. The child-mode token belongs to the parent's account, so its email is
 * known; the parent proves who they are with their password and gets their own session back.
 * The child-mode session is then signed out on the backend.
 */
export async function exitChildMode(_: FormState, formData: FormData): Promise<FormState> {
  const childToken = (await cookies()).get(ACCESS_COOKIE)?.value;
  try {
    const me = await api<Me>("/auth/me");
    await signInWith(me.user.email, String(formData.get("password") ?? ""));
  } catch (error) {
    return formError(error);
  }
  await endSession(childToken);
  redirect("/who-is-learning");
}
