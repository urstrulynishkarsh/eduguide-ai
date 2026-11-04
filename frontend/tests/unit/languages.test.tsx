import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CopyProvider } from "@/components/copy-provider";
import { FormMessage } from "@/components/form-message";
import { LanguagePicker } from "@/components/language-picker";
import { chooseLanguage } from "@/lib/actions/auth";
import { classLabel, copyFor, reasonText, said, SCREEN_LANGUAGES, screenLanguage } from "@/lib/copy";
import { en } from "@/lib/copy/en";
import type { Reason } from "@/lib/types";

vi.mock("@/lib/actions/auth", () => ({ chooseLanguage: vi.fn() }));

/** Every leaf of a dictionary as [path, value]; a function is called with sample values. */
function leaves(value: unknown, path = ""): [string, unknown][] {
  if (typeof value === "function") return [[path, value(...[2, 5, 3, 1].slice(0, value.length))]];
  if (Array.isArray(value)) return value.flatMap((item, i) => leaves(item, `${path}[${i}]`));
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, item]) => leaves(item, path ? `${path}.${key}` : key));
  }
  return [[path, value]];
}

// The labels and error messages English leaves to the backend; reasons are checked on their own below.
const OPEN = /^(options|errors|reasons)\./;

const REASONS: Reason[] = [
  "weak",
  "again",
  "next_level",
  "keep_going",
  "review",
  "new_chapter",
  "revise",
  "strengthen",
  "final_review",
  "learn_first",
  "first_practice",
  "towards_aim",
  "more_practice",
  "full_mock_test",
  "practice_test",
  "planned",
].map((code) => ({ code, accuracy: 0.33, answers: 6, difficulty: "easy", days: 8, mastery: 0.45, aim: 0.8 }));

describe.each(SCREEN_LANGUAGES.filter((language) => language !== "en"))("the %s screens", (language) => {
  const copy = copyFor(language);
  const words = new Map(leaves(copy));

  it("say everything the English screens say, and nothing is left empty", () => {
    for (const [path, value] of leaves(en)) {
      if (OPEN.test(path)) continue;
      expect(words.has(path), `${language}: ${path} is missing`).toBe(true);
      expect(typeof words.get(path), path).toBe(typeof value);
      if (typeof value === "string") expect(String(words.get(path)).trim(), path).not.toBe("");
    }
  });

  it("word every reason and every error English words, with its numbers", () => {
    for (const reason of REASONS) {
      const text = reasonText(copy, reason);
      expect(text, reason.code).not.toMatch(/undefined|NaN|null/);
      expect(text).not.toBe(reasonText(en, reason));
    }
    expect(reasonText(copy, REASONS[0])).toContain("33%");
    for (const code of Object.keys(en.errors)) expect(copy.errors[code], code).toBeTruthy();
  });
});

describe("words the backend sends", () => {
  it("are said in the screen language by their code, or as the backend wrote them", () => {
    const hi = copyFor("hi");
    expect(said(hi.errors, "book_not_found", "We couldn't find this book.")).toBe("हमें यह किताब नहीं मिली।");
    expect(said(hi.errors, "a_new_code", "Something new.")).toBe("Something new.");
    expect(classLabel(hi, { class_level: "class_7", class_label: "Class 7" })).toBe("कक्षा 7");
    expect(classLabel(en, { class_level: "class_7", class_label: "Class 7" })).toBe("Class 7");
    expect(reasonText(en, REASONS[0])).toBe(
      "33% right in the last 6 answers. Revise the idea, then practise easy questions.",
    );
    expect(reasonText(en, { ...REASONS[0], code: "from_a_newer_backend" })).toBe("Planned for you.");
  });

  it("are English for a language the screens don't have", () => {
    expect([screenLanguage("hi"), screenLanguage("ta"), screenLanguage(undefined)]).toEqual([
      "hi",
      "en",
      "en",
    ]);
  });

  it("show a refusal in Hindi by its code, falling back to the backend's message", () => {
    render(
      <CopyProvider language="hi">
        <FormMessage error={{ code: "unreachable" }} />
        <FormMessage error={{ code: "not_yet_translated", message: "Sorry, not yet." }} />
        <FormMessage error={{}} />
      </CopyProvider>,
    );
    const alerts = screen.getAllByRole("alert");
    expect(alerts.map((alert) => alert.textContent)).toEqual([
      copyFor("hi").errors.unreachable,
      "Sorry, not yet.",
    ]);
  });
});

describe("LanguagePicker", () => {
  it("names each language in its own words and switches the screens", async () => {
    render(
      <CopyProvider language="hinglish">
        <LanguagePicker />
      </CopyProvider>,
    );
    const picker = screen.getByRole("combobox", { name: "Bhasha" });
    expect(picker).toHaveValue("hinglish");
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
      "English",
      "हिन्दी",
      "Hinglish",
    ]);
    await userEvent.setup().selectOptions(picker, "hi");
    expect(chooseLanguage).toHaveBeenCalledWith("hi");
  });
});
