import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BadgeList, RewardStrip } from "@/components/rewards";
import { en } from "@/lib/copy/en";
import type { Rewards } from "@/lib/types";

function rewards(overrides: Partial<Rewards> = {}): Rewards {
  return {
    xp: 110,
    level: 2,
    level_xp: 10,
    level_size: 150,
    streak: 3,
    longest_streak: 5,
    today: { answered: 4, goal: 10 },
    badges: [
      { code: "first_practice", earned_at: "2026-11-02T10:00:00Z" },
      { code: "right_10", earned_at: null },
    ],
    ...overrides,
  };
}

describe("RewardStrip", () => {
  it("shows the streak, the level with its XP, and today's goal", () => {
    render(<RewardStrip copy={en} rewards={rewards()} />);
    expect(screen.getByText("🔥 3 days in a row")).toBeInTheDocument();
    expect(screen.getByText("10 / 150 XP")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Level 2" })).toHaveAttribute("aria-valuenow", "7");
    expect(screen.getByRole("progressbar", { name: "Today: 4 of 10 questions" })).toHaveAttribute(
      "aria-valuenow",
      "40",
    );
  });

  it("gives the youngest no XP or levels, and celebrates the day's goal", () => {
    render(<RewardStrip copy={en} rewards={rewards({ today: { answered: 5, goal: 5 } })} playful />);
    expect(screen.queryByText(/XP|Level/)).not.toBeInTheDocument();
    expect(screen.getByText("Today's goal done! 🎉")).toBeInTheDocument();
  });

  it("asks for an answer today before the streak is lost", () => {
    render(<RewardStrip copy={en} rewards={rewards({ streak: 0, today: { answered: 0, goal: 10 } })} />);
    expect(screen.getByText("🔥 No streak yet")).toBeInTheDocument();
    expect(screen.getByText(en.rewards.streakHint)).toBeInTheDocument();
  });
});

describe("BadgeList", () => {
  it("shows when a badge was earned, and how to earn the others", () => {
    const { container } = render(<BadgeList copy={en} badges={rewards().badges} />);
    expect(screen.getByText("Earned 2 Nov")).toBeInTheDocument();
    expect(screen.getByText("Get 10 questions right the first time.")).toBeInTheDocument();
    expect(container.querySelectorAll('[data-earned="true"]')).toHaveLength(1);
  });
});
