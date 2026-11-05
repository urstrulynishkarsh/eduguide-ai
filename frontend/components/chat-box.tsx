"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { useCopy } from "@/components/copy-provider";
import { FormMessage } from "@/components/form-message";
import { SourceLine } from "@/components/source-line";
import { Button } from "@/components/ui/button";
import { createChat } from "@/lib/actions/chat";
import type { Refusal } from "@/lib/forms";
import { readEvents } from "@/lib/sse";
import type { Chat, ChatKind, ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

/** What the reply stream says (docs/03 §3.8). */
type ReplyEvent =
  | { event: "delta"; data: { text: string } }
  | { event: "done"; data: { question: ChatMessage; answer: ChatMessage } }
  | { event: "error"; data: { code: string; message: string } };

/**
 * A fast model writes a whole reply in a fraction of a second, which would land all at once: each
 * piece stays a moment, in step with its length, so the reply is shown at a steady reading pace. A
 * slower model's pieces come no faster than this anyway. A hidden tab is not paced: its timers wait a
 * second or more.
 */
function pace(piece: string): Promise<void> {
  if (document.hidden) return Promise.resolve();
  return new Promise((resolve) => setTimeout(resolve, piece.length * 5));
}

function Bubble({ message }: { message: Pick<ChatMessage, "role" | "content"> & Partial<ChatMessage> }) {
  const copy = useCopy();
  const text = copy.chat;
  const mine = message.role === "user";
  return (
    <li
      className={cn(
        "grid max-w-[85%] gap-2 rounded-2xl px-4 py-3",
        mine ? "justify-self-end bg-primary text-primary-foreground" : "justify-self-start border bg-card",
      )}
    >
      {message.rung && (
        <span className="justify-self-start rounded-full bg-secondary px-2 py-0.5 text-xs font-semibold text-secondary-foreground">
          {text.rungs[message.rung]}
        </span>
      )}
      <p className="whitespace-pre-line">{message.content}</p>
      {message.sources && message.sources.length > 0 && (
        <SourceLine label={copy.concepts.basedOn} sources={message.sources} />
      )}
    </li>
  );
}

/**
 * A conversation with the assistant or the tutor. The reply appears as it is written, at a steady
 * reading pace, and the question and the reply are kept once it is complete; after an error the
 * question can be sent again. A new conversation is made with its first message, then opened at its
 * own address.
 */
export function ChatBox({
  kind,
  studentId,
  chat,
  basePath,
}: {
  kind: ChatKind;
  studentId: string;
  chat: Chat | null;
  basePath: string;
}) {
  const copy = useCopy();
  const text = copy.chat;
  const router = useRouter();
  const [messages, setMessages] = useState(chat?.messages ?? []);
  const [draft, setDraft] = useState("");
  const [asking, setAsking] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [error, setError] = useState<Refusal>();
  const [, startTransition] = useTransition();
  const chatId = useRef(chat?.id);
  const end = useRef<HTMLDivElement>(null);
  const words = text[kind];

  // A block body: newer browsers return a Promise from scrollIntoView, which must not become the
  // effect's clean-up.
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "nearest" });
  }, [messages, reply]);

  async function send(question: string) {
    question = question.trim();
    if (!question || asking) return;
    setAsking(question);
    setReply("");
    setError(undefined);
    setDraft("");
    const fail = (refusal: Refusal) => {
      setError(refusal);
      setAsking(null);
      setDraft(question);
    };

    if (!chatId.current) {
      const made = await createChat(kind, studentId);
      if ("error" in made) return fail(made.error);
      chatId.current = made.data.id;
    }
    try {
      const response = await fetch(`/api/chat/${encodeURIComponent(chatId.current)}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: question }),
      });
      if (!response.ok || !response.body) {
        const refused = (await response.json().catch(() => null))?.error;
        return fail(
          refused?.code === "ai_not_configured"
            ? { message: words.aiOff }
            : { code: "internal_error", ...refused },
        );
      }
      for await (const { event, data } of readEvents(response.body) as AsyncGenerator<ReplyEvent>) {
        if (event === "delta") {
          setReply((current) => current + data.text);
          await pace(data.text);
        } else if (event === "error") return fail(data);
        else {
          if (chat) {
            setMessages((current) => [...current, data.question, data.answer]);
            setAsking(null);
          } else {
            // The new conversation opens at its own address; this page (kept for returning to)
            // starts afresh for the next new one.
            const opened = `${basePath}/${chatId.current}`;
            chatId.current = undefined;
            startTransition(() => {
              setAsking(null);
              router.replace(opened, { scroll: false });
            });
          }
          return;
        }
      }
      fail({ code: "internal_error" }); // the stream ended before the reply was complete
    } catch {
      fail({ code: "unreachable" });
    }
  }

  return (
    <div className="grid gap-4">
      {messages.length === 0 && !asking && words.suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {words.suggestions.map((suggestion) => (
            <Button key={suggestion} variant="outline" size="sm" onClick={() => send(suggestion)}>
              {suggestion}
            </Button>
          ))}
        </div>
      )}
      <ol aria-live="polite" aria-busy={Boolean(asking)} className="grid gap-3">
        {messages.map((message) => (
          <Bubble key={message.id} message={message} />
        ))}
        {asking && (
          <>
            <Bubble message={{ role: "user", content: asking }} />
            <Bubble message={{ role: "assistant", content: reply || text.thinking }} />
          </>
        )}
      </ol>
      <FormMessage error={error} />
      <form
        onSubmit={(event) => {
          event.preventDefault();
          send(draft);
        }}
        className="flex items-end gap-2"
      >
        <textarea
          aria-label={words.placeholder}
          placeholder={words.placeholder}
          value={draft}
          maxLength={2000}
          rows={2}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              send(draft);
            }
          }}
          className="min-w-0 flex-1 rounded-md border border-input bg-card px-3 py-2 shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        />
        <Button type="submit" disabled={!draft.trim() || Boolean(asking)}>
          {text.send}
        </Button>
      </form>
      <div ref={end} />
    </div>
  );
}
