import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExitForm } from "@/app/learn/exit/exit-form";
import { PinForm } from "@/components/pin-form";
import { leaveChildMode, type PinState } from "@/lib/actions/auth";

vi.mock("@/lib/actions/auth", () => ({ leaveChildMode: vi.fn() }));

const pad = (name: string) => within(screen.getByRole("group", { name }));

async function tap(user: ReturnType<typeof userEvent.setup>, name: string, digits: string) {
  for (const digit of digits) await user.click(pad(name).getByRole("button", { name: digit }));
}

describe("the parent PIN form", () => {
  it("has nothing a browser could fill in but the password, and sends the PIN typed twice", async () => {
    const action = vi.fn<(state: PinState, formData: FormData) => Promise<PinState>>(async () => ({
      saved: true,
    }));
    const { container } = render(<PinForm action={action} submitLabel="Save PIN" />);
    const user = userEvent.setup();

    // The only field a password manager or a phone keyboard sees is the account's password.
    const fields = [...container.querySelectorAll("input")].filter((input) => input.type !== "hidden");
    expect(fields.map((input) => input.name)).toEqual(["password"]);

    await user.type(screen.getByLabelText("Your password"), "Str0ng-Passw0rd");
    await tap(user, "New PIN", "2461");
    await user.click(pad("New PIN").getByRole("button", { name: "Delete" }));
    await tap(user, "New PIN", "8");
    expect(pad("New PIN").getByText("4 of 4 digits entered")).toBeInTheDocument();
    await tap(user, "New PIN", "9"); // a fifth digit is not taken

    // The number keys work while the pad has focus.
    pad("The PIN again").getByRole("button", { name: "5" }).focus();
    await user.keyboard("2468");
    await user.click(screen.getByRole("button", { name: "Save PIN" }));

    await waitFor(() => expect(action).toHaveBeenCalledOnce());
    const sent = action.mock.calls[0][1];
    expect([sent.get("password"), sent.get("pin"), sent.get("pin_again")]).toEqual([
      "Str0ng-Passw0rd",
      "2468",
      "2468",
    ]);
    expect(await screen.findByRole("status")).toHaveTextContent("PIN saved.");
    // Sent, the pads start again.
    expect(pad("New PIN").getByText("0 of 4 digits entered")).toBeInTheDocument();
  });

  it("leaves child mode as soon as the fourth digit is in, and starts again after a wrong PIN", async () => {
    vi.mocked(leaveChildMode).mockResolvedValue({ code: "wrong_pin", message: "The PIN is not correct." });
    render(<ExitForm />);
    const user = userEvent.setup();

    await tap(user, "Parent PIN", "246");
    expect(leaveChildMode).not.toHaveBeenCalled();
    await tap(user, "Parent PIN", "8");

    await waitFor(() => expect(leaveChildMode).toHaveBeenCalledOnce());
    expect(vi.mocked(leaveChildMode).mock.calls[0][1].get("pin")).toBe("2468");
    expect(await screen.findByRole("alert")).toHaveTextContent("The PIN is not correct.");
    expect(pad("Parent PIN").getByText("0 of 4 digits entered")).toBeInTheDocument();

    // Typed again straight away, no digit is lost.
    await tap(user, "Parent PIN", "1357");
    await waitFor(() => expect(leaveChildMode).toHaveBeenCalledTimes(2));
    expect(vi.mocked(leaveChildMode).mock.calls[1][1].get("pin")).toBe("1357");
  });
});
