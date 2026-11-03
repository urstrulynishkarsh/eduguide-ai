import "server-only";

import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, callBackend } from "@/lib/backend";
import { ACCESS_COOKIE, storeTokens } from "@/lib/session";
import type {
  Book,
  Chapter,
  ChapterDetail,
  ClassProfile,
  ExerciseDetail,
  Me,
  OnboardingOptions,
  PracticeSession,
  Progress,
  Student,
} from "@/lib/types";

type Options = Parameters<typeof callBackend>[1];

/** The child whose data the parent area shows (the child switcher). Not secret: just a choice. */
export const CHOSEN_CHILD_COOKIE = "eg_child";

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

const id = encodeURIComponent;

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

export const getStudents = cache(() => load<Student[]>("/students"));
export const getStudent = (studentId: string) => load<Student>(`/students/${id(studentId)}`);

/** The parent area's children and the one chosen in the switcher (the first, until one is chosen). */
export const getChosenChild = cache(async () => {
  const [children, store] = await Promise.all([getStudents(), cookies()]);
  const chosenId = store.get(CHOSEN_CHILD_COOKIE)?.value;
  return { children, child: children.find((child) => child.id === chosenId) ?? children[0] ?? null };
});

/** The chosen child for a parent page that is about one child; a parent with none adds one first. */
export async function requireChosenChild(): Promise<Student> {
  const { child } = await getChosenChild();
  if (!child) redirect("/onboarding/child");
  return child;
}

/** My Learning Library: a child's books and the family's shared ones (the API's maximum page). */
export async function getBooks(studentId?: string): Promise<Book[]> {
  const forChild = studentId ? `&student_id=${id(studentId)}` : "";
  return (await load<{ items: Book[] }>(`/books?limit=100${forChild}`)).items;
}
export const getBook = (bookId: string) => load<Book>(`/books/${id(bookId)}`);
export const getChapters = (bookId: string) => load<Chapter[]>(`/books/${id(bookId)}/chapters`);
export const getChapter = (chapterId: string) => load<ChapterDetail>(`/chapters/${id(chapterId)}`);
export const getExercise = (exerciseId: string) => load<ExerciseDetail>(`/exercises/${id(exerciseId)}`);
export const getPractice = (sessionId: string) =>
  load<PracticeSession>(`/practice/sessions/${id(sessionId)}`);
export const getProgress = (studentId: string) => load<Progress>(`/students/${id(studentId)}/progress`);

/*
 * Form options and class profiles are public. They are fetched on each request rather than
 * cached, so building the app never needs the backend to be running.
 */
export const getOptions = () => callBackend<OnboardingOptions>("/meta/options");
export const getClassProfile = (classLevel: string) =>
  callBackend<ClassProfile>(`/meta/classes/${id(classLevel)}`);

/** Keeps the tokens of a sign-in, sign-up or child-mode start in the session cookies. */
export async function saveSession(accessToken: string, refreshToken: string | null): Promise<void> {
  storeTokens(await cookies(), accessToken, refreshToken);
}
