import { useEffect, useState } from "react";
import { api, type Conversation, type Dashboard, type Message, type MemoryItem, type PendingMemory } from "./lib/api";
import ChatComposer from "./components/ChatComposer";
import ChatMessage from "./components/ChatMessage";
import ConversationRow from "./components/ConversationRow";
import MemorySummary from "./components/MemorySummary";
import TrendChart from "./components/TrendChart";

export default function App() {
  const [user, setUser] = useState<{ id: string; email: string } | null>(null);
  const [login, setLogin] = useState({ displayName: "", email: "", password: "", confirmPassword: "" });
  const [authMode, setAuthMode] = useState<"signin" | "register">("signin");
  const [authNotice, setAuthNotice] = useState("");
  const [namePrompt, setNamePrompt] = useState(false);
  const [preferredName, setPreferredName] = useState("");
  const [pendingMemories, setPendingMemories] = useState<PendingMemory[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [memory, setMemory] = useState<MemoryItem[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [page, setPage] = useState<"chat" | "dashboard">("chat");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const current = await api.me();
      setUser(current.user);
      const list = await api.conversations();
      setConversations(list);
      const first = list[0] ?? await api.createConversation();
      if (!list.length) setConversations([first]);
      setActive(first.id);
      setMessages((await api.conversation(first.id)).messages);
      const savedMemory = await api.memory();
      setMemory(savedMemory);
      setNamePrompt(!savedMemory.some((item) => item.text.toLowerCase().includes("call me") || item.label.toLowerCase() === "name"));
    } catch { setUser(null); }
  };
  useEffect(() => { void load(); }, []);
  useEffect(() => { if (page === "dashboard") void api.dashboard().then(setDashboard).catch((e) => setError(e.message)); }, [page]);

  if (!user) return <main className="grid min-h-screen place-items-center bg-[#EDE7DA] p-5 md:p-10">
    <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl bg-[#142033] shadow-2xl md:grid-cols-[0.9fr_1.1fr]">
      <section className="relative hidden min-h-[620px] flex-col justify-between overflow-hidden p-10 text-white md:flex">
        <div className="orb -right-20 top-28 h-64 w-64 bg-[#D9B777]/80"></div><div className="orb -bottom-16 right-20 h-48 w-48 bg-[#58789A]/80"></div><div className="orb bottom-32 left-8 h-20 w-20 bg-[#7C9272]/80"></div>
        <div className="relative z-10"><div className="mb-16 flex items-center gap-3 text-lg font-semibold"><span className="grid h-9 w-9 place-items-center rounded-full bg-ochre text-ink">C</span>CareCompanion</div><p className="mb-4 text-sm uppercase tracking-[0.22em] text-[#D9B777]">A steadier everyday</p><h1 className="max-w-sm text-5xl leading-tight text-white">Small steps. A healthier rhythm.</h1><p className="mt-5 max-w-sm leading-7 text-white/65">A private space to reflect on your routines and build practical habits with a coach that remembers your journey.</p></div>
        <p className="text-sm text-white/45">Wellness coaching, not medical diagnosis.</p>
      </section>
      <section className="bg-[#FBF8F1] p-7 sm:p-12">
        <div className="mb-10 md:hidden"><p className="text-sm font-semibold text-dusk">CareCompanion</p></div>
        <p className="text-sm uppercase tracking-[0.18em] text-dusk">{authMode === "signin" ? "Welcome back" : "Get started"}</p>
        <h1 className="mt-2 text-4xl">{authMode === "signin" ? "Sign in to your space" : "Create your account"}</h1>
        <p className="mt-3 max-w-md text-quiet">{authMode === "signin" ? "Continue your wellness conversations where you left off." : "Save your goals and return to your coaching journey anytime."}</p>
        <form className="mt-8" onSubmit={async (event) => { event.preventDefault(); setError(""); setAuthNotice(""); if (authMode === "register" && login.password !== login.confirmPassword) { setError("Passwords do not match."); return; } try { if (authMode === "signin") { await api.login(login.email, login.password); await load(); } else { const result = await api.register(login.email, login.password, login.displayName); if (result.status === "email_confirmation_required") { setAuthNotice(result.message ?? "Check your email to confirm your account, then sign in."); setAuthMode("signin"); } else { await load(); } } } catch (e) { setError(e instanceof Error ? e.message : "Unable to continue."); } }}>
          {authMode === "register" && <><label className="mb-2 block text-sm font-medium text-ink" htmlFor="display-name">Your name</label><input id="display-name" required className="mb-5 w-full rounded-lg border border-line bg-white p-3.5 outline-none focus:border-dusk" placeholder="How should we call you?" value={login.displayName} onChange={(e) => setLogin({ ...login, displayName: e.target.value })} /></>}
          <label className="mb-2 block text-sm font-medium text-ink" htmlFor="email">Email</label>
          <input id="email" required className="mb-5 w-full rounded-lg border border-line bg-white p-3.5 outline-none focus:border-dusk" placeholder="you@example.com" type="email" value={login.email} onChange={(e) => setLogin({ ...login, email: e.target.value })} />
          <label className="mb-2 block text-sm font-medium text-ink" htmlFor="password">Password</label>
          <input id="password" required minLength={8} className="mb-6 w-full rounded-lg border border-line bg-white p-3.5 outline-none focus:border-dusk" placeholder="At least 8 characters" type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} />
          {authMode === "register" && <><label className="mb-2 block text-sm font-medium text-ink" htmlFor="confirm-password">Confirm password</label><input id="confirm-password" required minLength={8} className="mb-6 w-full rounded-lg border border-line bg-white p-3.5 outline-none focus:border-dusk" placeholder="Enter your password again" type="password" value={login.confirmPassword} onChange={(e) => setLogin({ ...login, confirmPassword: e.target.value })} /></>}
          <button className="w-full rounded-lg bg-ink px-4 py-3.5 font-medium text-white transition hover:bg-[#263D59]">{authMode === "signin" ? "Sign in" : "Create account"}</button>
        </form>
        {authNotice && <p className="mt-4 rounded-lg bg-[#E7EEF4] p-3 text-sm text-dusk">{authNotice}</p>}
        {error && <p className="mt-4 rounded-lg bg-[#F5E5E1] p-3 text-sm text-[#9F4338]">{error}</p>}
        <p className="mt-7 text-center text-sm text-quiet">{authMode === "signin" ? "New to CareCompanion?" : "Already have an account?"}{" "}<button type="button" className="font-semibold text-dusk hover:underline" onClick={() => { setError(""); setAuthMode(authMode === "signin" ? "register" : "signin"); }}>{authMode === "signin" ? "Create an account" : "Sign in"}</button></p>
      </section>
    </div>
  </main>;

  const selectConversation = async (id: string) => { setActive(id); setPage("chat"); setMessages((await api.conversation(id)).messages); };
  const refreshMemory = async () => setMemory(await api.memory());
  const send = async (text: string): Promise<boolean> => {
    if (!active) return false;
    const conversationId = active;
    const optimisticMessageId = crypto.randomUUID();
    setBusy(true);
    setError("");
    setMessages((items) => [...items, { id: optimisticMessageId, role: "user", content: text }]);
    try {
      const result = await api.sendMessage(conversationId, text);
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: "assistant", content: result.assistant_message }]);
      setPendingMemories(result.pending_memories ?? []);
      await refreshMemory();
      return true;
    } catch (e) {
      setMessages((items) => items.filter((item) => item.id !== optimisticMessageId));
      setError(e instanceof Error ? e.message : "Unable to send message.");
      return false;
    } finally {
      setBusy(false);
    }
  };
  const newChat = async () => { const item = await api.createConversation(); setConversations((items) => [item, ...items]); await selectConversation(item.id); };
  const rename = async (item: Conversation) => { const title = window.prompt("Conversation name", item.title); if (!title) return; const updated = await api.updateConversation(item.id, { title }); setConversations((items) => items.map((value) => value.id === item.id ? updated : value)); };
  const pin = async (item: Conversation) => { const updated = await api.updateConversation(item.id, { is_pinned: !item.is_pinned }); setConversations((items) => items.map((value) => value.id === item.id ? updated : value)); };
  const remove = async (item: Conversation) => { if (!window.confirm(`Delete "${item.title}"?`)) return; await api.deleteConversation(item.id); const rest = conversations.filter((value) => value.id !== item.id); setConversations(rest); if (active === item.id) { const next = rest[0] ?? await api.createConversation(); setConversations(rest.length ? rest : [next]); await selectConversation(next.id); } };

  const savePreferredName = async () => {
    const name = preferredName.trim();
    if (!name) return;
    await api.saveMemory(`Call me ${name}.`);
    setMemory(await api.memory());
    setNamePrompt(false);
  };

  const confirmPendingMemory = async (item: PendingMemory) => { await api.confirmMemory(item.content, item.conversation_id); setPendingMemories((items) => items.filter((value) => value !== item)); await refreshMemory(); };

  return <div className="flex h-screen overflow-hidden">
    <aside className="w-72 shrink-0 overflow-y-auto bg-inkdeep p-5 text-white">
      <div className="mb-8 text-xl font-semibold">CareCompanion</div>
      <button onClick={() => void newChat()} className="mb-7 w-full rounded bg-ochre px-3 py-2 text-ink">+ New chat</button>
      <p className="mb-2 text-xs uppercase tracking-widest text-white/50">Recent conversations</p>
      <ul className="space-y-1">{conversations.map((item) => <ConversationRow key={item.id} title={item.title} active={item.id === active} pinned={item.is_pinned} onSelect={() => void selectConversation(item.id)} onRename={() => void rename(item)} onPin={() => void pin(item)} onDelete={() => void remove(item)} />)}</ul>
      <div className="mt-8 border-t border-white/10 pt-4">
        <button onClick={() => setPage("dashboard")} className="w-full rounded px-3 py-2 text-left text-sm text-white/80 hover:bg-white/10">Health Dashboard</button>
        <button onClick={async () => { await api.logout(); setUser(null); }} className="mt-4 rounded px-3 py-2 text-sm text-white/60 transition-colors hover:bg-white/10 hover:text-white focus-visible:bg-white/10 focus-visible:text-white">Log out</button>
      </div>
    </aside>
    <main className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
      <div className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col overflow-y-auto p-6 md:p-10">
        {page === "dashboard" ? <><div className="mb-6 flex items-end justify-between"><div><p className="text-sm uppercase tracking-widest text-dusk">Your patterns</p><h1 className="text-4xl">Health Dashboard</h1><p className="mt-2 text-quiet">PMData research demo data, not personal measurements.</p></div><span className="rounded-full bg-[#E7D3A8] px-3 py-1 text-xs font-medium text-ink">Research view</span></div>{dashboard && <><div className="landscape mb-5 rounded-2xl shadow-lg"><span className="landscape-sun"></span><div className="absolute left-5 top-5 z-10 text-xs uppercase tracking-[0.18em] text-white/70">A view of your selected data</div><div className="absolute bottom-5 left-5 z-10 text-2xl font-semibold text-white">{dashboard.participant ?? "PMData"}</div><div className="absolute bottom-5 right-5 z-10 text-xs text-white/70">{dashboard.source}</div></div><div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{dashboard.metrics.map((metric) => <div className="rounded-xl border border-line bg-paper p-4 shadow-soft" key={metric.key}><p className="text-sm text-quiet">{metric.label}</p><strong className="mt-2 block text-2xl text-ink">{metric.latest.toFixed(1)}</strong><span className="text-xs text-quiet">Average {metric.average.toFixed(1)}</span></div>)}</div>{dashboard.chart.label && <TrendChart label={dashboard.chart.label} points={dashboard.chart.points} />}</>}</> : <><div className="mb-8 flex items-start justify-between"><div><p className="text-sm uppercase tracking-widest text-dusk">CareCompanion</p><h1 className="text-4xl">Your wellness coach</h1><p className="mt-2 max-w-xl text-quiet">A calm space to reflect, build better routines, and make progress one conversation at a time.</p></div><div className="hidden h-10 w-10 place-items-center rounded-full bg-ink text-sm font-semibold text-white sm:grid">CC        </div></div><MemorySummary items={memory} onRefresh={refreshMemory} /><div className={`${messages.length ? "flex-1" : ""} space-y-6 py-6`}>{messages.length === 0 && <div className="welcome-grid rounded-2xl border border-line bg-paper p-7"><p className="text-sm font-medium text-dusk">A fresh start</p><h2 className="mt-2 text-3xl">What would you like to work on?</h2><p className="mt-2 max-w-xl text-quiet">Choose a starting point or write your own message below. Your coach will use your conversation history when it is relevant.</p><div className="mt-6 grid gap-3 sm:grid-cols-2"><button onClick={() => void send("Help me improve my sleep routine.")} className="rounded-lg border border-line bg-white/70 p-4 text-left text-sm text-ink transition hover:border-dusk hover:bg-white">Improve my sleep routine<span className="mt-1 block text-xs text-quiet">Build a realistic evening habit</span></button><button onClick={() => void send("Help me review my activity patterns.")} className="rounded-lg border border-line bg-white/70 p-4 text-left text-sm text-ink transition hover:border-dusk hover:bg-white">Review my activity<span className="mt-1 block text-xs text-quiet">Understand my movement patterns</span></button><button onClick={() => void send("Help me create a realistic wellness goal.")} className="rounded-lg border border-line bg-white/70 p-4 text-left text-sm text-ink transition hover:border-dusk hover:bg-white">Set a wellness goal<span className="mt-1 block text-xs text-quiet">Choose one small next step</span></button><button onClick={() => void send("What is one healthy habit I can start today?")} className="rounded-lg border border-line bg-white/70 p-4 text-left text-sm text-ink transition hover:border-dusk hover:bg-white">Start today<span className="mt-1 block text-xs text-quiet">Find a simple place to begin</span></button></div></div>}{messages.map((message) => <ChatMessage key={message.id} message={message} />)}{busy && <p className="text-sm text-quiet">CareCompanion is thinking...</p>}{error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}</div></>}
      </div>
      {page === "chat" && <div className="shrink-0 border-t border-line bg-page px-6 pt-3 pb-5 md:px-10"><ChatComposer onSend={send} busy={busy} /></div>}
    </main>
    {pendingMemories.length > 0 && <div className="welcome-modal-backdrop fixed inset-0 z-40 grid place-items-center bg-[#142033]/45 p-5 backdrop-blur-sm"><div className="welcome-modal w-full max-w-lg rounded-2xl bg-[#FBF8F1] p-7 shadow-2xl"><p className="text-sm uppercase tracking-[0.18em] text-dusk">Permission to remember</p><h2 className="mt-2 text-3xl">Save this health information?</h2><p className="mt-3 leading-6 text-quiet">This is sensitive information you shared. Save it so future conversations can use it for safer, more relevant general guidance?</p><div className="my-5 rounded-lg border border-line bg-white p-4 text-sm">{pendingMemories.map((item) => <p key={item.content}>{item.content}</p>)}</div><div className="flex justify-end gap-3"><button onClick={() => setPendingMemories([])} className="rounded-lg px-4 py-2 text-sm text-quiet hover:bg-[#F0EADF]">Do not save</button><button onClick={() => void Promise.all(pendingMemories.map(confirmPendingMemory))} className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-white">Save for future chats</button></div></div></div>}
    {namePrompt && <div className="welcome-modal-backdrop fixed inset-0 z-50 grid place-items-center bg-[#142033]/45 p-5 backdrop-blur-sm"><div className="welcome-modal w-full max-w-md rounded-2xl bg-[#FBF8F1] p-7 shadow-2xl"><div className="mb-5 grid h-12 w-12 place-items-center rounded-full bg-[#E7D3A8] text-xl text-ink">C</div><p className="text-sm uppercase tracking-[0.18em] text-dusk">A quick welcome</p><h2 className="mt-2 text-3xl">What should I call you?</h2><p className="mt-2 leading-6 text-quiet">This helps make your conversations feel more personal. You can skip this and add it later.</p><input autoFocus value={preferredName} onChange={(event) => setPreferredName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void savePreferredName(); }} placeholder="Your preferred name" className="mt-6 w-full rounded-lg border border-line bg-white p-3.5 text-ink outline-none focus:border-dusk" /><div className="mt-5 flex justify-end gap-3"><button onClick={() => setNamePrompt(false)} className="rounded-lg px-4 py-2 text-sm text-quiet hover:bg-[#F0EADF]">Skip</button><button onClick={() => void savePreferredName()} disabled={!preferredName.trim()} className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40">Continue</button></div></div></div>}
  </div>;
}
