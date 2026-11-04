import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { stepsInParentWords } from "@/components/document-checklist";
import { ProgressView } from "@/components/progress-view";
import type { Progress } from "@/lib/types";
import { en } from "@/lib/copy/en";

describe("stepsInParentWords", () => {
  it("tells the parent what is happening in plain words, one line per idea", () => {
    const lines = stepsInParentWords(en, [
      { step: "extract_text", state: "done" },
      { step: "detect_chapters", state: "done" },
      { step: "detect_exercises", state: "active" },
      { step: "detect_topics", state: "pending" },
      { step: "make_chunks", state: "pending" },
      { step: "embed_chunks", state: "pending" },
    ]);
    expect(lines).toEqual([
      { label: "Reading your book", state: "done" },
      { label: "Finding the chapters", state: "done" },
      { label: "Finding exercises and questions", state: "active" },
      { label: "Understanding the topics", state: "pending" },
      { label: "Getting practice ready", state: "pending" },
    ]);
    const words = lines
      .map((line) => line.label)
      .join(" ")
      .toLowerCase();
    for (const banned of ["chunk", "embedding", "index", "extract"]) expect(words).not.toContain(banned);
  });

  it("marks a shared line done only when all of its steps are", () => {
    expect(
      stepsInParentWords(en, [
        { step: "make_chunks", state: "done" },
        { step: "embed_chunks", state: "active" },
      ]),
    ).toEqual([{ label: "Getting practice ready", state: "active" }]);
  });
});

const progress: Progress = {
  questions_answered: 10,
  correct_first_time: 7,
  accuracy: 0.7,
  time_spent_ms: 5 * 60_000,
  hints_used: 2,
  sessions_completed: 1,
  by_chapter: [{ id: "c1", name: "Chapter 4 Simple Equations", attempted: 10, accuracy: 0.7 }],
  by_topic: [],
  recent_sessions: [],
};

describe("ProgressView", () => {
  it("shows numbers and accuracy by chapter", () => {
    render(<ProgressView copy={en} progress={progress} />);
    expect(screen.getByText("Correct the first time").nextSibling).toHaveTextContent("70%");
    expect(screen.getByText("Chapter 4 Simple Equations")).toBeInTheDocument();
    expect(screen.getByText("5 min")).toBeInTheDocument();
  });

  it("shows the youngest stars, never marks or percentages", () => {
    const { container } = render(<ProgressView copy={en} progress={progress} stars />);
    expect(screen.getByText("You earned 7 stars!")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/%|correct/i);
  });
});
