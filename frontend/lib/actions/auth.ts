"use server";

import { redirect } from "next/navigation";

import { api, saveSession } from "@/lib/api";
import { callBackend } from "@/lib/backend";
import { formError, formText, type FormState } from "@/lib/forms";
import { homeFor } from "@/lib/routes";
import type { AuthResponse, Me, Role } from "@/lib/types";

async function signInWith(email: string, password: string): Promise<Role> {
  const { user, tokens } = await callBackend<AuthResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
  await saveSession(tokens.access_token, tokens.refresh_token);
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
      body: { ...values, password: String(formData.get("password") ?? "") },
    });
    await saveSession(tokens.access_token, tokens.refresh_token);
    role = user.role;
  } catch (error) {
    return { ...formError(error), values };
  }
  redirect(role === "parent" ? "/onboarding/child" : "/onboarding/profile");
}

/**
 * Leaves child mode. The child-mode token belongs to the parent's account, so its email is
 * known; the parent proves who they are with their password and gets their own session back.
 */
export async function exitChildMode(_: FormState, formData: FormData): Promise<FormState> {
  try {
    const me = await api<Me>("/auth/me");
    await signInWith(me.user.email, String(formData.get("password") ?? ""));
  } catch (error) {
    return formError(error);
  }
  redirect("/who-is-learning");
}
