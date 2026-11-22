const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.error?.message ?? body?.detail ?? "Request failed.");
  }
  return body as T;
}

export type Conversation = {
  id: string; title: string; is_pinned: boolean;
};
export type Message = { id: string; role: "user" | "assistant" | "system"; content: string; created_at?: string };
export type MemoryItem = {
  id: string;
  category?: string;
  label: string;
  text: string;
  key?: string | null;
  importance?: number;
  confidence?: number;
  confirmed?: boolean;
  is_current?: boolean;
  created_at?: string;
  updated_at?: string;
};
export type PendingMemory = { category: string; content: string; conversation_id: string };
export type Dashboard = {
  participants: string[];
  participant: string | null;
  metrics: { key: string; label: string; latest: number; average: number }[];
  chart: { label: string | null; points: { date: string; value: number }[] };
  source: string;
};

export type UserProfile = {
  id?: string;
  user_id?: string;
  full_name: string;
  age?: number | null;
  date_of_birth?: string | null;
  sex?: string;
  height?: number | null;
  current_weight?: number | null;
  unit_preference: "metric" | "imperial";
  primary_goal?: string;
  goals: string[];
  activity_level: string;
  dietary_preference: string;
  allergies?: string;
  medical_conditions?: string;
  medications?: string;
  injuries_limitations?: string;
  sleep_duration_hours?: number | null;
  sleep_quality?: string;
  lifestyle_notes?: string;
  onboarding_completed: boolean;
};

export const api = {
  me: () => request<{ user: { id: string; email: string; onboarding_completed?: boolean } }>("/api/auth/me"),
  getProfile: () => request<{ profile: UserProfile | null; onboarding_completed: boolean }>("/api/profile"),
  completeOnboarding: (data: Partial<UserProfile>) =>
    request<{ ok: boolean; profile: UserProfile }>("/api/profile/onboarding", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateProfile: (data: Partial<UserProfile>) =>
    request<{ ok: boolean; profile: UserProfile }>("/api/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  login: (email: string, password: string) => request("/api/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  }),
  register: (email: string, password: string, display_name: string) => request<{ status?: string; message?: string }>("/api/auth/register", {
    method: "POST", body: JSON.stringify({ email, password, display_name }),
  }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  conversations: () => request<Conversation[]>("/api/conversations"),
  createConversation: () => request<Conversation>("/api/conversations", {
    method: "POST", body: JSON.stringify({}),
  }),
  conversation: (id: string) => request<{ conversation: Conversation; messages: Message[] }>(`/api/conversations/${id}`),
  updateConversation: (id: string, body: { title?: string; is_pinned?: boolean }) =>
    request<Conversation>(`/api/conversations/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteConversation: (id: string) => request(`/api/conversations/${id}`, { method: "DELETE" }),
  sendMessage: (id: string, content: string) =>
    request<{
      assistant_message: string;
      pending_memories: PendingMemory[];
      conversation_title?: string;
      conversation_id?: string;
    }>(`/api/conversations/${id}/messages`, {
      method: "POST", body: JSON.stringify({ content }),
    }),
  memory: (category?: string, search?: string, include_history = true) => {
    const params = new URLSearchParams();
    if (category && category !== "all") params.set("category", category);
    if (search) params.set("search", search);
    if (include_history) params.set("include_history", "true");
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<MemoryItem[]>(`/api/memory${qs}`);
  },
  saveMemory: (content: string, memory_type = "preference", importance = 0.7) => request("/api/memory", {
    method: "POST", body: JSON.stringify({ content, memory_type, importance }),
  }),
  confirmMemory: (content: string, conversation_id: string, memory_type = "health") => request("/api/memory/confirm", {
    method: "POST", body: JSON.stringify({ content, conversation_id, memory_type }),
  }),
  updateMemory: (id: string, content: string) => request(`/api/memory/${id}`, {
    method: "PATCH", body: JSON.stringify({ content }),
  }),
  deleteMemory: (id: string) => request(`/api/memory/${id}`, { method: "DELETE" }),
  clearMemory: () => request("/api/memory", { method: "DELETE" }),
  dashboard: (participant?: string) =>
    request<Dashboard>(`/api/dashboard${participant ? `?participant=${encodeURIComponent(participant)}` : ""}`),
};
