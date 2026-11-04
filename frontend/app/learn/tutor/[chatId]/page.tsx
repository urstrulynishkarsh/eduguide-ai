import { ChatScreen } from "@/components/chat-screen";
import { getLearner } from "@/lib/api";
import { titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.chat.tutor.title);

export default async function TutorChatPage({ params }: PageProps<"/learn/tutor/[chatId]">) {
  const [{ chatId }, { student }] = await Promise.all([params, getLearner()]);
  return <ChatScreen kind="tutor" student={student} chatId={chatId} basePath="/learn/tutor" />;
}
