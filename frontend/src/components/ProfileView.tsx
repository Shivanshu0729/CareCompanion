import { useState } from "react";
import { api, type UserProfile } from "../lib/api";

interface ProfileViewProps {
  profile: UserProfile;
  onUpdate: (updated: UserProfile) => void;
  onBackToChat: () => void;
}

const GOAL_OPTIONS = [
  "Weight management",
  "Muscle building",
  "Improving fitness",
  "Better sleep",
  "Improving daily activity",
  "Nutrition improvement",
  "Stress management",
  "General wellness",
];

const ACTIVITY_LABELS: Record<string, string> = {
  sedentary: "Sedentary (Desk job, minimal exercise)",
  lightly_active: "Lightly Active (1-3 days/week)",
  moderately_active: "Moderately Active (3-5 days/week)",
  very_active: "Very Active (6-7 days/week, athletic/physical)",
};

const DIET_LABELS: Record<string, string> = {
  any: "No Restrictions",
  non_vegetarian: "Non-Vegetarian",
  vegetarian: "Vegetarian",
  vegan: "Vegan",
  pescatarian: "Pescatarian",
  keto: "Keto / Low-Carb",
};

export default function ProfileView({ profile, onUpdate, onBackToChat }: ProfileViewProps) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [formData, setFormData] = useState<UserProfile>({ ...profile });

  const calculateBMI = (weight?: number | null, height?: number | null): { value: string; label: string } | null => {
    if (!weight || !height || height <= 0) return null;
    // Assuming metric: weight in kg, height in cm
    const heightInMeters = height / 100;
    const bmi = weight / (heightInMeters * heightInMeters);
    let label = "Normal weight";
    if (bmi < 18.5) label = "Underweight";
    else if (bmi >= 25 && bmi < 30) label = "Overweight";
    else if (bmi >= 30) label = "Obese";
    return { value: bmi.toFixed(1), label };
  };

  const bmi = calculateBMI(profile.current_weight, profile.height);

  const toggleGoal = (goal: string) => {
    setFormData((prev) => ({
      ...prev,
      goals: prev.goals.includes(goal)
        ? prev.goals.filter((g) => g !== goal)
        : [...prev.goals, goal],
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");

    if (!formData.full_name?.trim()) {
      setError("Name is required.");
      setBusy(false);
      return;
    }

    try {
      const res = await api.updateProfile(formData);
      onUpdate(res.profile);
      setEditing(false);
      setSuccess("Profile updated successfully! New metrics have been synced with memory.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-line pb-6">
        <div>
          <div className="flex items-center gap-3">
            <button
              onClick={onBackToChat}
              className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-medium text-quiet hover:bg-slate-50 transition"
            >
              ← Back to Chat
            </button>
            <span className="text-xs uppercase tracking-widest text-dusk font-semibold">Account Profile</span>
          </div>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Personal Health Profile</h1>
          <p className="mt-1 text-sm text-quiet">
            Strict single-user account data. Your health coach exclusively personalizes guidance to this verified profile.
          </p>
        </div>
        {!editing && (
          <button
            onClick={() => {
              setFormData({ ...profile });
              setEditing(true);
            }}
            className="self-start rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#263D59]"
          >
            Edit Profile
          </button>
        )}
      </div>

      {success && (
        <div className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800 border border-emerald-200">
          {success}
        </div>
      )}
      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-800 border border-red-200">
          {error}
        </div>
      )}

      {/* Main Profile Cards or Edit Form */}
      {!editing ? (
        <div className="space-y-6">
          {/* Key Vitals Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-line bg-paper p-5 shadow-soft">
              <p className="text-xs font-semibold uppercase tracking-wider text-quiet">Name & Age</p>
              <h3 className="mt-2 text-xl font-bold text-ink">{profile.full_name}</h3>
              <p className="mt-1 text-sm text-quiet">
                {profile.age ? `${profile.age} years old` : "Age not set"} • {profile.sex?.replace("_", " ") ?? "unspecified"}
              </p>
            </div>

            <div className="rounded-2xl border border-line bg-paper p-5 shadow-soft">
              <p className="text-xs font-semibold uppercase tracking-wider text-quiet">Current Weight</p>
              <h3 className="mt-2 text-2xl font-bold text-ink">
                {profile.current_weight ? `${profile.current_weight} ${profile.unit_preference === "imperial" ? "lbs" : "kg"}` : "Not set"}
              </h3>
              <p className="mt-1 text-xs text-dusk">Baseline for nutrition & calories</p>
            </div>

            <div className="rounded-2xl border border-line bg-paper p-5 shadow-soft">
              <p className="text-xs font-semibold uppercase tracking-wider text-quiet">Height & BMI</p>
              <h3 className="mt-2 text-2xl font-bold text-ink">
                {profile.height ? `${profile.height} ${profile.unit_preference === "imperial" ? "in" : "cm"}` : "Not set"}
              </h3>
              <p className="mt-1 text-xs text-quiet">
                {bmi ? `BMI: ${bmi.value} (${bmi.label})` : "Height required for BMI"}
              </p>
            </div>

            <div className="rounded-2xl border border-line bg-paper p-5 shadow-soft">
              <p className="text-xs font-semibold uppercase tracking-wider text-quiet">Sleep Target</p>
              <h3 className="mt-2 text-2xl font-bold text-ink">
                {profile.sleep_duration_hours ? `${profile.sleep_duration_hours} hrs` : "Not set"}
              </h3>
              <p className="mt-1 text-xs text-quiet">Quality: {profile.sleep_quality ?? "Average"}</p>
            </div>
          </div>

          {/* Goals & Lifestyle */}
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-line bg-paper p-6 shadow-soft">
              <h3 className="text-base font-semibold text-ink">Active Goals</h3>
              <p className="mt-1 text-xs text-quiet">The objectives CareCompanion helps you prioritize.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {profile.goals && profile.goals.length > 0 ? (
                  profile.goals.map((g) => (
                    <span
                      key={g}
                      className="rounded-full bg-[#142033] px-3.5 py-1 text-xs font-medium text-white"
                    >
                      ✓ {g}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-quiet italic">No specific goals chosen yet.</p>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-line bg-paper p-6 shadow-soft">
              <h3 className="text-base font-semibold text-ink">Activity & Routine</h3>
              <p className="mt-1 text-xs text-quiet">Activity habits and dietary framework.</p>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between border-b border-line pb-2">
                  <span className="text-quiet">Activity Level:</span>
                  <span className="font-medium text-ink">
                    {ACTIVITY_LABELS[profile.activity_level] || profile.activity_level}
                  </span>
                </div>
                <div className="flex justify-between border-b border-line pb-2">
                  <span className="text-quiet">Dietary Preference:</span>
                  <span className="font-medium text-ink">
                    {DIET_LABELS[profile.dietary_preference] || profile.dietary_preference}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-quiet">Preferred Unit System:</span>
                  <span className="font-medium capitalize text-ink">{profile.unit_preference}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Medical & Health Notes */}
          <div className="rounded-2xl border border-line bg-paper p-6 shadow-soft">
            <h3 className="text-base font-semibold text-ink">Health, Allergies & Safety Notes</h3>
            <p className="mt-1 text-xs text-quiet">
              CareCompanion references these items to prevent unsafe workout or nutrition recommendations.
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-line bg-white p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-quiet">Allergies & Intolerances</span>
                <p className="mt-1 text-sm text-ink">{profile.allergies || "None reported."}</p>
              </div>
              <div className="rounded-xl border border-line bg-white p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-quiet">Medical Conditions</span>
                <p className="mt-1 text-sm text-ink">{profile.medical_conditions || "None reported."}</p>
              </div>
              <div className="rounded-xl border border-line bg-white p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-quiet">Current Medications</span>
                <p className="mt-1 text-sm text-ink">{profile.medications || "None."}</p>
              </div>
              <div className="rounded-xl border border-line bg-white p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-quiet">Injuries & Limitations</span>
                <p className="mt-1 text-sm text-ink">{profile.injuries_limitations || "None reported."}</p>
              </div>
            </div>
            {profile.lifestyle_notes && (
              <div className="mt-4 rounded-xl border border-line bg-white p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-quiet">General Lifestyle Notes</span>
                <p className="mt-1 text-sm text-ink">{profile.lifestyle_notes}</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Edit Form */
        <form onSubmit={handleSave} className="space-y-6 rounded-2xl border border-line bg-paper p-8 shadow-soft">
          <div className="flex items-center justify-between border-b border-line pb-4">
            <h2 className="text-xl font-semibold text-ink">Update Health Profile</h2>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="text-xs font-medium text-quiet hover:text-ink"
            >
              Cancel
            </button>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Full Name</label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Age</label>
              <input
                type="number"
                min={12}
                max={120}
                value={formData.age ?? ""}
                onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) || null })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">
                Current Weight ({formData.unit_preference === "imperial" ? "lbs" : "kg"})
              </label>
              <input
                type="number"
                step="0.1"
                min={20}
                max={400}
                value={formData.current_weight ?? ""}
                onChange={(e) => setFormData({ ...formData, current_weight: Number(e.target.value) || null })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
              <span className="text-[11px] text-quiet">
                Updating weight here automatically updates your current health memory.
              </span>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">
                Height ({formData.unit_preference === "imperial" ? "inches" : "cm"})
              </label>
              <input
                type="number"
                min={40}
                max={260}
                value={formData.height ?? ""}
                onChange={(e) => setFormData({ ...formData, height: Number(e.target.value) || null })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Sex</label>
              <select
                value={formData.sex ?? "prefer_not_to_say"}
                onChange={(e) => setFormData({ ...formData, sex: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              >
                <option value="prefer_not_to_say">Prefer not to say</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Units</label>
              <select
                value={formData.unit_preference}
                onChange={(e) => setFormData({ ...formData, unit_preference: e.target.value as any })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              >
                <option value="metric">Metric (kg, cm)</option>
                <option value="imperial">Imperial (lbs, in)</option>
              </select>
            </div>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Activity Level</label>
              <select
                value={formData.activity_level}
                onChange={(e) => setFormData({ ...formData, activity_level: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              >
                <option value="sedentary">Sedentary (desk job, minimal exercise)</option>
                <option value="lightly_active">Lightly active (1-3 days/week)</option>
                <option value="moderately_active">Moderately active (3-5 days/week)</option>
                <option value="very_active">Very active (6-7 days/week, heavy)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Dietary Preference</label>
              <select
                value={formData.dietary_preference}
                onChange={(e) => setFormData({ ...formData, dietary_preference: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              >
                <option value="any">No Restrictions</option>
                <option value="non_vegetarian">Non-Vegetarian</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="pescatarian">Pescatarian</option>
                <option value="keto">Keto / Low-Carb</option>
              </select>
            </div>
          </div>

          {/* Goals Selector */}
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-quiet mb-2">Goals</label>
            <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-4">
              {GOAL_OPTIONS.map((goal) => {
                const selected = formData.goals.includes(goal);
                return (
                  <button
                    type="button"
                    key={goal}
                    onClick={() => toggleGoal(goal)}
                    className={`rounded-lg border p-2.5 text-xs text-left transition ${
                      selected
                        ? "border-[#142033] bg-[#142033] font-medium text-white"
                        : "border-line bg-white text-ink hover:border-dusk"
                    }`}
                  >
                    {selected ? "✓ " : "+ "}
                    {goal}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Medical fields */}
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Allergies</label>
              <input
                type="text"
                placeholder="e.g. Peanuts, Dairy, Gluten"
                value={formData.allergies ?? ""}
                onChange={(e) => setFormData({ ...formData, allergies: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Medical Conditions</label>
              <input
                type="text"
                placeholder="e.g. Hypertension, Asthma"
                value={formData.medical_conditions ?? ""}
                onChange={(e) => setFormData({ ...formData, medical_conditions: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Medications</label>
              <input
                type="text"
                placeholder="e.g. Metformin 500mg"
                value={formData.medications ?? ""}
                onChange={(e) => setFormData({ ...formData, medications: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-quiet">Injuries & Limitations</label>
              <input
                type="text"
                placeholder="e.g. Lower back pain, knee meniscus"
                value={formData.injuries_limitations ?? ""}
                onChange={(e) => setFormData({ ...formData, injuries_limitations: e.target.value })}
                className="mt-1.5 w-full rounded-lg border border-line bg-white p-3 text-sm text-ink outline-none focus:border-dusk"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-line">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-lg px-4 py-2.5 text-sm text-quiet hover:bg-slate-100 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-ink px-6 py-2.5 text-sm font-medium text-white transition hover:bg-[#263D59] disabled:opacity-50"
            >
              {busy ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
