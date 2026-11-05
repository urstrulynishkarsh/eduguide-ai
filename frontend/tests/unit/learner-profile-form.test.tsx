import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LearnerProfileForm } from "@/components/learner-profile-form";

import { options } from "./fixtures";

function renderForm(props: Partial<React.ComponentProps<typeof LearnerProfileForm>> = {}) {
  const action = vi.fn(async () => ({}));
  render(<LearnerProfileForm options={options} action={action} submitLabel="Add child" askName {...props} />);
  return { user: userEvent.setup(), action };
}

const radio = (name: string) => screen.getByRole("radio", { name });

describe("LearnerProfileForm", () => {
  it("asks for the class first and shows the rest only after it", async () => {
    const { user } = renderForm();
    expect(screen.queryByLabelText("Child's name")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add child" })).toBeDisabled();

    await user.click(radio("Class 7"));
    expect(screen.getByLabelText("Child's name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add child" })).toBeEnabled();
  });

  it("offers the goals of the chosen class, with its default picked", async () => {
    const { user } = renderForm();
    await user.click(radio("UKG"));
    expect(radio("Build strong basics")).toBeChecked();
    expect(screen.queryByRole("radio", { name: "School exams" })).not.toBeInTheDocument();

    await user.click(radio("Class 7"));
    expect(radio("School exams")).toBeChecked();
    expect(screen.queryByRole("radio", { name: "JEE" })).not.toBeInTheDocument();
  });

  it("asks for a stream only in Class 11 – 12, and suggests that stream's subjects", async () => {
    const { user } = renderForm();
    await user.click(radio("Class 7"));
    expect(screen.queryByRole("group", { name: "Stream" })).not.toBeInTheDocument();

    await user.click(radio("Class 11"));
    expect(screen.getByRole("group", { name: "Stream" })).toBeInTheDocument();
    expect(radio("JEE")).toBeInTheDocument();

    await user.click(radio("Science"));
    expect(screen.getByRole("checkbox", { name: "Physics" })).toBeInTheDocument();

    await user.click(radio("Class 7"));
    expect(screen.queryByRole("group", { name: "Stream" })).not.toBeInTheDocument();
  });

  it("moves the goal to the new class's default when the class changes", async () => {
    const { user } = renderForm();
    await user.click(radio("Class 11"));
    await user.click(radio("JEE"));
    await user.click(radio("Class 7"));
    expect(radio("School exams")).toBeChecked();
  });

  it("asks for the board's name only for a state or other board", async () => {
    const { user } = renderForm();
    await user.click(radio("Class 7"));
    expect(screen.queryByLabelText("Name of the board")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Board"), "state");
    expect(screen.getByLabelText("Name of the board")).toBeInTheDocument();
  });

  it("keeps the browser from filling the child's and the board's names with the parent's own", async () => {
    const { user } = renderForm();
    await user.click(radio("Class 7"));
    await user.selectOptions(screen.getByLabelText("Board"), "state");
    // Not "off": Chrome ignores that and offers the parent's saved name (components/field.tsx).
    for (const label of ["Child's name", "Name of the board"]) {
      expect(screen.getByLabelText(label)).toHaveAttribute("autocomplete", "none");
    }
  });

  it("lets the parent add a subject of their own, once", async () => {
    const { user } = renderForm();
    await user.click(radio("Class 7"));
    await user.type(screen.getByLabelText("Add a subject"), "Sanskrit{Enter}");
    await user.type(screen.getByLabelText("Add a subject"), "sanskrit{Enter}");
    expect(screen.getAllByRole("checkbox", { name: "Sanskrit" })).toHaveLength(1);
    expect(screen.getByRole("checkbox", { name: "Sanskrit" })).toBeChecked();
  });

  it("starts from the learner's saved details when editing", () => {
    renderForm({
      student: {
        id: "s1",
        name: "Kabir",
        age: 17,
        has_own_login: true,
        profile: {
          class_level: "class_11",
          board: "cbse",
          board_name: null,
          medium: "en",
          primary_language: "en",
          stream: "science",
          goal: "jee",
          subjects: ["Physics"],
          class_label: "Class 11",
        },
      },
    });
    expect(radio("Class 11")).toBeChecked();
    expect(radio("Science")).toBeChecked();
    expect(radio("JEE")).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Physics" })).toBeChecked();
    expect(screen.getByLabelText("Child's name")).toHaveValue("Kabir");
  });
});
