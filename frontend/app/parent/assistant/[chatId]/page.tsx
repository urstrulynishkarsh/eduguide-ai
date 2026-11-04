import type { Metadata } from "next";

import { ChatScreen } from "@/components/chat-screen";
import { requireChosenChild } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.chat.assistant.title };

export default async function AssistantChatPage({ params }: PageProps<"/parent/assistant/[chatId]">) {
  const [{ chatId }, child] = await Promise.all([params, requireChosenChild()]);
  return <ChatScreen kind="assistant" student={child} chatId={chatId} basePath="/parent/assistant" />;
}
