import "server-only";

import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, callBackend } from "@/lib/backend";
import { ACCESS_COOKIE, storeTokens } from "@/lib/session";
import type { ClassProfile, Me, OnboardingOptions, Student } from "@/lib/types";

type Options = Parameters<typeof callBackend>[1];

/** A backend call as the signed-in session. For Server Actions, which handle the ApiError. */
export async function api<T>(path: string, options: Omit<Options, "token"> = {}): Promise<T> {
  const token = (await cookies()).get(ACCESS_COOKIE)?.value;
  return callBackend<T>(path, { ...options, token });
}

/**
 * A backend read for a page. A session the backend refuses (say the child was removed) is
 * ended through /signout; something that doesn't exist (or isn't the family's) shows "not found".
 */
async function load<T>(path: string): Promise<T> {
  try {
    return await api<T>(path);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/signout");
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export const getMe = cache(() => load<Me>("/auth/me"));

/**
 * The learner of a student session and the rules of their class. A student who has not filled in
 * their class details yet is sent to do that first. Shared by the student layout and its pages,
 * which render at the same time.
 */
export const getLearner = cache(async () => {
  const me = await getMe();
  const student = me.active_student;
  if (!student?.profile) redirect("/onboarding/profile");
  const classProfile = await getClassProfile(student.profile.class_level);
  return { me, student, profile: student.profile, classProfile };
});
export const getStudents = () => load<Student[]>("/students");
export const getStudent = (studentId: string) => load<Student>(`/students/${encodeURIComponent(studentId)}`);

/*
 * Form options and class profiles are public. They are fetched on each request rather than
 * cached, so building the app never needs the backend to be running.
 */
export const getOptions = () => callBackend<OnboardingOptions>("/meta/options");
const getClassProfile = (classLevel: string) =>
  callBackend<ClassProfile>(`/meta/classes/${encodeURIComponent(classLevel)}`);

/** Keeps the tokens of a sign-in, sign-up or child-mode start in the session cookies. */
export async function saveSession(accessToken: string, refreshToken: string | null): Promise<void> {
  storeTokens(await cookies(), accessToken, refreshToken);
}
