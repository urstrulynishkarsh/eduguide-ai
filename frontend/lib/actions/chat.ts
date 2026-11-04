"use server";

import { api } from "@/lib/api";
import { attempt, type Result } from "@/lib/forms";
import type { ChatKind, ChatSummary } from "@/lib/types";

/**
 * A new conversation, made when its first message is sent. A student session always uses itself,
 * whatever `studentId` says. The reply itself streams through app/api/chat/[chatId]/messages.
 */
export async function createChat(kind: ChatKind, studentId: string): Promise<Result<ChatSummary>> {
  return attempt(() =>
    api<ChatSummary>("/chat/sessions", { method: "POST", body: { kind, student_id: studentId } }),
  );
}
