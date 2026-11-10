import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../lib/api";

export default function ChatMessage({ message }: { message: Message }) {
  if (message.role === "user") {
    return <div className="flex justify-end"><p className="max-w-[34rem] whitespace-pre-wrap rounded-lg bg-[#E7EEF4] px-4 py-3 text-[15px] leading-relaxed text-ink">{message.content}</p></div>;
  }
  return <article className="border-l-2 border-sage pl-5"><div className="entry"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ table: ({ children }) => <div className="table-wrap"><table>{children}</table></div> }}>{message.content}</ReactMarkdown></div></article>;
}
