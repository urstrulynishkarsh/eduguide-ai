import { describe, expect, it } from "vitest";

import { studentNav } from "@/lib/navigation";
import type { ClassFeatures } from "@/lib/types";

const features = (on: boolean) =>
  Object.fromEntries(
    [
      "exam_style_practice",
      "practice_tests",
      "chapter_tests",
      "adaptive_difficulty",
      "weak_topic_detection",
      "timed_tests",
      "full_mock_tests",
      "previous_year_questions",
      "board_exam_preparation",
      "competitive_exam_modes",
    ].map((name) => [name, on]),
  ) as ClassFeatures;

const labels = (mode: Parameters<typeof studentNav>[0], on = true) =>
  studentNav(mode, features(on)).map((item) => item.label);

describe("studentNav", () => {
  it("gives Nursery – Class 2 three items and no tests", () => {
    expect(labels("playful")).toEqual(["home", "playAndLearn", "myStars"]);
  });

  it("gives Class 3 – 5 four items", () => {
    expect(labels("friendly")).toEqual(["home", "practice", "learn", "progress"]);
  });

  it("gives Class 6 – 12 all seven items of the spec", () => {
    const all = ["home", "practice", "learn", "studentTests", "progress", "studyPlan", "tutor"];
    expect(labels("standard")).toEqual(all);
    expect(labels("dense")).toEqual(all);
  });

  it("hides Tests when the class has no tests", () => {
    expect(labels("standard", false)).not.toContain("studentTests");
  });
});
