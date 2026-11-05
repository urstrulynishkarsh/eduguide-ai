"use client";

import { useRouter } from "next/navigation";
import { useEffect, useEffectEvent, useRef, useState, useTransition } from "react";

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

type Kept = { question: ChatMessage; answer: ChatMessage };

// A citation as models write it: "[S1]", "[S1, S2]", "(see [S2])". The books are listed under the reply
// instead, as in the reply that is kept (the backend's chat_service.citations()).
const TAGS = String.raw`\[S\d+(?:\s*,\s*S\d+)*\](?:\s*\[S\d+(?:\s*,\s*S\d+)*\])*`;
const CITATION = new RegExp(String.raw`\s*\((?:see\s+)?${TAGS}\)|\s*${TAGS}`, "gi");

const WORD_MS = 30; // a word every 30 ms: the pace a chat model types at
const CATCH_UP = 40; // further behind than this many words, several are shown at a time

/** Where `count` more words end after `from` (each word with the spaces after it), at most at `limit`. */
function afterWords(text: string, from: number, count: number, limit: number): number {
  const word = /\S+\s*/g;
  word.lastIndex = from;
  let end = from;
  for (let i = 0; i < count && word.exec(text); i++) end = word.lastIndex;
  return Math.min(end, limit);
}

/**
 * The part of a reply shown so far: word by word at a steady pace, however it arrives - a fast model
 * sends a whole reply in a fraction of a second, a busy one in bursts. Far behind, several words come
 * at a time, so a long reply never trails much behind. Until the reply is complete only whole words
 * show, so a citation is whole (and taken out) before it could.
 */
function useTyped(text: string, complete: boolean): string {
  const [end, setEnd] = useState(0);
  const target = complete ? text.length : text.search(/\S*$/);
  useEffect(() => {
    if (end >= target) return;
    const timer = setTimeout(() => {
      const behind = text.slice(end, target).match(/\S+/g)?.length ?? 1;
      const next = afterWords(text, end, Math.ceil(behind / CATCH_UP), target);
      setEnd(next > end ? next : target); // only spaces left: all of it
    }, WORD_MS);
    return () => clearTimeout(timer);
  }, [text, end, target]);
  return text.slice(0, Math.min(end, target));
}

/** Keeps the end of the conversation in view. (A block body: newer browsers return a Promise from
 * scrollIntoView, which must not become an effect's clean-up.) */
function bringIntoView(element: HTMLElement | null) {
  element?.scrollIntoView?.({ block: "nearest" });
}

const bubble = "grid max-w-[85%] gap-2 rounded-2xl px-4 py-3";

function Bubble({ message }: { message: Pick<ChatMessage, "role" | "content"> & Partial<ChatMessage> }) {
  const copy = useCopy();
  const text = copy.chat;
  const mine = message.role === "user";
  return (
    <li
      className={cn(
        bubble,
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
 * The reply being written: dots while the AI thinks, then its words as they are typed, with a cursor,
 * the conversation's `end` kept in view. `onTyped` once it is complete and all of it is shown.
 */
function Reply({
  text,
  complete,
  end,
  onTyped,
}: {
  text: string;
  complete: boolean;
  end: React.RefObject<HTMLDivElement | null>;
  onTyped: () => void;
}) {
  const copy = useCopy();
  const shown = useTyped(text, complete);
  const typing = !complete || shown.length < text.length;
  const typed = useEffectEvent(onTyped);
  useEffect(() => {
    bringIntoView(end.current);
  }, [shown, end]);
  useEffect(() => {
    if (!typing) typed();
  }, [typing]);
  return (
    <li className={cn(bubble, "justify-self-start border bg-card")}>
      {shown ? (
        <p className="whitespace-pre-line">
          {shown}
          {typing && (
            <span
              aria-hidden
              className="ml-1 inline-block size-2.5 rounded-full bg-foreground align-middle motion-safe:animate-pulse"
            />
          )}
        </p>
      ) : (
        <p role="status" className="flex h-6 items-center gap-1">
          <span className="sr-only">{copy.chat.thinking}</span>
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              aria-hidden
              className="size-2 rounded-full bg-muted-foreground/60 motion-safe:animate-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </p>
      )}
    </li>
  );
}

/**
 * A conversation with the assistant or the tutor, shown as ChatGPT or Claude show one: the reply is
 * typed out as it is written (dots while the AI thinks), and the question and the reply are kept once
 * it is complete; after an error the question can be sent again. A new conversation is made with its
 * first message, then opened at its own address.
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
  const [kept, setKept] = useState<Kept | null>(null); // the reply is complete; typed out, it is kept
  const [turn, setTurn] = useState(0); // a fresh reply for each question
  const [error, setError] = useState<Refusal>();
  const [, startTransition] = useTransition();
  const chatId = useRef(chat?.id);
  const end = useRef<HTMLDivElement>(null);
  const words = text[kind];
  const shownReply = reply.replace(CITATION, "").trimStart();

  useEffect(() => {
    bringIntoView(end.current);
  }, [messages]);

  async function send(question: string) {
    question = question.trim();
    if (!question || asking) return;
    setAsking(question);
    setReply("");
    setKept(null);
    setTurn((current) => current + 1);
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
        if (event === "delta") setReply((current) => current + data.text);
        else if (event === "error") return fail(data);
        else return setKept(data);
      }
      fail({ code: "internal_error" }); // the stream ended before the reply was complete
    } catch {
      fail({ code: "unreachable" });
    }
  }

  /**
   * The complete reply is typed out: it joins the conversation. A new conversation then opens at its
   * own address, and this page, which Next.js keeps to come back to, starts afresh for the next one.
   */
  function keep() {
    if (!kept) return;
    if (chat) {
      setMessages((current) => [...current, kept.question, kept.answer]);
      setAsking(null);
      setKept(null);
      return;
    }
    const opened = `${basePath}/${chatId.current}`;
    chatId.current = undefined;
    startTransition(() => {
      setAsking(null);
      setKept(null);
      router.replace(opened, { scroll: false });
    });
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
            <Reply key={turn} text={shownReply} complete={kept !== null} end={end} onTyped={keep} />
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
