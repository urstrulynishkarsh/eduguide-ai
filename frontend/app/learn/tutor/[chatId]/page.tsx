import type { Metadata } from "next";

import { ChatScreen } from "@/components/chat-screen";
import { getLearner } from "@/lib/api";
import { copy } from "@/lib/copy";

export const metadata: Metadata = { title: copy.chat.tutor.title };

export default async function TutorChatPage({ params }: PageProps<"/learn/tutor/[chatId]">) {
  const [{ chatId }, { student }] = await Promise.all([params, getLearner()]);
  return <ChatScreen kind="tutor" student={student} chatId={chatId} basePath="/learn/tutor" />;
}
