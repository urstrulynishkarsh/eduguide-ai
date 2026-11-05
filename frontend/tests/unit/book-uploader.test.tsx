import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BookUploader } from "@/components/book-uploader";
import { createBook } from "@/lib/actions/books";

import { options } from "./fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, refresh: vi.fn() }) }));
vi.mock("@/lib/actions/books", () => ({ createBook: vi.fn() }));

/** The browser's upload request to the upload route: accepted at once. */
class Upload {
  static sent: { url: string; body: FormData }[] = [];
  upload = {};
  status = 202;
  responseText = "{}";
  onload = () => {};
  private url = "";
  open(_method: string, url: string) {
    this.url = url;
  }
  send(body: FormData) {
    Upload.sent.push({ url: this.url, body });
    this.onload();
  }
}

afterEach(() => vi.unstubAllGlobals());

describe("BookUploader", () => {
  it("makes the book without its file (a Server Action takes at most 1 MB), then sends the file", async () => {
    vi.mocked(createBook).mockResolvedValue({ bookId: "b1" });
    vi.stubGlobal("XMLHttpRequest", Upload);
    render(<BookUploader newBook={{ options, learners: [], chosenId: null }} limits={options.upload} />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Book name"), "Class 7 Mathematics");
    await user.type(screen.getByLabelText("Subject"), "Mathematics");
    const book = new File(["x".repeat(2 * 1024 * 1024)], "maths.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("File"), book);
    // Submitted directly: jsdom does not see a file user-event chose, so its check of `required`
    // would stop a click on Upload.
    fireEvent.submit(screen.getByRole("button", { name: "Upload" }));

    await vi.waitFor(() => expect(push).toHaveBeenCalledWith("/parent/books/b1"));
    const fields = vi.mocked(createBook).mock.calls[0][1];
    expect(fields.get("title")).toBe("Class 7 Mathematics");
    expect(fields.has("file")).toBe(false);
    expect(Upload.sent).toEqual([{ url: "/api/books/b1/documents", body: expect.any(FormData) }]);
    expect(Upload.sent[0].body.get("file")).toBe(book);
  });
});
