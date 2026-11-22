from __future__ import annotations

import logging
import re
from typing import Sequence

from src.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)

TITLE_SYSTEM_PROMPT = (
    "You are a conversation title generator. Based on the user's first message, "
    "generate one short and descriptive title of 2–6 words. Capture the main subject, "
    "avoid generic wording, do not answer the user's question, and return only the title "
    "without quotation marks or explanation."
)

DISALLOWED_TITLES = {
    "new conversation",
    "new chat",
    "chat",
    "general discussion",
    "health chat",
    "discussion",
    "conversation",
    "untitled",
    "wellness coach",
    "carecompanion",
    "title",
    "question",
    "health",
    "user message",
    "first message",
}


def to_title_case(text: str) -> str:
    """Format title with proper capitalization for 2-6 word titles."""
    lower_words = {"a", "an", "the", "in", "on", "for", "and", "to", "at", "by", "of", "with", "is", "as"}
    words = text.split()
    if not words:
        return ""
    titled = []
    for i, w in enumerate(words):
        if i == 0 or i == len(words) - 1 or w.lower() not in lower_words:
            titled.append(w.capitalize())
        else:
            titled.append(w.lower())
    return " ".join(titled)


def clean_title(raw: str) -> str:
    """Clean and standardize a generated title into 2-6 words."""
    if not raw:
        return ""
    text = raw.strip()

    # Remove prefixes like 'Title:', 'Subject:', 'Topic:', 'Conversation:'
    text = re.sub(r"^(title|subject|topic|conversation)\s*:\s*", "", text, flags=re.IGNORECASE)

    # Strip quotation marks and common markdown wrappers
    text = text.strip("\"'“”«»‘’`*#_ ")

    # Remove emojis and non-alphanumeric/standard punctuation
    text = re.sub(r"[^\w\s\'-]", " ", text)

    # Remove trailing punctuation
    text = text.rstrip(".!?:;,- ")

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    if not words:
        return ""

    # Truncate to maximum 6 words
    if len(words) > 6:
        words = words[:6]

    cleaned = to_title_case(" ".join(words))
    return cleaned[:80].strip()


def generate_fallback_title(message: str) -> str:
    """Generate a high-quality, concise 2-6 word fallback title without LLM."""
    cleaned = " ".join(message.strip().split())
    if not cleaned:
        return "Getting Started"

    lowered = cleaned.lower()

    # 1. Domain-specific intent patterns matching common wellness/tech/project queries
    patterns: Sequence[tuple[str, str]] = (
        (r"\b(sleep\s+schedule|sleep\s+routine|sleep\s+pattern|improve\s+.*sleep)\b", "Improving Sleep Schedule"),
        (r"\b(lose\s+weight|weight\s+loss)\b.*\b(eat|food|diet|nutrition)\b", "Weight Loss Nutrition"),
        (r"\b(eat|food|diet|nutrition|meal\s+plan)\b.*\b(lose\s+weight|weight\s+loss)\b", "Weight Loss Nutrition"),
        (r"\b(feeling\s+tired|feel\s+tired|fatigue|exhausted|low\s+energy)\b", "Understanding Daily Fatigue"),
        (r"\b(workout\s+routine|exercise\s+routine|build\s+.*workout)\b", "Building a Workout Routine"),
        (r"\b(analyze|review|check)\b.*\b(sleep\s+data|fitbit|health\s+data|data)\b", "Sleep Data Analysis"),
        (r"\b(daily\s+activity|improve\s+.*activity|step\s+count|more\s+active)\b", "Improving Daily Activity"),
        (r"\b(sleep|bedtime|insomnia|wake\s*up)\b", "Sleep and Recovery Routine"),
        (r"\b(meal\s+plan|diet\s+plan|7\s*day\s+chart|meal\s+chart)\b", "7-Day Nutrition Plan"),
        (r"\b(nutrition|diet|eating|calories|protein)\b", "Nutrition and Healthy Habits"),
        (r"\b(workout|exercise|fitness|running|gym)\b", "Fitness and Exercise Plan"),
        (r"\b(stress|anxiety|anxious|overwhelmed|calm|mindfulness)\b", "Stress and Mental Wellbeing"),
        (r"\b(weight|current\s+weight|body\s+weight)\b", "Body Weight Tracking"),
        (r"\b(blood\s+pressure|heart\s+rate|pulse|vitals)\b", "Heart Rate and Vitals"),
        (r"\b(habit|goals?|routine|discipline)\b", "Building Better Habits"),
        (r"\b(python|fastapi|react|code|coding|software|api|backend|frontend)\b", "Technical and Coding Discussion"),
        (r"\b(project|architecture|milestone|feature|carecompanion)\b", "Project Architecture and Planning"),
        (r"\b(career|job|internship|resume|interview)\b", "Career and Professional Goals"),
    )

    for pattern, title in patterns:
        if re.search(pattern, lowered):
            return title

    # 2. General sentence condensation: strip conversational preambles
    condensed = re.sub(
        r"^(can you|could you|please|help me|i want to|i would like to|tell me about|"
        r"how do i|what should i|how can i|i need help with|i have been|i am|i'm|"
        r"what is|how to)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Clean leading verbs (e.g. "improve my posture" -> "Improving Posture")
    condensed = re.sub(r"^improve\b", "improving", condensed, flags=re.IGNORECASE)
    condensed = re.sub(r"^build\b", "building", condensed, flags=re.IGNORECASE)
    condensed = re.sub(r"^create\b", "creating", condensed, flags=re.IGNORECASE)
    condensed = re.sub(r"^review\b", "reviewing", condensed, flags=re.IGNORECASE)
    condensed = re.sub(r"^track\b", "tracking", condensed, flags=re.IGNORECASE)
    condensed = re.sub(r"^understand\b", "understanding", condensed, flags=re.IGNORECASE)

    # Remove punctuation
    condensed = re.sub(r"[^\w\s\'-]", " ", condensed)
    words = [w for w in condensed.split() if w.lower() not in {"a", "an", "the", "my", "our", "some"}]
    if not words:
        words = cleaned.split()

    # Pick 2 to 5 words
    selected_words = words[:5]
    if len(selected_words) < 2 and len(words) >= 2:
        selected_words = words[:2]

    title = " ".join(selected_words).title()
    title = clean_title(title)

    if not title or title.lower() in DISALLOWED_TITLES or len(title.split()) < 2:
        return "General Inquiry"

    return title


class TitleGenerator:
    """Generates concise, professional conversation titles using LLM or algorithmic fallback."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def generate_title(self, first_user_message: str) -> str:
        """Generate a 2-6 word title based on the first user message."""
        cleaned_input = first_user_message.strip()
        if not cleaned_input:
            return "Getting Started"

        # Attempt LLM generation if client is available
        if self.llm is not None:
            try:
                messages = [
                    LLMMessage(role="system", content=TITLE_SYSTEM_PROMPT),
                    LLMMessage(role="user", content=cleaned_input),
                ]
                # Fast, focused generation with low token limit
                response = self.llm.generate(
                    messages,
                    temperature=0.2,
                    max_tokens=25,
                )
                generated = clean_title(response.content)
                words = generated.split()
                # Validate output
                if (
                    generated
                    and 2 <= len(words) <= 7
                    and generated.lower() not in DISALLOWED_TITLES
                    and not re.search(r"@[a-zA-Z0-9.-]+", generated)  # No emails/handles
                ):
                    return generated
            except Exception as exc:
                logger.info("LLM title generation skipped or failed, using fallback: %s", exc)

        # Fallback to smart algorithmic title generation
        return generate_fallback_title(cleaned_input)
