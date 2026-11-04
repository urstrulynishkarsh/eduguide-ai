import "server-only";

import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, callBackend } from "@/lib/backend";
import { ACCESS_COOKIE, storeLanguage, storeTokens } from "@/lib/session";
import type {
  Book,
  Chapter,
  ChapterDetail,
  Chat,
  ChatKind,
  ChatSummary,
  ClassProfile,
  Dashboard,
  ExerciseDetail,
  Me,
  Misconception,
  MockTest,
  MockTestDetail,
  OnboardingOptions,
  PaperAnalysis,
  PracticeSession,
  Progress,
  Rewards,
  Student,
  StudyPlan,
  TestAttempt,
  TestReport,
  Trends,
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
 * A failed backend read of a page. A session the backend refuses (say the child was removed) is
 * ended through /signout; something that doesn't exist (or isn't the family's) shows "not found".
 */
function failed(error: unknown): never {
  if (error instanceof ApiError && error.status === 401) redirect("/signout");
  if (error instanceof ApiError && error.status === 404) notFound();
  throw error;
}

async function load<T>(path: string): Promise<T> {
  try {
    return await api<T>(path);
  } catch (error) {
    return failed(error);
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

/** Each book with its chapters (Make a plan lists them). */
export async function getBooksWithChapters(studentId?: string) {
  const books = await getBooks(studentId);
  const chapters = await Promise.all(books.map((book) => getChapters(book.id)));
  return books.map((book, i) => ({ id: book.id, title: book.title, chapters: chapters[i] }));
}
export const getChapter = (chapterId: string) => load<ChapterDetail>(`/chapters/${id(chapterId)}`);
export const getExercise = (exerciseId: string) => load<ExerciseDetail>(`/exercises/${id(exerciseId)}`);
export const getPractice = (sessionId: string) =>
  load<PracticeSession>(`/practice/sessions/${id(sessionId)}`);
export const getProgress = (studentId: string) => load<Progress>(`/students/${id(studentId)}/progress`);
export const getDashboard = (studentId: string) => load<Dashboard>(`/students/${id(studentId)}/dashboard`);
export const getTrends = (studentId: string) => load<Trends>(`/students/${id(studentId)}/progress/trends`);
export const getRewards = (studentId: string) => load<Rewards>(`/students/${id(studentId)}/rewards`);
export const getMisconceptions = async (studentId: string) =>
  (await load<{ items: Misconception[] }>(`/students/${id(studentId)}/misconceptions`)).items;
export const getPaperAnalysis = (bookId: string) =>
  load<PaperAnalysis>(`/books/${id(bookId)}/paper-analysis`);

/** A learner's tests, newest first (the API's maximum page). */
export async function getTests(studentId: string): Promise<MockTest[]> {
  return (await load<{ items: MockTest[] }>(`/students/${id(studentId)}/mock-tests?limit=50`)).items;
}
export const getTest = (testId: string) => load<MockTestDetail>(`/mock-tests/${id(testId)}`);
export const getAttempt = (attemptId: string) => load<TestAttempt>(`/test-attempts/${id(attemptId)}`);
export const getReport = (attemptId: string) => load<TestReport>(`/test-attempts/${id(attemptId)}/report`);

/** The learner's study plan, or null before one is made. */
export async function getPlan(studentId: string): Promise<StudyPlan | null> {
  try {
    return await api<StudyPlan>(`/students/${id(studentId)}/study-plan`);
  } catch (error) {
    if (error instanceof ApiError && error.body.code === "study_plan_not_found") return null;
    return failed(error);
  }
}

/** Conversations with the assistant or the tutor that have begun, newest first. */
export async function getChats(kind: ChatKind, studentId: string): Promise<ChatSummary[]> {
  const page = await load<{ items: ChatSummary[] }>(
    `/chat/sessions?kind=${kind}&student_id=${id(studentId)}&limit=50`,
  );
  return page.items.filter((chat) => chat.title);
}
export const getChat = (chatId: string) => load<Chat>(`/chat/sessions/${id(chatId)}`);

/*
 * Form options and class profiles are public. They are fetched on each request rather than
 * cached, so building the app never needs the backend to be running.
 */
export const getOptions = () => callBackend<OnboardingOptions>("/meta/options");
export const getClassProfile = (classLevel: string) =>
  callBackend<ClassProfile>(`/meta/classes/${id(classLevel)}`);

/**
 * Keeps the tokens of a sign-in, sign-up or child-mode start in the session cookies, and the screen
 * language the session starts in: the account's, or in child mode the child's.
 */
export async function saveSession(
  accessToken: string,
  refreshToken: string | null,
  language: string,
): Promise<void> {
  const store = await cookies();
  storeTokens(store, accessToken, refreshToken);
  storeLanguage(store, language);
}

/** The screen language chosen on the language picker: the device's, and the account's when signed in. */
export async function saveLanguage(language: string): Promise<void> {
  const store = await cookies();
  if (store.has(ACCESS_COOKIE))
    await api("/auth/me", { method: "PATCH", body: { preferred_language: language } });
  storeLanguage(store, language);
}
