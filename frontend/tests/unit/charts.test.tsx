import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LineChart, Sparkline } from "@/components/charts";
import { ProgressOverTime } from "@/components/progress-over-time";
import { en } from "@/lib/copy/en";
import type { Trends } from "@/lib/types";

// 12 Mondays, oldest first, ending on 2 November 2026.
const weeks = Array.from({ length: 12 }, (_, i) => ({
  day: new Date(Date.UTC(2026, 10, 2) - (11 - i) * 7 * 86_400_000).toISOString().slice(0, 10),
  answered: i === 11 ? 10 : i === 8 ? 4 : 0,
  correct: i === 11 ? 7 : i === 8 ? 3 : 0,
  minutes: i === 11 ? 12 : 0,
}));

function trends(overrides: Partial<Trends> = {}): Trends {
  return {
    weeks,
    subjects: [{ code: "Mathematics", answered: 14, accuracy: 0.714 }],
    formats: [{ code: "mcq", answered: 14, accuracy: 0.714 }],
    difficulties: [{ code: "medium", answered: 14, accuracy: 0.714 }],
    tests: [
      {
        attempt_id: "a1",
        mock_test_id: "t1",
        kind: "chapter",
        place: "Chapter 4 Simple Equations",
        score: 20,
        total_marks: 25,
        percentage: 80,
        submitted_at: "2026-11-03T08:00:00Z",
      },
    ],
    ...overrides,
  };
}

describe("ProgressOverTime", () => {
  it("draws the 12 weeks, the test scores and the shares, each with its numbers in a table", () => {
    render(<ProgressOverTime copy={en} trends={trends()} />);
    const weeksChart = screen.getByRole("group", { name: "The last 12 weeks" });
    expect(within(weeksChart).getAllByRole("img")).toHaveLength(12);
    expect(
      within(weeksChart).getByRole("img", { name: "Week of 2 Nov: 10 answered, 7 right the first time" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Chapter test · Chapter 4 Simple Equations, 3 Nov: 80%" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "By kind of question" })).toBeInTheDocument();
    expect(screen.getByText("MCQ")).toBeInTheDocument(); // the format in words
    expect(screen.getAllByText("Show the numbers")).toHaveLength(2);
    expect(screen.getByRole("row", { name: "2 Nov 10 7 12" })).toBeInTheDocument();
  });

  it("keeps it simple for Class 3 – 5, and shows nothing before any work", () => {
    const { unmount } = render(<ProgressOverTime copy={en} trends={trends()} simple />);
    expect(screen.queryByRole("group", { name: "Test scores" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "By difficulty" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "By subject" })).toBeInTheDocument();
    unmount();

    const idle = weeks.map((week) => ({ ...week, answered: 0, correct: 0, minutes: 0 }));
    const { container } = render(<ProgressOverTime copy={en} trends={trends({ weeks: idle, tests: [] })} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("charts", () => {
  it("scales a line to scores below zero (wrong answers lose marks)", () => {
    render(
      <LineChart
        label="Scores"
        points={[{ key: "1", tick: "1 Nov", label: "JEE test: −20%", value: -20 }]}
      />,
    );
    expect(screen.getByText("-20%", { selector: "span.-mb-2" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "JEE test: −20%" })).toBeInTheDocument();
  });

  it("names a sparkline's values", () => {
    render(<Sparkline values={[6, 8, 10]} label="Marks by year: 2022: 6, 2023: 8, 2024: 10" />);
    expect(
      screen.getByRole("img", { name: "Marks by year: 2022: 6, 2023: 8, 2024: 10" }),
    ).toBeInTheDocument();
  });
});
