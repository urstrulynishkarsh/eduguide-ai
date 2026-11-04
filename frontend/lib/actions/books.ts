"use server";

import { refresh } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { api, CHOSEN_CHILD_COOKIE } from "@/lib/api";
import { ApiError } from "@/lib/backend";
import { copy } from "@/lib/copy";
import { formError, formText, type FormState } from "@/lib/forms";
import type { Book } from "@/lib/types";

const id = encodeURIComponent;

/** The child switcher of the parent area. */
export async function chooseChild(studentId: string): Promise<void> {
  (await cookies()).set(CHOSEN_CHILD_COOKIE, studentId, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
  refresh();
}

/** Step one of "Upload Book": the book itself. The browser then sends the file (see BookUploader). */
export async function createBook(_: FormState, formData: FormData): Promise<FormState & { bookId?: string }> {
  const studentId = formText(formData, "student_id");
  try {
    const book = await api<Book>("/books", {
      method: "POST",
      body: {
        title: formText(formData, "title"),
        subject: formText(formData, "subject"),
        material_type: formText(formData, "material_type"),
        student_id: studentId || null,
        class_level: studentId ? null : formText(formData, "class_level"),
      },
    });
    return { bookId: book.id };
  } catch (error) {
    return formError(error);
  }
}

export async function deleteBook(bookId: string): Promise<void> {
  await api(`/books/${id(bookId)}`, { method: "DELETE" });
  redirect("/parent/books");
}

export async function retryDocument(documentId: string): Promise<void> {
  await api(`/documents/${id(documentId)}/retry`, { method: "POST" });
  refresh();
}

export async function removeDocument(documentId: string): Promise<void> {
  await api(`/documents/${id(documentId)}`, { method: "DELETE" });
  refresh();
}

/** Analyse the previous-year papers of a book: the AI reads them in the background. */
export async function analysePapers(bookId: string): Promise<FormState> {
  try {
    await api(`/books/${id(bookId)}/paper-analysis`, { method: "POST" });
  } catch (error) {
    const state = formError(error);
    if (error instanceof ApiError && error.body.code === "ai_not_configured") {
      state.message = copy.errors.analysis_ai_not_configured;
    }
    return state;
  }
  refresh();
  return {};
}
