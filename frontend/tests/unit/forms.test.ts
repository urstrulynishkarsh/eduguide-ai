import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/backend";
import { childFromForm, formError, formFieldName, profileFromForm } from "@/lib/forms";

function formData(entries: [string, string][]): FormData {
  const data = new FormData();
  for (const [name, value] of entries) data.append(name, value);
  return data;
}

describe("formFieldName", () => {
  it.each([
    ["profile.class_level", "class_level"],
    ["class_level", "class_level"],
    ["profile.subjects.2", "subjects"],
    ["email", "email"],
  ])("%s → %s", (backendField, field) => {
    expect(formFieldName(backendField)).toBe(field);
  });
});

describe("formError", () => {
  it("puts the backend's messages next to the fields they are about", () => {
    const error = new ApiError(422, {
      code: "invalid_learning_profile",
      message: "Class 11 and 12 need a stream.",
      details: [
        { field: "profile.stream", message: "Choose a stream." },
        { field: "profile.goal", message: "JEE needs the Science stream." },
      ],
    });
    expect(formError(error)).toEqual({
      message: "Class 11 and 12 need a stream.",
      fieldErrors: { stream: "Choose a stream.", goal: "JEE needs the Science stream." },
    });
  });

  it("throws on anything that is not a backend error (redirects, bugs)", () => {
    const redirect = new Error("NEXT_REDIRECT");
    expect(() => formError(redirect)).toThrow(redirect);
  });
});

describe("profileFromForm", () => {
  it("sends empty choices as null and keeps every subject", () => {
    const data = formData([
      ["class_level", "class_7"],
      ["board", "cbse"],
      ["board_name", ""],
      ["medium", "en"],
      ["primary_language", "hinglish"],
      ["subjects", "Mathematics"],
      ["subjects", "Science"],
    ]);
    expect(profileFromForm(data)).toEqual({
      class_level: "class_7",
      board: "cbse",
      board_name: null,
      medium: "en",
      primary_language: "hinglish",
      stream: null,
      goal: null,
      subjects: ["Mathematics", "Science"],
    });
  });
});

describe("childFromForm", () => {
  it("reads the name and the age as a number", () => {
    expect(
      childFromForm(
        formData([
          ["name", " Aarav "],
          ["age", "12"],
        ]),
      ),
    ).toEqual({ name: "Aarav", age: 12 });
  });

  it("sends an empty age as not given", () => {
    expect(
      childFromForm(
        formData([
          ["name", "Anaya"],
          ["age", ""],
        ]),
      ),
    ).toEqual({ name: "Anaya", age: null });
  });
});
