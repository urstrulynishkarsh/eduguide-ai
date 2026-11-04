import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clock, TestPlayer } from "@/components/test-player";
import { TestReportView } from "@/components/test-report";
import { saveTestAnswer, submitTest } from "@/lib/actions/tests";
import type { TestAttempt, TestReport } from "@/lib/types";

import { question } from "./fixtures";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));
vi.mock("@/lib/actions/tests", () => ({ saveTestAnswer: vi.fn(), submitTest: vi.fn() }));

const written = question({
  id: "q2",
  number: 2,
  format: "short_answer",
  text: "What is an equation?",
  options: [],
});

function sitting(overrides: Partial<TestAttempt> = {}): TestAttempt {
  return {
    id: "a1",
    mock_test_id: "t1",
    status: "in_progress",
    seconds_left: null,
    sections: [
      { code: "A", title: "Objective questions", marks: 1, negative: 0, questions: [question({})] },
      { code: "C", title: "Short answer questions", marks: 2, negative: 0, questions: [written] },
    ],
    responses: {},
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(saveTestAnswer).mockReset().mockResolvedValue({ data: undefined });
  vi.mocked(submitTest).mockReset().mockResolvedValue({ data: undefined });
  refresh.mockReset();
});
afterEach(() => vi.useRealTimers());

describe("clock", () => {
  it.each([
    [754, "12:34"],
    [59, "00:59"],
    [3754, "1:02:34"],
  ])("%i seconds → %s", (seconds, shown) => expect(clock(seconds)).toBe(shown));
});

describe("TestPlayer", () => {
  it("saves a chosen option at once, in its section", async () => {
    render(<TestPlayer attempt={sitting()} title="Chapter test · Chapter 4" />);
    expect(screen.getByText("Section A · Objective questions · 1 mark each")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "7" }));
    await vi.waitFor(() => expect(saveTestAnswer).toHaveBeenCalledWith("a1", "q1", { option: 1 }));
    expect(screen.getByText("1 of 2 answered")).toBeInTheDocument();
  });

  it("brings back the answers saved before a reload", () => {
    render(
      <TestPlayer
        attempt={sitting({ responses: { q1: { option: 2, value: null, text: null, pairs: null } } })}
        title="Chapter test"
      />,
    );
    expect(screen.getByRole("button", { name: "12" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("1 of 2 answered")).toBeInTheDocument();
  });

  it("asks before submitting, and sends what is still being typed first", async () => {
    render(<TestPlayer attempt={sitting()} title="Chapter test" />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "2" })); // the question grid
    await user.type(screen.getByLabelText("Your answer"), "It has an equals sign.");
    await user.click(screen.getByRole("button", { name: "Submit test" }));
    expect(screen.getByText("1 question not answered yet. Submit anyway?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yes, submit" }));

    await vi.waitFor(() => expect(refresh).toHaveBeenCalled()); // the page then shows the report
    expect(saveTestAnswer).toHaveBeenCalledWith("a1", "q2", { text: "It has an equals sign." });
    expect(vi.mocked(saveTestAnswer).mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(submitTest).mock.invocationCallOrder[0],
    );
  });

  it("submits by itself when the time runs out", async () => {
    vi.useFakeTimers();
    render(<TestPlayer attempt={sitting({ seconds_left: 2 })} title="Full mock test" />);
    expect(screen.getByRole("timer")).toHaveTextContent("00:02");
    await act(() => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getByRole("timer")).toHaveTextContent("00:00");
    await vi.waitFor(() => expect(submitTest).toHaveBeenCalledWith("a1"));
  });

  it("still submits after an answer could not be sent", async () => {
    vi.mocked(saveTestAnswer).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    render(<TestPlayer attempt={sitting()} title="Chapter test" />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "7" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("We can't reach EduGuide right now.");
    await user.click(screen.getByRole("button", { name: "Submit test" }));
    await user.click(screen.getByRole("button", { name: "Yes, submit" }));
    await vi.waitFor(() => expect(refresh).toHaveBeenCalled());
  });

  it("keeps the answers when marking fails, so the test can be sent again", async () => {
    vi.mocked(submitTest).mockResolvedValue({ error: "Written answers are marked by the AI." });
    render(<TestPlayer attempt={sitting()} title="Chapter test" />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Submit test" }));
    await user.click(screen.getByRole("button", { name: "Yes, submit" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Written answers are marked by the AI.");
    expect(screen.getByRole("button", { name: "Submit test" })).toBeEnabled();
    expect(refresh).not.toHaveBeenCalled();
  });
});

const solution = { concept: "Undo the addition.", steps: ["x = 12 - 5"], final_answer: "x = 7" };
const report: TestReport = {
  score: 2.5,
  total_marks: 8,
  percentage: 31.25,
  time_taken_ms: 12 * 60_000,
  correct: 1,
  wrong: 1,
  unanswered: 1,
  sections: [
    { code: "A", title: "Objective questions", score: 1, total_marks: 1 },
    { code: "C", title: "Short answer questions", score: 1.5, total_marks: 2 },
  ],
  areas: [
    {
      chapter_id: "c1",
      chapter: "Chapter 4 Simple Equations",
      topic: "4.2 Solving Equations",
      questions: 3,
      accuracy: 1 / 3,
    },
  ],
  questions: [
    {
      question: question({}),
      marks: 1,
      marks_awarded: 1,
      correct: true,
      response: { option: 1 },
      feedback: null,
      solution,
    },
    {
      question: written,
      marks: 2,
      marks_awarded: 1.5,
      correct: false,
      response: { text: "Two sides that are equal." },
      feedback: "Add an example.",
      solution,
    },
    {
      question: question({
        id: "q3",
        number: 3,
        format: "long_answer",
        text: "Make an equation.",
        options: [],
      }),
      marks: 5,
      marks_awarded: null,
      correct: null,
      response: null,
      feedback: null,
      solution,
    },
  ],
};

describe("TestReportView", () => {
  it("shows the score, each section, the weakest topics and every question", () => {
    render(<TestReportView report={report} />);
    expect(screen.getByText("Score").nextSibling).toHaveTextContent("2.5 / 8 31%");
    expect(screen.getByText("Time taken").nextSibling).toHaveTextContent("12 min");
    expect(screen.getByText("C · Short answer questions").nextSibling).toHaveTextContent("1.5 / 2");
    expect(screen.getByText("4.2 Solving Equations")).toBeInTheDocument();

    expect(screen.getByText("Your answer: 7")).toBeInTheDocument(); // the option, not its number
    expect(screen.getByText("Add an example.")).toBeInTheDocument();
    expect(screen.getByText("0 / 5")).toBeInTheDocument();
    expect(screen.getAllByText("Solution")).toHaveLength(3);
  });
});
