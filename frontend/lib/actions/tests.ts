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
import type { Answer, MockTest, TestAttempt } from "@/lib/types";

const id = encodeURIComponent;

/**
 * "Create Test", also the chapter page's Take Test and a test task of the study plan. The parent
 * goes on to the test's page (with "Start now with …"); the learner to their tests, where it starts
 * once its questions are ready.
 */
export async function createTest(
  area: "parent" | "learn",
  _: FormState,
  formData: FormData,
): Promise<FormState> {
  const minutes = formText(formData, "duration_minutes");
  let test: MockTest;
  try {
    test = await api<MockTest>("/mock-tests", {
      method: "POST",
      body: {
        ...questionRequestFromForm(formData),
        kind: formText(formData, "kind") || "practice",
        ...(minutes && { duration_minutes: Number(minutes) }),
      },
    });
  } catch (error) {
    return questionsError(error);
  }
  redirect(area === "parent" ? `/parent/tests/${id(test.id)}` : "/learn/tests");
}

/** The learner starts a test (the clock starts), or carries on with the sitting in progress. */
export async function startTest(testId: string): Promise<void> {
  const sitting = await api<TestAttempt>(`/mock-tests/${id(testId)}/attempts`, { method: "POST" });
  redirect(`/learn/tests/${id(sitting.id)}`);
}

/** Saved, not marked: it can be changed until the test is submitted. */
export async function saveTestAnswer(
  attemptId: string,
  questionId: string,
  answer: Answer,
): Promise<Result<void>> {
  return attempt(() =>
    api<void>(`/test-attempts/${id(attemptId)}/answers/${id(questionId)}`, { method: "PUT", body: answer }),
  );
}

/** Marks the test (written answers by the AI). The screen then shows the report. */
export async function submitTest(attemptId: string): Promise<Result<void>> {
  return attempt(
    () => api<void>(`/test-attempts/${id(attemptId)}/submit`, { method: "POST" }),
    "marking_ai_not_configured",
  );
}
