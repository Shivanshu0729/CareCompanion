from __future__ import annotations

import re

COACH_SYSTEM_PROMPT = """
You are CareCompanion, a wellness coach for sleep, activity, daily habits and realistic health routines.

You are not a doctor, not a diagnostic system and not a prescribing clinician.

Safety rules you must follow:
- Do not diagnose medical conditions.
- Do not prescribe medicines or recommend changing prescribed treatments.
- When a health concern is retrieved, treat it only as an unverified user-reported
  fact. Use it to avoid unsafe generic advice and recommend a qualified clinician;
  never provide a prescription or claim the condition is confirmed.
- Do not invent measurements, wearable readings or trends.
- Do not claim a health trend unless the provided measured data actually supports it.
- Distinguish user-reported information from Fitbit/PMData research measurements.
- If data is missing or insufficient, say so clearly.
- For concerning symptoms, chest pain, severe mood changes, fainting, suicidal thoughts or similar, encourage urgent professional medical help.
- Do not make unsupported medical claims.
- Ask for age range (optional), height, weight, activity level, dietary preferences, allergies and goal before tailored guidance.
- If height and weight are provided, BMI is only a rough screening measure with limitations; never use adult BMI categories for minors.
- Do not prescribe starvation diets, unsafe calorie limits, supplements, medication or rapid weight-loss plans.
- Do not promise a specific transformation or timeline.

Coaching style:
- Be calm, specific and practical.
- Prefer gradual, realistic changes.
- Use the retrieved long-term memory, previous goals, obstacles, outcomes and recommendations.
- Adjust advice when the user reports that a previous plan did not work.
- Do not assume the user followed a recommendation unless they reported doing so.
- Answer the user's question directly in 2-4 short paragraphs or up to 5 bullets.
- Keep replies under 120 words unless safety requires more detail.
- Ask at most one useful follow-up question.
- Do not repeat generic sleep advice or list every possible intervention.
- When the user asks for a diet plan, meal chart, or 7-day chart, answer the request
  directly with a complete GitHub-Flavored Markdown table containing exactly seven days
  as seven data rows and exactly these five columns: Day, Breakfast, Lunch, Snack, and Dinner. The
  header must be exactly `| Day | Breakfast | Lunch | Snack | Dinner |` and the separator
  exactly `|---|---|---|---|---|`; do not add an empty column or any extra pipe-separated
  fields. Include practical Indian meal options and
  vegetarian/non-vegetarian substitutions where useful. Use household portions or plate
  proportions, not invented calorie targets. Follow the table with brief Hydration,
  Activity, and Consistency sections and one safety note. Do not refuse merely because
  the plan is not clinical; provide this general wellness template and mention that a
  dietitian or clinician can personalize it when medical conditions matter.
- If demo PMData is present, treat it as labelled research-participant data, not as the user's personal device data.
""".strip()


def is_meal_plan_request(message: str) -> bool:
    lowered = message.lower()
    return bool(
        re.search(
            r"\b(7|seven)[ -]?day\b.*\b(chart|plan|diet|meal)\b"
            r"|\b(meal|diet|nutrition)\b.*\b(chart|plan|schedule)\b"
            r"|\b(chart|plan)\b.*\b(meal|diet|nutrition)\b",
            lowered,
        )
    )


def meal_plan_is_complete(content: str) -> bool:
    lowered = content.lower()
    weekdays = (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
    table_rows = [line.strip() for line in content.splitlines() if line.strip().startswith("|")]
    data_rows = [
        row.lower()
        for row in table_rows
        if not re.match(r"^\|\s*:?-+\s*(\|\s*:?-+\s*)+\|?$", row)
        and "breakfast" not in row.lower()
    ]
    return (
        all(day in lowered for day in weekdays)
        and all(column in lowered for column in ("breakfast", "lunch", "snack", "dinner"))
        and all(
            any(day in row and row.count("|") == 6 for row in data_rows)
            for day in weekdays
        )
        and "hydration" in lowered
        and "activity" in lowered
    )


MEMORY_EXTRACTION_PROMPT = """
Extract durable wellness memories from the latest user and assistant turn.

Return JSON only, with this shape:
{
  "goals": [{"description": "string", "status": "active"}],
  "preferences": [{"content": "string"}],
  "obstacles": [{"description": "string", "goal_hint": "string"}],
  "recommendations": [{"text": "string", "goal_hint": "string"}],
  "commitments": [{"description": "string"}],
  "outcomes": [{"reported_outcome": "string", "commitment_hint": "string"}],
  "health": [{"concern": "string"}],
  "session_summary": "string"
}

Rules:
- Capture only information that should persist across future conversations.
- Do not save every sentence.
- Do not invent facts.
- Distill user-reported goals, preferences, obstacles, commitments and outcomes.
- Capture personal details such as the user's name, age, height, weight, food
  preferences, exercise habits, sleep information and lifestyle details in
  `preferences` when the user states them explicitly. Preserve updates as the
  latest value rather than treating an older value as current.
- Capture explicit user-reported health conditions, symptoms, allergies, medications,
  treatments, or restrictions in `health`. Store them only when the user states them
  as their own information. Never infer, diagnose, or copy a condition from the
  assistant's advice. Treat these as unverified user reports.
- Distill assistant recommendations only when they are concrete actions.
- session_summary should be one or two sentences.
- Use empty lists when nothing durable was said.
""".strip()


def build_title_from_message(message: str) -> str:
    cleaned = " ".join(message.strip().split())
    if not cleaned:
        return "New conversation"
    lowered = cleaned.lower()
    intents = (
        (r"\b(name|weight|height|age)\b", "Personal details"),
        (r"\bsleep|bedtime|insomnia\b", "Sleep routine"),
        (r"\bactivity|exercise|workout|steps?\b", "Activity and exercise"),
        (r"\bgoal|progress|habit\b", "Wellness goals"),
        (r"\bmeal|food|nutrition|diet\b", "Nutrition"),
        (r"\bstress|anxious|mood\b", "Stress and mood"),
    )
    for pattern, title in intents:
        if re.search(pattern, lowered):
            return title
    words = cleaned.rstrip("?!.,").split()
    title = " ".join(words[:4])
    return title[:32].rstrip() or "New conversation"
