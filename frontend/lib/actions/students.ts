"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";

import { api, saveSession } from "@/lib/api";
import { childFromForm, formError, profileFromForm, type FormState } from "@/lib/forms";
import type { ChildSession, Me, TestAttempt } from "@/lib/types";

const path = (studentId: string) => `/students/${encodeURIComponent(studentId)}`;

/** "Add Child". From onboarding the parent goes on to pick who is learning; otherwise back to Children. */
export async function addChild(
  from: "onboarding" | "parent",
  _: FormState,
  formData: FormData,
): Promise<FormState> {
  try {
    await api("/students", {
      method: "POST",
      body: { ...childFromForm(formData), profile: profileFromForm(formData) },
    });
  } catch (error) {
    return formError(error);
  }
  refresh(); // the parent area's child switcher lists the children too
  redirect(from === "onboarding" ? "/who-is-learning" : "/parent/children");
}

export async function updateChild(studentId: string, _: FormState, formData: FormData): Promise<FormState> {
  try {
    await api(path(studentId), { method: "PATCH", body: childFromForm(formData) });
    await api(`${path(studentId)}/profile`, { method: "PUT", body: profileFromForm(formData) });
  } catch (error) {
    return formError(error);
  }
  refresh(); // the parent area's child switcher lists the children too
  redirect("/parent/children");
}

export async function removeChild(studentId: string): Promise<void> {
  await api(path(studentId), { method: "DELETE" });
  refresh(); // the parent area's child switcher lists the children too
  redirect("/parent/children");
}

/** A student who signed up alone fills in (or changes) their own class details. */
export async function saveOwnProfile(_: FormState, formData: FormData): Promise<FormState> {
  try {
    const me = await api<Me>("/auth/me");
    await api(`${path(me.active_student!.id)}/profile`, { method: "PUT", body: profileFromForm(formData) });
  } catch (error) {
    return formError(error);
  }
  redirect("/learn");
}

/**
 * The parent hands the device to a child, optionally straight into a practice or a test made for
 * them. A test's clock starts now (a sitting in progress is carried on), before the hand-over, so
 * nothing has changed if it can't. The parent's refresh token is dropped (see lib/session.ts).
 */
export async function startChildMode(
  studentId: string,
  start: { practice?: string; test?: string },
): Promise<void> {
  const id = encodeURIComponent;
  const sitting =
    start.test && (await api<TestAttempt>(`/mock-tests/${id(start.test)}/attempts`, { method: "POST" }));
  const session = await api<ChildSession>(`${path(studentId)}/session`, { method: "POST" });
  // The screens in the child's language (the language of their explanations) until a grown-up returns.
  await saveSession(session.access_token, null, session.student.profile?.primary_language ?? "en");
  if (sitting) redirect(`/learn/tests/${id(sitting.id)}`);
  redirect(start.practice ? `/learn/practice/${id(start.practice)}` : "/learn");
}
