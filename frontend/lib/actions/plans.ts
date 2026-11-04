"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";

import { api } from "@/lib/api";
import { formError, formText, type FormState } from "@/lib/forms";

const id = encodeURIComponent;

/** "Make a plan" (a parent for a child, or a student for themselves). It replaces the current one. */
export async function createPlan(
  area: "parent" | "learn",
  _: FormState,
  formData: FormData,
): Promise<FormState> {
  try {
    await api("/study-plans", {
      method: "POST",
      body: {
        student_id: formText(formData, "student_id") || null,
        exam_date: formText(formData, "exam_date"),
        daily_minutes: Number(formText(formData, "daily_minutes")),
        target_score: Number(formText(formData, "target_score")),
        chapter_ids: formData.getAll("chapter_ids").map(String),
      },
    });
  } catch (error) {
    return formError(error);
  }
  redirect(area === "parent" ? "/parent/plans" : "/learn/plan");
}

/** Ticks a task off ("done"), or takes the tick back ("pending"). */
export async function setTaskStatus(itemId: string, status: "done" | "pending"): Promise<void> {
  await api(`/study-plan-items/${id(itemId)}`, { method: "PATCH", body: { status } });
  refresh();
}

export async function deletePlan(planId: string): Promise<void> {
  await api(`/study-plans/${id(planId)}`, { method: "DELETE" });
  refresh();
}
