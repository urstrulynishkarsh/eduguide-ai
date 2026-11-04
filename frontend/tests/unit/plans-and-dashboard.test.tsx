import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Recommendations, RecentTests, WeekChart } from "@/components/dashboard";
import { PlanSummary, TaskActions, TaskLine } from "@/components/plan-view";
import type { Dashboard, PlanItem, StudyPlan } from "@/lib/types";
import { en } from "@/lib/copy/en";

vi.mock("@/lib/actions/plans", () => ({ setTaskStatus: vi.fn() }));
vi.mock("@/lib/actions/practice", () => ({ createPractice: vi.fn() }));
vi.mock("@/lib/actions/tests", () => ({ createTest: vi.fn() }));

function task(overrides: Partial<PlanItem> = {}): PlanItem {
  return {
    id: "i1",
    kind: "practice",
    status: "pending",
    minutes: 20,
    reason: {
      code: "towards_aim",
      accuracy: null,
      answers: null,
      difficulty: null,
      days: null,
      mastery: 0.45,
      aim: 0.8,
    },
    book_title: "Class 7 Maths",
    chapter: "Chapter 4 Simple Equations",
    topic: null,
    practice: { student_id: "s1", chapter_id: "c1", topic_id: null, difficulty: "medium" },
    revise: null,
    test: null,
    ...overrides,
  };
}

function plan(overrides: Partial<StudyPlan> = {}): StudyPlan {
  return {
    id: "p1",
    exam_date: "2026-12-10",
    daily_minutes: 45,
    status: "active",
    days_left: 36,
    planned_on: "2026-11-04",
    unscheduled: 0,
    done: 3,
    missed: 1,
    total: 24,
    days: [],
    ...overrides,
  };
}

/** A task as the learner sees it today: its line with its buttons. */
function renderTask(item: PlanItem) {
  return render(
    <ul>
      <TaskLine copy={en} item={item}>
        <TaskActions copy={en} item={item} />
      </TaskLine>
    </ul>,
  );
}

describe("study plan", () => {
  it("sums the plan up, and says what to change when not everything fits", () => {
    render(<PlanSummary copy={en} plan={plan({ unscheduled: 4 })} />);
    expect(
      screen.getByText(
        "Exam on 10 December 2026 · 36 days to the exam · 3 of 24 tasks done · 1 missed · 45 min a day",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Not everything fits: add minutes a day or choose fewer chapters.",
    );
  });

  it("starts a practice task as it was planned, and can tick it off", () => {
    const { container } = renderTask(task());
    expect(screen.getByText(/Practice: Chapter 4 Simple Equations/)).toBeInTheDocument();
    expect(screen.getByText(/45% mastered; the aim is 80%/)).toBeInTheDocument(); // the reason, in words
    expect(screen.getByRole("button", { name: "Start: Chapter 4 Simple Equations" })).toBeInTheDocument();
    expect(container.querySelector('input[name="chapter_id"]')).toHaveValue("c1");
    expect(container.querySelector('input[name="difficulty"]')).toHaveValue("medium");
    expect(container.querySelector('input[name="topic_id"]')).toBeNull(); // empty fields are not sent
    expect(screen.getByRole("button", { name: "✓ Done" })).toBeInTheDocument();
  });

  it("opens Learn a Concept for a learn task, with its question and the task to tick off", () => {
    renderTask(
      task({
        kind: "learn",
        practice: null,
        revise: { question: "4.3 Equations in Daily Life", chapter_id: "c1" },
      }),
    );
    expect(screen.getByRole("link", { name: "Start: Chapter 4 Simple Equations" })).toHaveAttribute(
      "href",
      "/learn/concepts/c1?q=4.3%20Equations%20in%20Daily%20Life&task=i1",
    );
  });

  it("names a test task by its book, and lets a done task be undone", () => {
    renderTask(
      task({
        kind: "test",
        status: "done",
        chapter: null,
        practice: null,
        test: { kind: "practice", book_id: "b1" },
      }),
    );
    expect(screen.getByText(/Test: Class 7 Maths \(whole book\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Start/ })).not.toBeInTheDocument();
  });
});

const empty = { answered: 0, correct: 0, minutes: 0 };
const week: Dashboard["week"] = [
  { day: "2026-10-29", answered: 5, correct: 3, minutes: 12 },
  ...["2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03"].map((day) => ({ day, ...empty })),
  { day: "2026-11-04", answered: 8, correct: 8, minutes: 15 },
];

function recommendation(id: string, overrides: Partial<Dashboard["recommendations"][number]> = {}) {
  return {
    id,
    status: "active" as const,
    reason: {
      code: "weak",
      accuracy: 0.4,
      answers: 5,
      difficulty: "easy",
      days: null,
      mastery: null,
      aim: null,
    },
    chapter_id: "c1",
    chapter: "Chapter 4 Simple Equations",
    topic: `4.${id} Topic ${id}`,
    practice: { student_id: "s1", topic_id: `t${id}`, chapter_id: null, difficulty: "easy" },
    revise: { question: `4.${id} Topic ${id}`, chapter_id: "c1" },
    ...overrides,
  };
}

describe("dashboard", () => {
  it("tells screen readers the numbers of each day of the week", () => {
    render(<WeekChart copy={en} week={week} />);
    expect(
      screen.getByRole("img", { name: "Thursday, 29 October: 5 answered, 3 right the first time" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("img")).toHaveLength(7);
    expect(screen.getByText("Right the first time")).toBeInTheDocument(); // the legend
  });

  it("puts Start Recommended Practice on the parent's first recommendation", () => {
    const { container } = render(
      <Recommendations
        copy={en}
        items={[recommendation("1"), recommendation("2"), recommendation("3", { status: "done" })]}
        area="parent"
      />,
    );
    expect(
      screen.getByRole("button", { name: "Start Recommended Practice: 4.1 Topic 1" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start: 4.2 Topic 2" })).toBeInTheDocument();
    expect(screen.getByText("Done today ✓")).toBeInTheDocument();
    expect(container.querySelector('input[name="topic_id"]')).toHaveValue("t1");
    expect(screen.queryByRole("link")).not.toBeInTheDocument(); // revising is for the learner
  });

  it("lets a learner revise a weak topic's idea first", () => {
    render(<Recommendations copy={en} items={[recommendation("1")]} area="learn" />);
    expect(screen.getByRole("link", { name: "Revise the idea first" })).toHaveAttribute(
      "href",
      "/learn/concepts/c1?q=4.1%20Topic%201",
    );
  });

  it("opens the report of a recent test", () => {
    render(
      <RecentTests
        copy={en}
        tests={[
          {
            attempt_id: "a1",
            mock_test_id: "t1",
            kind: "chapter",
            place: "Chapter 4 Simple Equations",
            score: 6.5,
            total_marks: 12,
            percentage: 54.2,
            submitted_at: "2026-11-03T10:00:00Z",
          },
        ]}
      />,
    );
    const link = screen.getByRole("link", { name: /Chapter test · Chapter 4 Simple Equations/ });
    expect(link).toHaveAttribute("href", "/parent/tests/t1?attempt=a1");
    expect(link).toHaveTextContent("6.5 / 12 · 54% · 3 Nov");
  });
});
