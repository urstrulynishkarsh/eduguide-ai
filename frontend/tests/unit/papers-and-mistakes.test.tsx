import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Mistakes } from "@/components/dashboard";
import { PaperAnalysisView } from "@/components/paper-analysis";
import { testSummary } from "@/components/test-report";
import { copy } from "@/lib/copy";
import type { Misconception, MockTest, PaperAnalysis } from "@/lib/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));
vi.mock("@/lib/actions/books", () => ({ analysePapers: vi.fn() }));
vi.mock("@/lib/actions/practice", () => ({ createPractice: vi.fn() }));
vi.mock("@/lib/actions/tests", () => ({ createTest: vi.fn() }));

function mistake(overrides: Partial<Misconception> = {}): Misconception {
  return {
    id: "m1",
    status: "active",
    chapter_id: "c1",
    chapter: "Chapter 4 Simple Equations",
    topic: "4.2 Solving Equations",
    pattern: "Moves a number across the = sign without changing its sign.",
    fix: "When a number moves across =, its sign changes.",
    answers: 2,
    practice: { student_id: "s1", topic_id: "t1", chapter_id: null, difficulty: "mixed" },
    revise: { question: "Why does the sign change?", chapter_id: "c1" },
    ...overrides,
  };
}

const ANALYSIS: PaperAnalysis = {
  status: "ready",
  papers: [
    {
      document_id: "d2",
      title: "maths 2023",
      status: "ready",
      error: null,
      year: 2023,
      questions: 38,
      total_marks: 80,
    },
    {
      document_id: "d3",
      title: "maths 2024",
      status: "new",
      error: null,
      year: null,
      questions: 0,
      total_marks: 0,
    },
  ],
  chapters: [
    {
      chapter_id: "c2",
      chapter: "Chapter 5 Arithmetic Progressions",
      topic: null,
      marks_per_paper: 8.5,
      share: 0.11,
      papers: 2,
      trend: "rising",
      practice: { student_id: null, chapter_id: "c2", topic_id: null, difficulty: "mixed" },
    },
  ],
  unmatched: { questions: 3 },
  topics: [
    { chapter_id: "c2", chapter: "Chapter 5", topic: "5.3 nth Term of an AP", questions: 4, papers: 2 },
  ],
  formats: [{ format: "mcq", share: 0.53 }],
  layout: [{ title: "Section A", questions: 20, marks: 1 }],
  layout_year: 2023,
  test: { student_id: null, kind: "previous_year", book_id: "b1" },
};

describe("Understand Mistakes", () => {
  it("says what the child keeps doing and what to remember, with a practice of that topic", () => {
    const { container } = render(<Mistakes items={[mistake()]} area="parent" />);
    expect(screen.getByText(/Moves a number across the = sign/)).toBeInTheDocument();
    expect(screen.getByText("4.2 Solving Equations · Seen in 2 answers")).toBeInTheDocument();
    expect(screen.getByText(/When a number moves across =/)).toHaveTextContent("Remember:");
    expect(screen.getByRole("button", { name: "Practise this: 4.2 Solving Equations" })).toBeInTheDocument();
    expect(container.querySelector('input[name="topic_id"]')).toHaveValue("t1");
    expect(screen.queryByRole("link")).not.toBeInTheDocument(); // the idea again is for the learner
  });

  it("lets the learner learn the idea again, and marks one put right", () => {
    render(<Mistakes items={[mistake(), mistake({ id: "m2", status: "resolved" })]} area="learn" />);
    expect(screen.getByRole("link", { name: "Revise the idea first" })).toHaveAttribute(
      "href",
      "/learn/concepts/c1?q=Why%20does%20the%20sign%20change%3F",
    );
    expect(screen.getByText("Put right ✓")).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });
});

describe("previous-year papers", () => {
  it("shows where the marks go, with a practice and a test like the papers for the child", () => {
    const { container } = render(
      <PaperAnalysisView bookId="b1" analysis={ANALYSIS} studentId="s1" classLabel="Class 10" />,
    );
    expect(screen.getByText("2023 · 38 questions · 80 marks")).toBeInTheDocument();
    expect(screen.getByText("Not analysed yet")).toBeInTheDocument();
    expect(screen.getByText("8.5 marks a paper · in 2 of 2 papers · ↑ More each year")).toBeInTheDocument();
    expect(screen.getByText("3 questions not from your textbooks.")).toBeInTheDocument();
    expect(screen.getByText("The 2023 paper")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Practise: Chapter 5 Arithmetic Progressions" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyse again" })).toBeInTheDocument();
    const test = screen.getByRole("button", { name: "Make a test like these papers" }).closest("form")!;
    expect(test.querySelector('input[name="kind"]')).toHaveValue("previous_year");
    expect(test.querySelector('input[name="student_id"]')).toHaveValue("s1");
    expect(container.querySelectorAll('input[name="student_id"][value="s1"]')).toHaveLength(2);
  });

  it("offers nothing to practise for a child of another class, and starts with Analyse", () => {
    render(
      <PaperAnalysisView
        bookId="b1"
        analysis={{ ...ANALYSIS, status: "none", papers: [{ ...ANALYSIS.papers[1] }] }}
        studentId={null}
        classLabel="Class 10"
      />,
    );
    expect(screen.getByRole("button", { name: "Analyse the papers" })).toBeInTheDocument();
    expect(screen.queryByText(copy.papers.whereMarks)).not.toBeInTheDocument();

    render(<PaperAnalysisView bookId="b1" analysis={ANALYSIS} studentId={null} classLabel="Class 10" />);
    expect(screen.getByText(copy.papers.otherClass("Class 10"))).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Practise|Make a test/ })).not.toBeInTheDocument();
  });

  it("names the exam pattern of a test, and the marks lost for a wrong answer", () => {
    const test = { question_count: 25, total_marks: 100, duration_minutes: 60, exam: "jee" } as MockTest;
    expect(testSummary(test)).toBe("25 questions · 100 marks · 60 min · JEE Main pattern");
    expect(copy.tests.sectionTitle("A", "Objective questions", 4, 1)).toBe(
      "Section A · Objective questions · 4 marks each, −1 for a wrong answer",
    );
    expect(copy.tests.sectionTitle("C", "Short answer questions", 2, 0)).toBe(
      "Section C · Short answer questions · 2 marks each",
    );
  });
});
