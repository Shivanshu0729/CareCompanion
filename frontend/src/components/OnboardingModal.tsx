import { useState } from "react";
import { type UserProfile } from "../lib/api";

interface OnboardingModalProps {
  initialName?: string;
  onComplete: (data: Partial<UserProfile>) => Promise<void>;
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

const ACTIVITY_OPTIONS = [
  { value: "sedentary", label: "Sedentary", desc: "Desk job, little to no regular exercise" },
  { value: "lightly_active", label: "Lightly Active", desc: "Light exercise or brisk walks 1-3 days/week" },
  { value: "moderately_active", label: "Moderately Active", desc: "Moderate exercise or workouts 3-5 days/week" },
  { value: "very_active", label: "Very Active", desc: "Heavy exercise or physical job 6-7 days/week" },
];

const DIET_OPTIONS = [
  { value: "any", label: "No Restrictions" },
  { value: "non_vegetarian", label: "Non-Vegetarian" },
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "pescatarian", label: "Pescatarian" },
  { value: "keto", label: "Keto / Low-Carb" },
];

export default function OnboardingModal({ initialName = "", onComplete }: OnboardingModalProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    full_name: initialName,
    age: 28,
    sex: "prefer_not_to_say",
    unit_preference: "metric" as "metric" | "imperial",
    height: 175,
    current_weight: 75,
    activity_level: "moderately_active",
    dietary_preference: "any",
    allergies: "",
    medical_conditions: "",
    medications: "",
    injuries_limitations: "",
    sleep_duration_hours: 7.5,
    sleep_quality: "Good",
    goals: ["Improving fitness", "Better sleep"] as string[],
    primary_goal: "",
    lifestyle_notes: "",
  });

  const toggleGoal = (goal: string) => {
    setFormData((prev) => ({
      ...prev,
      goals: prev.goals.includes(goal)
        ? prev.goals.filter((g) => g !== goal)
        : [...prev.goals, goal],
    }));
  };

  const handleNext = () => {
    setError("");
    if (step === 1) {
      if (!formData.full_name.trim()) {
        setError("Please enter your name.");
        return;
      }
      if (!formData.age || formData.age < 12 || formData.age > 115) {
        setError("Please enter a realistic age.");
        return;
      }
      if (!formData.height || formData.height < 50 || formData.height > 250) {
        setError("Please enter a valid height.");
        return;
      }
      if (!formData.current_weight || formData.current_weight < 25 || formData.current_weight > 350) {
        setError("Please enter a valid weight.");
        return;
      }
    }
    if (step === 3 && formData.goals.length === 0) {
      setError("Please select at least one wellness goal.");
      return;
    }
    setStep((prev) => (prev < 4 ? ((prev + 1) as any) : 4));
  };

  const handleSubmit = async () => {
    setBusy(true);
    setError("");
    try {
      await onComplete(formData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-fade-in">
      <div className="relative flex max-h-[92vh] w-full max-w-2xl flex-col rounded-2xl bg-white shadow-2xl overflow-hidden border border-line">
        {/* Header with Progress Steps */}
        <div className="bg-[#142033] px-8 py-6 text-white">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.2em] text-[#D9B777]">Account Setup</span>
            <span className="text-xs text-white/60">Step {step} of 4</span>
          </div>
          <h2 className="mt-1 text-2xl font-semibold">
            {step === 1 && "Personal Health Profile"}
            {step === 2 && "Health & Lifestyle Context"}
            {step === 3 && "Your Wellness Goals"}
            {step === 4 && "Review & Confirmation"}
          </h2>
          <p className="mt-1 text-xs text-white/70">
            {step === 1 && "Basic vitals help your coach calibrate realistic activity and nutrition recommendations."}
            {step === 2 && "Help CareCompanion understand your routine and any health conditions or dietary limits."}
            {step === 3 && "Select the main areas you want to improve together."}
            {step === 4 && "Verify your baseline metrics. You can update these anytime in your profile."}
          </p>

          {/* Stepper bar */}
          <div className="mt-5 grid grid-cols-4 gap-2">
            {[1, 2, 3, 4].map((s) => (
              <div
                key={s}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  s <= step ? "bg-[#D9B777]" : "bg-white/20"
                }`}
              />
            ))}
          </div>
        </div>

        {/* Body content */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {error && (
            <div className="rounded-lg bg-red-50 p-3.5 text-sm font-medium text-red-700 border border-red-200">
              {error}
            </div>
          )}

          {/* STEP 1: Basic Information */}
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-ink">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Shivanshu"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink">Age</label>
                  <input
                    type="number"
                    min="12"
                    max="115"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) })}
                    className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink">Biological Sex</label>
                  <select
                    value={formData.sex}
                    onChange={(e) => setFormData({ ...formData, sex: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink bg-white"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                    <option value="prefer_not_to_say">Prefer not to say</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between rounded-lg bg-paper p-3 border border-line">
                <span className="text-sm font-medium text-ink">Preferred Measurement Units</span>
                <div className="flex rounded-md bg-white p-1 border border-line">
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, unit_preference: "metric" })}
                    className={`px-3 py-1 text-xs font-semibold rounded ${
                      formData.unit_preference === "metric" ? "bg-ink text-white" : "text-quiet"
                    }`}
                  >
                    Metric (kg / cm)
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, unit_preference: "imperial" })}
                    className={`px-3 py-1 text-xs font-semibold rounded ${
                      formData.unit_preference === "imperial" ? "bg-ink text-white" : "text-quiet"
                    }`}
                  >
                    Imperial (lb / in)
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink">
                    Height ({formData.unit_preference === "metric" ? "cm" : "inches"})
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={formData.height}
                    onChange={(e) => setFormData({ ...formData, height: Number(e.target.value) })}
                    className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink">
                    Current Weight ({formData.unit_preference === "metric" ? "kg" : "lbs"})
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={formData.current_weight}
                    onChange={(e) => setFormData({ ...formData, current_weight: Number(e.target.value) })}
                    className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink"
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Health & Lifestyle */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-ink">Current Activity Level</label>
                <div className="mt-2 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                  {ACTIVITY_OPTIONS.map((item) => (
                    <button
                      type="button"
                      key={item.value}
                      onClick={() => setFormData({ ...formData, activity_level: item.value })}
                      className={`p-3 text-left rounded-lg border transition ${
                        formData.activity_level === item.value
                          ? "border-ink bg-ochre/15 text-ink shadow-sm"
                          : "border-line bg-white hover:border-dusk text-quiet"
                      }`}
                    >
                      <strong className="block text-sm text-ink">{item.label}</strong>
                      <span className="text-xs text-quiet">{item.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink">Dietary Preference</label>
                  <select
                    value={formData.dietary_preference}
                    onChange={(e) => setFormData({ ...formData, dietary_preference: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink bg-white"
                  >
                    {DIET_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink">Typical Sleep Duration</label>
                  <input
                    type="number"
                    step="0.5"
                    min="3"
                    max="14"
                    value={formData.sleep_duration_hours}
                    onChange={(e) => setFormData({ ...formData, sleep_duration_hours: Number(e.target.value) })}
                    className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink"
                    placeholder="Hours/night (e.g. 7.5)"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-ink">
                  Food Allergies or Intolerances <span className="text-xs text-quiet font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Peanuts, lactose, gluten, shellfish"
                  value={formData.allergies}
                  onChange={(e) => setFormData({ ...formData, allergies: e.target.value })}
                  className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-ink">
                  Medical Conditions, Medications or Physical Limitations <span className="text-xs text-quiet font-normal">(Optional)</span>
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Asthma, lower-back discomfort, hypertension (only share what you are comfortable disclosing)"
                  value={formData.medical_conditions}
                  onChange={(e) => setFormData({ ...formData, medical_conditions: e.target.value })}
                  className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink text-sm"
                />
                <p className="mt-1 text-[11px] text-quiet">
                  CareCompanion uses this to ensure exercise and meal recommendations avoid contraindicated advice.
                </p>
              </div>
            </div>
          )}

          {/* STEP 3: Goals */}
          {step === 3 && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-ink">
                  Select your primary wellness objectives <span className="text-xs text-quiet font-normal">(Pick all that apply)</span>
                </label>
                <div className="mt-3 flex flex-wrap gap-2">
                  {GOAL_OPTIONS.map((g) => {
                    const active = formData.goals.includes(g);
                    return (
                      <button
                        type="button"
                        key={g}
                        onClick={() => toggleGoal(g)}
                        className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                          active
                            ? "bg-ink text-white shadow"
                            : "bg-paper text-ink border border-line hover:border-dusk"
                        }`}
                      >
                        {active ? "✓ " : "+ "}
                        {g}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-ink">
                  Specific focus or target for the next 30 days <span className="text-xs text-quiet font-normal">(Optional)</span>
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Aiming to walk 8,000 steps daily, eat balanced dinners before 8 PM, and maintain consistent sleep."
                  value={formData.primary_goal}
                  onChange={(e) => setFormData({ ...formData, primary_goal: e.target.value })}
                  className="mt-1.5 w-full rounded-lg border border-line p-3 outline-none focus:border-dusk text-ink text-sm"
                />
              </div>
            </div>
          )}

          {/* STEP 4: Review and Confirmation */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-line bg-paper p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-line/60 pb-3">
                  <div>
                    <h3 className="text-lg font-semibold text-ink">{formData.full_name}</h3>
                    <p className="text-xs text-quiet">
                      {formData.age} years old · {formData.sex}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="text-xs font-semibold text-dusk hover:underline"
                  >
                    Edit Step 1
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-xs text-quiet block">Baseline Vitals</span>
                    <strong className="text-ink">
                      {formData.current_weight} {formData.unit_preference === "metric" ? "kg" : "lbs"} · {formData.height}{" "}
                      {formData.unit_preference === "metric" ? "cm" : "in"}
                    </strong>
                  </div>
                  <div>
                    <span className="text-xs text-quiet block">Activity & Diet</span>
                    <strong className="text-ink capitalize">
                      {formData.activity_level.replace("_", " ")} · {formData.dietary_preference}
                    </strong>
                  </div>
                </div>

                {formData.allergies && (
                  <div className="text-sm">
                    <span className="text-xs text-quiet block">Allergies</span>
                    <span className="text-ink">{formData.allergies}</span>
                  </div>
                )}

                {formData.medical_conditions && (
                  <div className="text-sm">
                    <span className="text-xs text-quiet block">Health Limitations</span>
                    <span className="text-ink">{formData.medical_conditions}</span>
                  </div>
                )}

                <div className="border-t border-line/60 pt-3 flex items-start justify-between">
                  <div>
                    <span className="text-xs text-quiet block mb-1">Active Goals</span>
                    <div className="flex flex-wrap gap-1.5">
                      {formData.goals.map((g) => (
                        <span key={g} className="rounded-md bg-white border border-line px-2.5 py-1 text-xs text-ink font-medium">
                          {g}
                        </span>
                      ))}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep(3)}
                    className="text-xs font-semibold text-dusk hover:underline"
                  >
                    Edit Goals
                  </button>
                </div>
              </div>

              {/* Privacy Notice Card */}
              <div className="rounded-xl border border-ochre/30 bg-[#FBF8F1] p-4 text-xs text-ink/80 space-y-1.5">
                <p className="font-semibold text-ink flex items-center gap-1.5">
                  <span>🔒</span> Strict Single-User Account Isolation
                </p>
                <p>
                  This health profile is strictly private to your authenticated account. CareCompanion is designed to coach only
                  you as the individual user. Your health measurements will never be applied to another person, and you can edit or
                  update your measurements anytime.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer controls */}
        <div className="flex items-center justify-between border-t border-line bg-paper px-8 py-4">
          {step > 1 ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => setStep((prev) => (prev - 1) as any)}
              className="rounded-lg px-4 py-2 text-sm font-medium text-ink hover:bg-white/80 transition"
            >
              ← Back
            </button>
          ) : (
            <div></div>
          )}

          <div className="flex items-center gap-3">
            {step < 4 ? (
              <button
                type="button"
                onClick={handleNext}
                className="rounded-lg bg-ink px-6 py-2.5 text-sm font-semibold text-white shadow hover:bg-[#263D59] transition"
              >
                Continue →
              </button>
            ) : (
              <button
                type="button"
                disabled={busy}
                onClick={handleSubmit}
                className="rounded-lg bg-ink px-6 py-2.5 text-sm font-semibold text-white shadow hover:bg-[#263D59] transition disabled:opacity-50"
              >
                {busy ? "Saving Profile..." : "Confirm & Begin Coaching"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
