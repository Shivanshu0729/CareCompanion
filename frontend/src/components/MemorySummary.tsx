import { useState } from "react";
import { api, type MemoryItem } from "../lib/api";

const CATEGORIES = [
  { id: "all", label: "All Memories" },
  { id: "health", label: "Health" },
  { id: "profile", label: "Profile" },
  { id: "goal", label: "Goals" },
  { id: "context", label: "Projects" },
  { id: "progress", label: "Progress" },
  { id: "preference", label: "Preferences" },
];

const CATEGORY_COLORS: Record<string, string> = {
  health: "bg-rose-100 text-rose-800 border-rose-200",
  profile: "bg-blue-100 text-blue-800 border-blue-200",
  goal: "bg-emerald-100 text-emerald-800 border-emerald-200",
  context: "bg-purple-100 text-purple-800 border-purple-200",
  progress: "bg-amber-100 text-amber-800 border-amber-200",
  preference: "bg-indigo-100 text-indigo-800 border-indigo-200",
  setting: "bg-gray-100 text-gray-700 border-gray-200",
  historical: "bg-gray-100 text-gray-500 border-gray-300",
};

export default function MemorySummary({
  items,
  onRefresh,
}: {
  items: MemoryItem[];
  onRefresh: () => Promise<void>;
}) {
  const [activeCategory, setActiveCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newText, setNewText] = useState("");
  const [newCategory, setNewCategory] = useState("health");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const filteredItems = items.filter((item) => {
    const isCurrent = item.is_current !== false;
    if (!showHistory && !isCurrent) return false;

    const cat = (item.category || item.label || "preference").toLowerCase();
    const matchesCategory =
      activeCategory === "all" ||
      (activeCategory === "context" && (cat === "context" || cat === "project")) ||
      cat === activeCategory;
    const matchesSearch =
      !search.trim() ||
      item.text.toLowerCase().includes(search.toLowerCase()) ||
      (item.key && item.key.toLowerCase().includes(search.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newText.trim()) return;
    await api.saveMemory(newText.trim(), newCategory);
    setNewText("");
    setIsAdding(false);
    await onRefresh();
  };

  const handleSaveEdit = async (id: string) => {
    if (!editText.trim()) return;
    await api.updateMemory(id, editText.trim());
    setEditingId(null);
    await onRefresh();
  };

  return (
    <details className="rounded-xl border border-line bg-paper shadow-soft transition-all" open>
      <summary className="flex cursor-pointer select-none items-center justify-between px-5 py-4 text-base font-semibold text-ink">
        <span className="flex items-center gap-2">
          <span>🧠</span> What CareCompanion Remembers ({items.length})
        </span>
        <span className="text-xs font-normal text-quiet">Click to toggle</span>
      </summary>

      <div className="border-t border-line px-5 py-4">
        {/* Category Tabs & Search Bar */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-1">
            {CATEGORIES.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveCategory(tab.id)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                  activeCategory === tab.id
                    ? "bg-ink text-white"
                    : "bg-white/80 text-quiet hover:bg-white hover:text-ink"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-quiet cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showHistory}
                onChange={(e) => setShowHistory(e.target.checked)}
                className="rounded border-line text-ink"
              />
              Show history
            </label>
            <input
              type="text"
              placeholder="Search memories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-line bg-white px-3 py-1 text-xs text-ink outline-none sm:w-36 focus:border-dusk"
            />
            <button
              onClick={() => setIsAdding(!isAdding)}
              className="rounded-lg bg-[#E7D3A8] px-2.5 py-1 text-xs font-medium text-ink hover:bg-[#D9B777]"
            >
              + Add
            </button>
          </div>
        </div>

        {/* Add Memory Form */}
        {isAdding && (
          <form onSubmit={handleAdd} className="mt-3 rounded-lg border border-line bg-white p-3">
            <p className="text-xs font-medium text-ink">Add a new memory manually</p>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="rounded border border-line bg-white px-2 py-1 text-xs outline-none focus:border-dusk"
              >
                <option value="profile">Profile</option>
                <option value="goal">Goal</option>
                <option value="context">Project / Context</option>
                <option value="progress">Progress</option>
                <option value="preference">Preference</option>
                <option value="health">Health & Limitations</option>
              </select>
              <input
                type="text"
                required
                placeholder="e.g. Currently building an AI app using FastAPI"
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                className="flex-1 rounded border border-line px-2.5 py-1 text-xs outline-none focus:border-dusk"
              />
              <div className="flex gap-1.5">
                <button type="submit" className="rounded bg-ink px-3 py-1 text-xs font-medium text-white">
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setIsAdding(false)}
                  className="rounded border border-line px-2 py-1 text-xs text-quiet"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        )}

        {/* Memory Items List */}
        <div className="mt-4 divide-y divide-line/60">
          {filteredItems.length === 0 ? (
            <p className="py-4 text-center text-xs text-quiet">
              {search ? "No memories match your search." : "No memories saved in this category yet."}
            </p>
          ) : (
            filteredItems.map((item) => {
              const catKey = (item.category || item.label || "preference").toLowerCase();
              const isPast = item.is_current === false;
              const badgeStyle = isPast
                ? CATEGORY_COLORS.historical
                : (CATEGORY_COLORS[catKey] || CATEGORY_COLORS.preference);
              const isGoal = item.id.startsWith("goal:");
              const isSummary = item.id.startsWith("summary:");

              return (
                <div key={item.id} className={`group flex flex-col justify-between py-2.5 sm:flex-row sm:items-start sm:gap-4 ${isPast ? "opacity-60" : ""}`}>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`inline-block rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${badgeStyle}`}>
                        {item.label || item.category || "Memory"}
                      </span>
                      {isPast && (
                        <span className="rounded border border-gray-300 bg-gray-100 px-1.5 py-0.5 text-[9px] font-medium text-gray-600">
                          Past / Superseded
                        </span>
                      )}
                      {item.updated_at && (
                        <span className="text-[10px] text-quiet">
                          {new Date(item.updated_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                          })}
                        </span>
                      )}
                    </div>

                    {editingId === item.id ? (
                      <div className="mt-2 flex gap-2">
                        <input
                          type="text"
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          className="flex-1 rounded border border-line px-2 py-1 text-xs outline-none focus:border-dusk"
                        />
                        <button
                          onClick={() => handleSaveEdit(item.id)}
                          className="rounded bg-ink px-2.5 py-1 text-xs text-white"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="rounded border border-line px-2 py-1 text-xs text-quiet"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <p className="mt-1 text-xs text-ink leading-relaxed">{item.text}</p>
                    )}
                  </div>

                  {!isGoal && !isSummary && editingId !== item.id && (
                    <div className="mt-1 flex items-center gap-2.5 opacity-90 sm:mt-0 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                      <button
                        className="text-[11px] text-dusk hover:underline"
                        onClick={() => {
                          setEditingId(item.id);
                          setEditText(item.text);
                        }}
                      >
                        Edit
                      </button>
                      <button
                        className="text-[11px] text-[#9F4338] hover:underline"
                        onClick={async () => {
                          if (window.confirm("Delete this memory?")) {
                            await api.deleteMemory(item.id);
                            await onRefresh();
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Clear All Footer */}
        {items.length > 0 && (
          <div className="mt-4 flex justify-between border-t border-line/60 pt-3 text-[11px]">
            <span className="text-quiet">Memories persist automatically across conversations.</span>
            <button
              onClick={async () => {
                if (window.confirm("Clear all saved memories? This cannot be undone.")) {
                  await api.clearMemory();
                  await onRefresh();
                }
              }}
              className="text-[#9F4338] hover:underline"
            >
              Clear all memories
            </button>
          </div>
        )}
      </div>
    </details>
  );
}
