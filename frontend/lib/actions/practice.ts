"use server";

import { redirect } from "next/navigation";

import { api } from "@/lib/api";
import { ApiError } from "@/lib/backend";
import { copy } from "@/lib/copy";
import { formError, formText, type FormState } from "@/lib/forms";
import type { AnswerResult, Explanation, Help, PracticeSession } from "@/lib/types";

/** What the practice screen gets back: the data, or a message to show. */
export type Result<T> = { data: T } | { error: string };

const sessionPath = (sessionId: string) => `/practice/sessions/${encodeURIComponent(sessionId)}`;
const questionPath = (sessionId: string, questionId: string) =>
  `${sessionPath(sessionId)}/questions/${encodeURIComponent(questionId)}`;

async function attempt<T>(call: () => Promise<T>): Promise<Result<T>> {
  try {
    return { data: await call() };
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    const aiOff = error.body.code === "ai_not_configured";
    return { error: aiOff ? copy.errors.explain_ai_not_configured : error.body.message };
  }
}

/**
 * "Create Practice". `area` says where the practice is shown next: the parent's page (with
 * "Start now with …") or the learner's practice screen.
 */
export async function createPractice(
  area: "parent" | "learn",
  _: FormState,
  formData: FormData,
): Promise<FormState> {
  const place = ["exercise_id", "chapter_id", "book_id"].find((name) => formText(formData, name));
  const count = formText(formData, "count");
  let session: PracticeSession;
  try {
    session = await api<PracticeSession>("/practice/sessions", {
      method: "POST",
      body: {
        student_id: formText(formData, "student_id") || null,
        ...(place && { [place]: formText(formData, place) }),
        ...(count && { count: Number(count) }),
        difficulty: formText(formData, "difficulty") || "mixed",
        question_type: formText(formData, "question_type") || "mixed",
        language: formText(formData, "language") || null,
      },
    });
  } catch (error) {
    const state = formError(error);
    if (error instanceof ApiError && error.body.code === "ai_not_configured") {
      state.message = copy.errors.ai_not_configured;
    }
    return state;
  }
  redirect(`/${area === "parent" ? "parent" : "learn"}/practice/${encodeURIComponent(session.id)}`);
}

export async function answerQuestion(
  sessionId: string,
  answer: { question_id: string; option?: number; value?: number; text?: string; pairs?: number[] },
  timeTakenMs: number,
): Promise<Result<AnswerResult>> {
  return attempt(() =>
    api<AnswerResult>(`${sessionPath(sessionId)}/answers`, {
      method: "POST",
      body: { ...answer, time_taken_ms: Math.min(Math.round(timeTakenMs), 3_600_000) },
    }),
  );
}

export async function getHelp(
  sessionId: string,
  questionId: string,
  level: "hint" | "steps" | "answer",
): Promise<Result<Help>> {
  return attempt(() =>
    api<Help>(`${questionPath(sessionId, questionId)}/help`, { method: "POST", body: { level } }),
  );
}

export async function explainQuestion(
  sessionId: string,
  questionId: string,
  style: string,
): Promise<Result<Explanation>> {
  return attempt(() =>
    api<Explanation>(`${questionPath(sessionId, questionId)}/explain`, { method: "POST", body: { style } }),
  );
}

/** "Learn a Concept" and the chapter page's Learn: an explanation from the learner's own books. */
export async function explainConcept(
  place: { studentId?: string; chapterId: string },
  question: string,
  style: string,
): Promise<Result<Explanation>> {
  return attempt(() =>
    api<Explanation>("/learn/explain", {
      method: "POST",
      body: { question, style, chapter_id: place.chapterId, student_id: place.studentId ?? null },
    }),
  );
}
