import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { answerFor, pictureAndWord } from "@/components/answer-input";
import { PracticePlayer } from "@/components/practice-player";
import { answerQuestion, getHelp } from "@/lib/actions/practice";
import type { PracticeSession, Question } from "@/lib/types";

import { question } from "./fixtures";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }) }));
vi.mock("@/lib/actions/practice", () => ({
  answerQuestion: vi.fn(),
  getHelp: vi.fn(),
  explainQuestion: vi.fn(),
}));

function session(...questions: Question[]): PracticeSession {
  return {
    id: "s1",
    student_id: "c1",
    status: "ready",
    error: null,
    question_count: questions.length,
    answered: 0,
    correct: 0,
    items: questions.map((q) => ({
      question: q,
      attempts: 0,
      correct: null,
      hints_shown: 0,
      hints_total: 2,
      steps_shown: false,
      answer_shown: false,
    })),
  };
}

const result = (overrides = {}) => ({
  data: {
    correct: true,
    try_again: false,
    feedback: null,
    correct_answer: null,
    session_completed: false,
    ...overrides,
  },
});

beforeEach(() => vi.mocked(answerQuestion).mockReset());

describe("answerFor", () => {
  it.each([
    ["mcq", { option: 2 }, { option: 2 }],
    ["visual_choice", {}, null],
    ["numerical", { value: "2.5" }, { value: 2.5 }],
    ["counting", { value: "" }, null],
    ["fill_blank", { text: "  seven " }, { text: "seven" }],
    ["long_answer", { text: "   " }, null],
  ])("%s %j → %j", (format, draft, expected) => {
    expect(answerFor(question({ format }), draft)).toEqual(expected);
  });

  it("waits until every matching item has a partner", () => {
    const matching = question({ format: "matching", match_left: ["a", "b"], match_right: ["x", "y"] });
    expect(answerFor(matching, { pairs: [1] })).toBeNull();
    expect(answerFor(matching, { pairs: [1, 0] })).toEqual({ pairs: [1, 0] });
  });
});

it("pictureAndWord splits the picture from its word", () => {
  expect(pictureAndWord("🍎 सेब")).toEqual({ picture: "🍎", word: "सेब" });
  expect(pictureAndWord("Apple")).toEqual({ word: "Apple" });
});

describe("PracticePlayer", () => {
  it("checks a chosen option and moves on to the next question", async () => {
    vi.mocked(answerQuestion).mockResolvedValue(result());
    render(
      <PracticePlayer
        session={session(question({}), question({ id: "q2", text: "Second?" }))}
        uiMode="standard"
      />,
    );
    const user = userEvent.setup();

    expect(screen.getByRole("button", { name: "Check" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "7" }));
    await user.click(screen.getByRole("button", { name: "Check" }));

    expect(answerQuestion).toHaveBeenCalledWith("s1", { question_id: "q1", option: 1 }, expect.any(Number));
    expect(await screen.findByText("Correct! Well done 🎉")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next question" }));
    expect(screen.getByRole("heading", { name: "Second?" })).toBeInTheDocument();
  });

  it("shows the right answer after a wrong one", async () => {
    vi.mocked(answerQuestion).mockResolvedValue(result({ correct: false, correct_answer: "x = 7" }));
    render(<PracticePlayer session={session(question({}))} uiMode="dense" />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "5" }));
    await user.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByText("The answer is: x = 7")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "See results" })).toBeInTheDocument();
  });

  it("lets the youngest answer with one tap, and invites them to try again", async () => {
    vi.mocked(answerQuestion).mockResolvedValue(result({ correct: false, try_again: true }));
    const picture = question({
      format: "visual_choice",
      text: "सेब कौन सा है?",
      options: ["🍎 सेब", "🐱 बिल्ली", "🚗 कार"],
    });
    render(<PracticePlayer session={session(picture)} uiMode="playful" />);
    const user = userEvent.setup();

    expect(screen.queryByRole("button", { name: "Check" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Question 1 of/)).not.toBeInTheDocument(); // no marks, no counters
    await user.click(screen.getByRole("button", { name: "बिल्ली" }));
    expect(answerQuestion).toHaveBeenCalledWith("s1", { question_id: "q1", option: 1 }, expect.any(Number));
    expect(await screen.findByText("Let's try again! 🌟")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "सेब" })).toBeEnabled();
  });

  it("counts on a number pad for the youngest", async () => {
    vi.mocked(answerQuestion).mockResolvedValue(result());
    render(
      <PracticePlayer
        session={session(question({ format: "counting", text: "🍎🍎🍎", options: [] }))}
        uiMode="playful"
      />,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "3" }));
    expect(answerQuestion).toHaveBeenCalledWith("s1", { question_id: "q1", value: 3 }, expect.any(Number));
    expect(await screen.findByText("Yay! Well done! ⭐")).toBeInTheDocument();
  });

  it("gives a hint first, then the steps", async () => {
    vi.mocked(getHelp)
      .mockResolvedValueOnce({
        data: { hint: "Subtract 5.", hints_left: 1, concept: null, steps: [], final_answer: null },
      })
      .mockResolvedValueOnce({
        data: {
          hint: null,
          hints_left: 1,
          concept: "Undo the addition.",
          steps: ["x = 12 - 5"],
          final_answer: null,
        },
      });
    render(<PracticePlayer session={session(question({}))} uiMode="standard" />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Hint/ }));
    expect(await screen.findByText(/Subtract 5\./)).toBeInTheDocument();
    expect(screen.getByText("(1 hint left)")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Show Steps/ }));
    expect(await screen.findByText("x = 12 - 5")).toBeInTheDocument();
    expect(getHelp).toHaveBeenLastCalledWith("s1", "q1", "steps");
  });

  it("says where a generated question comes from, never that it is the book's", () => {
    render(<PracticePlayer session={session(question({}))} uiMode="standard" />);
    expect(
      screen.getByText(/Generated from concepts in: Class 7 Maths → Chapter 4 → Exercise 4\.1, page 3/),
    ).toBeInTheDocument();
  });
});
