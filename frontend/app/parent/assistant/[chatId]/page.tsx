import { ChatScreen } from "@/components/chat-screen";
import { requireChosenChild } from "@/lib/api";
import { titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.chat.assistant.title);

export default async function AssistantChatPage({ params }: PageProps<"/parent/assistant/[chatId]">) {
  const [{ chatId }, child] = await Promise.all([params, requireChosenChild()]);
  return <ChatScreen kind="assistant" student={child} chatId={chatId} basePath="/parent/assistant" />;
}
