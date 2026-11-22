from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_COMMON_SUFFIXES = ("ing", "tion", "tions", "ies", "es", "s", "ed", "ment", "ments", "er", "ers")

SINGLE_VALUE_KEYS = {
    "current_weight",
    "weight",
    "height",
    "current_height",
    "age",
    "name",
    "profession",
    "education",
    "diet_type",
    "explanation_style",
    "sleep_bedtime",
    "project_status",
    "framework_choice",
}

CANONICAL_KEY_ALIASES: dict[str, str] = {
    # Weight aliases -> all map to canonical key "current_weight"
    "weight": "current_weight",
    "current_weight": "current_weight",
    "user_weight": "current_weight",
    "body_weight": "current_weight",
    "current_body_weight": "current_weight",
    "bodyweight": "current_weight",
    "weight_kg": "current_weight",
    "weight_lbs": "current_weight",
    "weigh": "current_weight",
    "my_weight": "current_weight",
    "target_weight": "target_weight",

    # Height aliases
    "user_height": "height",
    "current_height": "height",
    "my_height": "height",
    "stature": "height",
    "height_cm": "height",

    # Age aliases
    "user_age": "age",
    "current_age": "age",
    "my_age": "age",
    "birth_age": "age",

    # Name aliases
    "user_name": "name",
    "preferred_name": "name",
    "first_name": "name",
    "full_name": "name",
    "display_name": "name",
    "my_name": "name",

    # Profession aliases
    "job": "profession",
    "occupation": "profession",
    "work": "profession",
    "career_role": "profession",
    "job_title": "profession",

    # Diet aliases
    "diet": "diet_type",
    "dietary_preference": "diet_type",
    "food_preference": "diet_type",
    "eating_habit": "diet_type",

    # Style aliases
    "style": "explanation_style",
    "response_length": "explanation_style",
    "tone": "explanation_style",
    "communication_style": "explanation_style",

    # Bedtime aliases
    "bedtime": "sleep_bedtime",
    "target_bedtime": "sleep_bedtime",
    "sleep_schedule": "sleep_bedtime",

    # Tech stack / framework
    "backend_framework": "framework_choice",
    "primary_framework": "framework_choice",
    "tech_framework": "framework_choice",
}


def normalize_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.lower()))


def tokenize(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


def simple_stem(word: str) -> str:
    """Lightweight suffix-stripping for morphological variants (e.g. issues -> issue)."""
    word = word.lower()
    if len(word) <= 3:
        return word
    for suffix in _COMMON_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def stemmed_tokens(value: str) -> set[str]:
    return {simple_stem(tok) for tok in tokenize(value)}


def token_overlap(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)


def stemmed_token_overlap(left: str, right: str) -> float:
    left_tokens = stemmed_tokens(left)
    right_tokens = stemmed_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)


def is_near_duplicate(left: str, right: str, threshold: float = 0.82) -> bool:
    norm_left = normalize_text(left)
    norm_right = normalize_text(right)
    if norm_left == norm_right:
        return True
    # Digits/numbers (e.g. 75 vs 80) indicate distinct factual values, not duplicates
    digits_left = set(re.findall(r"\b\d+(?:\.\d+)?\b", norm_left))
    digits_right = set(re.findall(r"\b\d+(?:\.\d+)?\b", norm_right))
    if digits_left != digits_right:
        return False
    return token_overlap(left, right) >= threshold


def relevance_score(query: str, content: str) -> float:
    if not query.strip():
        return 0.15
    overlap = token_overlap(query, content)
    stem_overlap = stemmed_token_overlap(query, content)
    query_tokens = tokenize(query)
    content_tokens = tokenize(content)
    if not query_tokens:
        return 0.15
    coverage = len(query_tokens & content_tokens) / len(query_tokens)
    stem_coverage = len(stemmed_tokens(query) & stemmed_tokens(content)) / len(stemmed_tokens(query))
    
    # Combined exact + stemmed score
    return (0.35 * overlap) + (0.25 * stem_overlap) + (0.20 * coverage) + (0.20 * stem_coverage)


def is_credential_or_secret(text: str) -> bool:
    """Detects API keys, passwords, bearer tokens, or secrets that must never be stored in memory."""
    patterns = (
        r"\b(?:gsk_|sk-|ghp_|gho_|xoxb-|xoxp-)[A-Za-z0-9_]{16,}\b",
        r"\bBearer\s+[A-Za-z0-9\-_=]{20,}\b",
        r"\b(?:password|passwd|api_key|apikey|secret_key|auth_token)\s*[:=]\s*[^\s,;]{6,}\b",
        r"\b[A-Za-z0-9+/]{40,}={0,2}\b",  # Generic base64 / hash tokens
    )
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def detect_query_intents(query: str) -> set[str]:
    """Detect topics in user query to bias memory retrieval."""
    lowered = query.lower()
    intents: set[str] = set()

    if re.search(r"\b(python|java|javascript|typescript|c\+\+|rust|go|react|fastapi|backend|frontend|code|coding|learn|study|library|framework|syntax|algorithm|programming)\b", lowered):
        intents.add("learning")
        intents.add("technical")

    if re.search(r"\b(job|internship|career|hire|resume|interview|role|position|company|salary|promotion)\b", lowered):
        intents.add("career")

    if re.search(r"\b(project|previous project|carecompanion|architecture|stack|database|continue|task|milestone|feature|app|system|repo|repository)\b", lowered):
        intents.add("project")

    if re.search(r"\b(health|condition|issue|issues|lung|breathing|heart|sleep|bedtime|diet|food|allergic|allergy|injury|pain|medication|doctor|weight|height|routine|run|running|marathon|jog|jogging|exercise|workout|cardio|gym)\b", lowered):
        intents.add("health")

    if re.search(r"\b(preference|explain|style|format|concise|detailed|short|table|bullet)\b", lowered):
        intents.add("preference")

    if re.search(r"\b(who am i|my name|what do you know|about me|tell me (?:all )?about|profile|my background|remember)\b", lowered):
        intents.add("profile")

    return intents


def is_historical_query(query: str) -> bool:
    """Detects whether user is explicitly asking about historical/previous values."""
    lowered = query.lower()
    return bool(
        re.search(
            r"\b(previous|previously|past|earlier|before|history|used to|old|former|last time|did i weigh|was my weight)\b",
            lowered,
        )
    )


def is_single_value_key(key: str | None) -> bool:
    """Returns True if the key represents a fact with at most one current value."""
    if not key:
        return False
    return key in SINGLE_VALUE_KEYS


def extract_weight_update(text: str) -> tuple[float, str, str] | None:
    """
    Detects and validates an explicit weight update from user text.
    Returns (numeric_value, unit, formatted_statement) or None.
    Validates reasonable human weight (20-400 kg or 44-880 lbs).
    """
    lowered = text.lower()
    if not re.search(r"\b(weigh|weight|weighs|kg|kgs|kilogram|kilograms|lbs|pound|pounds)\b", lowered):
        return None

    patterns = (
        r"\b(?:my\s+weight\s+is|i\s+weigh|weight\s+(?:is\s+)?now|update\s+(?:my\s+)?weight\s+to|current\s+weight\s*[:=]?)\s*(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|lbs?|pounds?)?\b",
        r"\bweigh(?:ing)?\s*(?:around|about|approximately)?\s*(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|lbs?|pounds?)\b",
        r"\b(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|lbs?|pounds?)\s*(?:in weight|body\s*weight)\b",
        r"\bweight\s*[:=]\s*(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|lbs?|pounds?)?\b",
    )

    for pattern in patterns:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            raw_val = match.group(1)
            raw_unit = match.group(2) if len(match.groups()) >= 2 and match.group(2) else "kg"
            try:
                num = float(raw_val)
            except ValueError:
                continue

            unit = "lbs" if "lb" in raw_unit.lower() or "pound" in raw_unit.lower() else "kg"

            if unit == "kg" and not (20.0 <= num <= 400.0):
                continue
            if unit == "lbs" and not (44.0 <= num <= 880.0):
                continue

            num_str = f"{num:g}"
            formatted = f"User's current weight is {num_str} {unit}."
            return (num, unit, formatted)

    return None


def canonical_category(key: str | None, content: str, default: str = "health") -> str:
    """Classifies memory into proper domain category."""
    lowered = content.lower()
    c_key = key or ""

    # Health: weight, height, diet, allergies, respiratory, cardiac, health conditions
    if c_key in {"current_weight", "weight", "height", "current_height", "diet_type"} or \
       re.search(r"\b(weigh|weight|height|tall|vegetarian|vegan|keto|diet|allergic|allergy|asthma|lung|breathing|cardiac|heart|blood pressure)\b", lowered):
        return "health"

    # Profile: name, education, profession
    if c_key in {"name", "profession", "education"} or \
       re.search(r"\b(name is|call me|my name|degree|graduated|university|college|profession|job|work as|software engineer|developer)\b", lowered):
        return "profile"

    # Goals: career, learning, fitness goals
    if c_key.startswith("learning_goal") or c_key.startswith("career_goal") or c_key == "fitness_goal" or \
       re.search(r"\b(goal|learn|learning|internship|career goal|fitness goal)\b", lowered):
        return "goal"

    # Projects / Context:
    if c_key.startswith("project_") or re.search(r"\b(project|carecompanion|architecture|stack|tech choice)\b", lowered):
        return "context"

    # Progress:
    if c_key.startswith("progress_") or re.search(r"\b(completed|milestone|finished|outcome|progress)\b", lowered):
        return "progress"

    # Preferences:
    if c_key in {"explanation_style", "sleep_bedtime", "framework_choice"} or \
       re.search(r"\b(style|tone|format|concise|detailed|bullet points)\b", lowered):
        return "preference"

    if default == "recommendation" or "recommend" in lowered:
        return "recommendation"

    return default


def memory_key(content: str) -> str | None:
    return normalize_canonical_key(None, "preference", content)


def normalize_canonical_key(raw_key: str | None, category: str, content: str) -> str | None:
    """
    Unconditionally normalizes keys into deterministic canonical representations.
    Prevents fragmentation across 'user_weight', 'current_weight', and 'body_weight'.
    """
    lowered = content.lower()

    # Rule 1: Explicit content pattern overrides
    if re.search(r"\b(weigh|weight|weighs|weighing)\b", lowered):
        return "current_weight"
    if re.search(r"\b(height|tall)\b", lowered):
        return "height"
    if re.search(r"\b(age|years old)\b", lowered):
        return "age"
    if re.search(r"\b(name is|call me|my name)\b", lowered):
        return "name"
    if re.search(r"\b(vegetarian|vegan|keto|non-vegetarian|eat meat|pescatarian)\b", lowered):
        return "diet_type"
    if re.search(r"\b(lung|breathing|respiratory|asthma)\b", lowered):
        return "health_respiratory"
    if re.search(r"\b(heart|cardiac|blood pressure|bp|hypertension)\b", lowered):
        return "health_cardiac"
    if re.search(r"\b(allergy|allergic)\b", lowered):
        match = re.search(r"\ballergic to ([a-z0-9_\- ]+)", lowered)
        item = match.group(1).split()[0] if match else "general"
        return f"allergy_{item}"

    # Rule 2: Clean and check raw_key against alias map
    if raw_key:
        cleaned = raw_key.lower().strip().replace(" ", "_").replace("-", "_")
        if cleaned in CANONICAL_KEY_ALIASES:
            return CANONICAL_KEY_ALIASES[cleaned]
        if cleaned in SINGLE_VALUE_KEYS:
            return cleaned
        if cleaned not in {"general", "none", "null", "undefined", "unknown", "preference", "fact"}:
            return cleaned

    # Rule 3: Category-based canonical inference
    return canonical_memory_key(category, content)


def canonical_memory_key(category: str, content: str) -> str | None:
    """Generates canonical keys to support deterministic update and superseding logic."""
    lowered = content.lower()

    # Health & Body
    if "weight" in lowered or "weigh" in lowered:
        return "current_weight"
    if "height" in lowered:
        return "height"
    if re.search(r"\bage\b|\byears old\b", lowered):
        return "age"
    if re.search(r"\b(lung|breathing|respiratory|asthma)\b", lowered):
        return "health_respiratory"
    if re.search(r"\b(heart|cardiac|blood pressure|bp|hypertension)\b", lowered):
        return "health_cardiac"
    if re.search(r"\b(allergy|allergic)\b", lowered):
        match = re.search(r"\ballergic to ([a-z0-9_\- ]+)", lowered)
        item = match.group(1).split()[0] if match else "general"
        return f"allergy_{item}"

    # Profile & Identity
    if "name is" in lowered or "call me" in lowered:
        return "name"
    if re.search(r"\b(profession|job|work as|software engineer|developer|designer|manager|student)\b", lowered):
        return "profession"
    if re.search(r"\b(degree|university|college|graduated|education|studying at)\b", lowered):
        return "education"

    # Goals
    if re.search(r"\b(learn|learning|study)\b", lowered):
        if "python" in lowered:
            return "learning_goal_python"
        if "java" in lowered:
            return "learning_goal_java"
        if "javascript" in lowered or "typescript" in lowered:
            return "learning_goal_js_ts"
        return "learning_goal"
    if re.search(r"\b(internship|job|career|hired|employment)\b", lowered):
        return "career_goal"
    if re.search(r"\b(fitness|run|running|marathon|gym|workout)\b", lowered):
        return "fitness_goal"

    # Projects
    if "carecompanion" in lowered:
        return "project_carecompanion"
    if re.search(r"\bproject\b", lowered):
        match = re.search(r"project (?:is|called|named)?\s*([a-z0-9_\-]+)", lowered)
        name = match.group(1) if match else "primary"
        return f"project_{name}"

    # Preferences
    if re.search(r"\b(vegetarian|vegan|keto|non-vegetarian|meat|halal|kosher)\b", lowered):
        return "diet_type"
    if re.search(r"\b(concise|detailed|bullet points|explanation style)\b", lowered):
        return "explanation_style"

    # Fallback category-specific generic key if meaningful
    if category in {"profile", "goal", "context", "progress", "preference", "health"}:
        words = [w for w in _TOKEN_RE.findall(lowered) if len(w) > 3 and w not in {"user", "that", "this", "have", "with", "from"}]
        if words:
            return f"{category}_{words[0]}"

    return None
