import type { Metadata } from "next";

import { ChatScreen } from "@/components/chat-screen";
import { requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.chat.assistant.title };

/** The Parent AI Assistant about the chosen child: a new conversation. */
export default async function AssistantPage() {
  return <ChatScreen kind="assistant" student={await requireChosenChild()} basePath="/parent/assistant" />;
}
