import Link from "next/link";
import { redirect } from "next/navigation";

import { ChatBox } from "@/components/chat-box";
import { getChat, getChats } from "@/lib/api";
import { copy } from "@/lib/copy";
import type { ChatKind, Student } from "@/lib/types";

/**
 * The Parent AI Assistant or the Student AI Tutor: a conversation (a new one, or `chatId`) and the
 * earlier ones. A conversation of another child (the parent switched) is not shown here.
 */
export async function ChatScreen({
  kind,
  student,
  chatId,
  basePath,
}: {
  kind: ChatKind;
  student: Student;
  chatId?: string;
  basePath: "/parent/assistant" | "/learn/tutor";
}) {
  const [chats, chat] = await Promise.all([getChats(kind, student.id), chatId ? getChat(chatId) : null]);
  if (chat && chat.student_id !== student.id) redirect(basePath);
  const words = copy.chat[kind];

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_15rem] lg:items-start">
      <section className="grid max-w-3xl gap-4">
        <div className="grid gap-1">
          <h1 className="text-3xl font-extrabold dense:text-2xl">
            {words.title}
            {kind === "assistant" && ` · ${student.name}`}
          </h1>
          <p className="text-muted-foreground">{words.intro}</p>
        </div>
        <ChatBox key={chat?.id} kind={kind} studentId={student.id} chat={chat} basePath={basePath} />
      </section>
      <nav aria-label={copy.chat.conversations} className="grid gap-2">
        <Link
          href={basePath}
          className="rounded-lg border bg-card px-3 py-2 text-sm font-semibold hover:border-primary"
        >
          + {copy.chat.newConversation}
        </Link>
        {chats.length > 0 && (
          <>
            <h2 className="mt-2 text-sm font-semibold text-muted-foreground">{copy.chat.conversations}</h2>
            <ul className="grid gap-1">
              {chats.map((item) => (
                <li key={item.id}>
                  <Link
                    href={`${basePath}/${item.id}`}
                    aria-current={item.id === chat?.id ? "page" : undefined}
                    className="block truncate rounded-lg px-3 py-2 text-sm hover:bg-secondary aria-[current=page]:bg-secondary"
                  >
                    {item.title}
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </nav>
    </div>
  );
}
