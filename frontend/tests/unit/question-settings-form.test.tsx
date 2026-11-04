import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QuestionSettingsForm } from "@/components/question-settings-form";
import type { ClassFeatures, ClassProfile } from "@/lib/types";

import { options } from "./fixtures";

vi.mock("@/lib/actions/practice", () => ({ createPractice: vi.fn() }));
vi.mock("@/lib/actions/tests", () => ({ createTest: vi.fn() }));

function classProfile(timed: boolean): ClassProfile {
  return {
    class_level: timed ? "class_10" : "class_7",
    label: timed ? "Class 10" : "Class 7",
    ui_mode: timed ? "dense" : "standard",
    features: { timed_tests: timed } as ClassFeatures,
    question_formats: ["mcq", "short_answer"],
    default_session_questions: 10,
    max_session_questions: 30,
  };
}

const place = { student_id: "s1", book_id: "b1", chapter_id: undefined, exercise_id: undefined };

function renderForm(test: "practice" | "chapter" | "full_mock" | undefined, timed = false, chapter?: string) {
  return render(
    <QuestionSettingsForm
      area="parent"
      place={{ ...place, chapter_id: chapter }}
      test={test}
      classProfile={classProfile(timed)}
      languages={options.languages}
      defaultLanguage="en"
    />,
  );
}

describe("QuestionSettingsForm", () => {
  it("makes practice with the class's usual number and a question type, never a time limit", () => {
    renderForm(undefined, true);
    expect(screen.getByLabelText("Number of questions")).toHaveValue(10);
    expect(screen.getByLabelText("Question type")).toBeInTheDocument();
    expect(screen.queryByLabelText("Time limit in minutes")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Practice" })).toBeEnabled();
  });

  it("offers a time limit only where the class has timed tests", () => {
    const { container } = renderForm("practice");
    expect(screen.queryByLabelText("Time limit in minutes")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Number of questions")).toHaveValue(null); // the usual length
    expect(screen.queryByLabelText("Question type")).not.toBeInTheDocument();
    expect(container.querySelector('input[name="kind"]')).toHaveValue("practice");
    container.remove();

    renderForm("full_mock", true);
    expect(screen.getByLabelText("Time limit in minutes")).toHaveAccessibleDescription(
      "Leave empty for about 2 minutes a mark.",
    );
  });

  it("waits for a chapter before making a chapter test", () => {
    renderForm("chapter");
    expect(screen.getByText("Choose a chapter for a chapter test.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Test" })).toBeDisabled();
  });

  it("makes a chapter test once the chapter is chosen", () => {
    const { container } = renderForm("chapter", false, "c1");
    expect(screen.getByRole("button", { name: "Create Test" })).toBeEnabled();
    expect(container.querySelector('input[name="chapter_id"]')).toHaveValue("c1");
  });
});
