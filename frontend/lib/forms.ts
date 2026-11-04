import { ApiError } from "@/lib/backend";
import { copy } from "@/lib/copy";

/** What a Server Action hands back to its form when the backend says no. */
export interface FormState {
  message?: string;
  fieldErrors?: Record<string, string>;
  /** Typed values to put back, so a failed sign-in doesn't empty the form. */
  values?: Record<string, string>;
}

/** "profile.class_level" and "class_level" both name the form field "class_level"; "subjects.2" is "subjects". */
export function formFieldName(backendField: string): string {
  return backendField.replace(/^profile\./, "").split(".")[0];
}

/** Turns a backend error into form state. Anything else (a redirect, a bug) is thrown on. */
export function formError(error: unknown): FormState {
  if (!(error instanceof ApiError)) throw error;
  const fieldErrors: Record<string, string> = {};
  for (const detail of error.body.details ?? []) {
    fieldErrors[formFieldName(detail.field)] ??= detail.message;
  }
  return { message: error.body.message, fieldErrors };
}

function text(formData: FormData, name: string): string {
  return String(formData.get(name) ?? "").trim();
}

/** The "Add Child" form fields as the backend's student profile. The backend checks every rule. */
export function profileFromForm(formData: FormData) {
  return {
    class_level: text(formData, "class_level"),
    board: text(formData, "board"),
    board_name: text(formData, "board_name") || null,
    medium: text(formData, "medium"),
    primary_language: text(formData, "primary_language"),
    stream: text(formData, "stream") || null,
    goal: text(formData, "goal") || null,
    subjects: formData.getAll("subjects").map(String),
  };
}

/** Name and age of the "Add Child" form. An empty age is sent as "not given". */
export function childFromForm(formData: FormData) {
  const age = text(formData, "age");
  return { name: text(formData, "name"), age: age ? Number(age) : null };
}

/**
 * The fields practice and tests share (the backend's QuestionRequest): which child, one place at
 * most (none = all books), how many, how hard, which language.
 */
export function questionRequestFromForm(formData: FormData) {
  const place = ["exercise_id", "chapter_id", "topic_id", "book_id"].find((name) => text(formData, name));
  const count = text(formData, "count");
  return {
    student_id: text(formData, "student_id") || null,
    ...(place && { [place]: text(formData, place) }),
    ...(count && { count: Number(count) }),
    difficulty: text(formData, "difficulty") || "mixed",
    language: text(formData, "language") || null,
  };
}

/** A refused practice or test. "The AI is off" is said more helpfully than the API can. */
export function questionsError(error: unknown): FormState {
  const state = formError(error);
  if (error instanceof ApiError && error.body.code === "ai_not_configured") {
    state.message = copy.errors.ai_not_configured;
  }
  return state;
}

/** What a Server Action hands back to a client component: the data, or a message to show. */
export type Result<T> = { data: T } | { error: string };

export async function attempt<T>(
  call: () => Promise<T>,
  aiOff: string = copy.errors.explain_ai_not_configured,
): Promise<Result<T>> {
  try {
    return { data: await call() };
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    return { error: error.body.code === "ai_not_configured" ? aiOff : error.body.message };
  }
}

export { text as formText };
