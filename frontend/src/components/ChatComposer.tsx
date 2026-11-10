import { useRef, useState } from "react";

export default function ChatComposer({ onSend, busy }: { onSend: (text: string) => Promise<boolean>; busy: boolean }) {
  const [text, setText] = useState("");
  const submitting = useRef(false);
  const submit = async () => {
    const value = text.trim();
    if (!value || busy || submitting.current) return;
    submitting.current = true;
    setText("");
    try {
      const accepted = await onSend(value);
      if (!accepted) setText(value);
    } finally {
      submitting.current = false;
    }
  };
  return <form className="mx-auto w-full max-w-[44rem] px-4 pb-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
    <div className="flex items-end gap-2 rounded-lg border border-line bg-paper p-2 shadow-soft focus-within:border-dusk">
      <textarea aria-label="Message your coach" rows={1} value={text} onChange={(event) => setText(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(); } }} placeholder="Write about sleep, activity, or your next small step" className="flex-1 resize-none bg-transparent px-2 py-2 text-[15px] text-ink outline-none" />
      <button type="submit" disabled={busy || !text.trim()} className="grid h-10 w-10 place-items-center rounded bg-ochre text-ink disabled:opacity-40" aria-label="Send message">↑</button>
    </div>
    <p className="mt-2 text-center text-xs text-quiet">Wellness coaching, not medical advice.</p>
  </form>;
}
