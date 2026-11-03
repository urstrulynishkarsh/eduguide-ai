import { ApiError } from "@/lib/backend";

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

export { text as formText };
