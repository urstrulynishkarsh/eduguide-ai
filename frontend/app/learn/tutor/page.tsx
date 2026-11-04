import { ChatScreen } from "@/components/chat-screen";
import { getLearner } from "@/lib/api";
import { titled } from "@/lib/copy/server";

export const generateMetadata = titled((copy) => copy.chat.tutor.title);

/** The Student AI Tutor: hint first, answer last (in the Class 6 – 12 menus). A new conversation. */
export default async function TutorPage() {
  const { student } = await getLearner();
  return <ChatScreen kind="tutor" student={student} basePath="/learn/tutor" />;
}
