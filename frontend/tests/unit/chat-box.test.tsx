import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatBox } from "@/components/chat-box";
import { createChat } from "@/lib/actions/chat";
import type { ChatMessage } from "@/lib/types";

import { source } from "./fixtures";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/lib/actions/chat", () => ({ createChat: vi.fn() }));

/** The backend's reply stream: Server-Sent Events. */
function stream(...events: [string, object][]) {
  const body = events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join("");
  return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
}

function message(role: ChatMessage["role"], content: string, extra: Partial<ChatMessage> = {}): ChatMessage {
  return { id: `${role}:${content}`, role, content, sources: [], rung: null, ...extra };
}

const conversation = { id: "c1", student_id: "s1", title: "x + 5 = 12", messages: [] };

beforeEach(() => {
  replace.mockReset();
  vi.mocked(createChat)
    .mockReset()
    .mockResolvedValue({
      data: { id: "c9", student_id: "s1", title: "" },
    });
});
afterEach(() => vi.unstubAllGlobals());

describe("ChatBox", () => {
  it("shows the tutor's reply as it is written, then keeps it with its rung and books", async () => {
    const answer = message("assistant", "Socho: x ke saath kya juda hai?", {
      rung: "hint_1",
      sources: [source],
    });
    const fetchMock = vi.fn(async () =>
      stream(
        ["delta", { text: "Socho: " }],
        ["delta", { text: "x ke saath kya juda hai?" }],
        ["done", { question: message("user", "x + 5 = 12?"), answer }],
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<ChatBox kind="tutor" studentId="s1" chat={conversation} basePath="/learn/tutor" />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Type your question or problem…"), "x + 5 = 12?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Socho:")).toBeInTheDocument(); // the first word, before the rest
    expect(await screen.findByText("Hint 1")).toBeInTheDocument();
    expect(screen.getByText("Socho: x ke saath kya juda hai?")).toBeInTheDocument();
    expect(screen.getByText(/Based on: Class 7 Maths → Chapter 4/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat/c1/messages",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ text: "x + 5 = 12?" }) }),
    );
    expect(createChat).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Type your question or problem…")).toHaveValue("");
  });

  it("says plainly that the AI is off, and keeps the question to send again", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ error: { code: "ai_not_configured", message: "AI off." } }, { status: 503 }),
      ),
    );
    render(<ChatBox kind="assistant" studentId="s1" chat={null} basePath="/parent/assistant" />);
    await userEvent.setup().click(screen.getByRole("button", { name: "How is my child doing this week?" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The assistant needs the AI, which is not switched on yet.",
    );
    expect(screen.getByLabelText("Ask a question…")).toHaveValue("How is my child doing this week?");
    expect(createChat).toHaveBeenCalledWith("assistant", "s1");
  });

  it("drops a reply that fails half-way, so the question can be sent again", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        stream(["delta", { text: "Equation " }], ["error", { code: "ai_unavailable", message: "Busy." }]),
      ),
    );
    render(<ChatBox kind="tutor" studentId="s1" chat={conversation} basePath="/learn/tutor" />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Type your question or problem…"), "What is an equation?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Busy.");
    expect(screen.queryByText("Equation")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Type your question or problem…")).toHaveValue("What is an equation?");
  });

  it("types out a reply that arrives all at once, word by word and without its citation tags", async () => {
    const answer = message("assistant", "Add 7 to both sides. Then x = 12.");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        stream(
          ["delta", { text: "Add 7 to both sides [S1]. " }],
          ["delta", { text: "Then x = 12." }],
          ["done", { question: message("user", "x - 7 = 5?"), answer }],
        ),
      ),
    );
    const { container } = render(
      <ChatBox kind="tutor" studentId="s1" chat={conversation} basePath="/learn/tutor" />,
    );
    const shown: string[] = [];
    new MutationObserver(() => shown.push(container.textContent ?? "")).observe(container, {
      subtree: true,
      childList: true,
      characterData: true,
    });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Type your question or problem…"), "x - 7 = 5?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Add")).toBeInTheDocument(); // one word at a time
    // Typed out, the reply is kept in the conversation.
    await vi.waitFor(() => expect(screen.getByRole("list")).toHaveAttribute("aria-busy", "false"));
    expect(screen.getByText("Add 7 to both sides. Then x = 12.")).toBeInTheDocument();
    expect(shown.some((text) => text.includes("[S1"))).toBe(false);
  });

  it("shows that the AI is thinking until the first words come", async () => {
    let reply: (response: Response) => void = () => {};
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((resolve) => (reply = resolve))),
    );
    render(<ChatBox kind="tutor" studentId="s1" chat={conversation} basePath="/learn/tutor" />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Type your question or problem…"), "What is a ratio?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Thinking…");
    const answer = message("assistant", "A ratio compares two numbers.");
    reply(
      stream(
        ["delta", { text: answer.content }],
        ["done", { question: message("user", "What is a ratio?"), answer }],
      ),
    );
    expect(await screen.findByText("A")).toBeInTheDocument(); // the first word: the dots make way
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("opens a new conversation at its own address once its first reply is typed out", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        stream(
          ["delta", { text: "Two: fractions and decimals." }],
          [
            "done",
            {
              question: message("user", "Which topics need attention?"),
              answer: message("assistant", "Two: fractions and decimals."),
            },
          ],
        ),
      ),
    );
    render(<ChatBox kind="assistant" studentId="s1" chat={null} basePath="/parent/assistant" />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Which topics need attention?" }));

    expect(await screen.findByText("Two:")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled(); // not before the reply is all on screen
    await vi.waitFor(() => expect(replace).toHaveBeenCalledWith("/parent/assistant/c9", { scroll: false }));
  });
});
