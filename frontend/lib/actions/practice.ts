"use server";

import { redirect } from "next/navigation";

import { api } from "@/lib/api";
import {
  attempt,
  formText,
  questionRequestFromForm,
  questionsError,
  type FormState,
  type Result,
} from "@/lib/forms";
import type { AnswerResult, Explanation, Help, PracticeSession } from "@/lib/types";

const sessionPath = (sessionId: string) => `/practice/sessions/${encodeURIComponent(sessionId)}`;
const questionPath = (sessionId: string, questionId: string) =>
  `${sessionPath(sessionId)}/questions/${encodeURIComponent(questionId)}`;

/**
 * "Create Practice", also from a recommendation or a task of the study plan. `area` says where the
 * practice is shown next: the parent's page (with "Start now with …") or the learner's practice screen.
 */
export async function createPractice(
  area: "parent" | "learn",
  _: FormState,
  formData: FormData,
): Promise<FormState> {
  let session: PracticeSession;
  try {
    session = await api<PracticeSession>("/practice/sessions", {
      method: "POST",
      body: {
        ...questionRequestFromForm(formData),
        question_type: formText(formData, "question_type") || "mixed",
      },
    });
  } catch (error) {
    return questionsError(error);
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
