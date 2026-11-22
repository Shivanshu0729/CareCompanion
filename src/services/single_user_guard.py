from __future__ import annotations

import re
from typing import Sequence

THIRD_PARTY_REFUSAL_MESSAGE = (
    "I'm designed to provide personalized health coaching only for the person currently "
    "logged into this account. I can't create personalized health recommendations or "
    "maintain health profiles for someone else. This conversation and its health data "
    "belong to the currently logged-in user."
)

OFF_TOPIC_HEALTH_REDIRECT = (
    "I am CareCompanion, your dedicated health and wellness coach. I focus on "
    "fitness, nutrition, sleep, recovery, daily routines, and your personal wellness profile. "
    "How can I assist you with your health and wellbeing goals today?"
)

# Entities denoting third parties
THIRD_PARTY_ENTITY_PATTERN = re.compile(
    r"\b("
    r"my\s+(friend|father|dad|mother|mom|brother|sister|son|daughter|child|kid|children|kids|"
    r"wife|husband|partner|girlfriend|boyfriend|cousin|uncle|aunt|grandfather|grandmother|"
    r"grandpa|grandma|parent|parents|roommate|colleague|coworker|boss|client)|"
    r"a\s+(friend|coworker|colleague)|someone\s+i\s+know|"
    r"for\s+(him|her|them)\b|"
    r"\b(his|her)\s+(weight|diet|health|condition|diabetes|routine|workout|exercises?|pain|symptoms|age)"
    r")\b",
    re.IGNORECASE,
)

# Coaching/recommendation verbs or requests
COACHING_REQUEST_PATTERN = re.compile(
    r"\b("
    r"suggest|recommend|create|make|give|provide|tell|design|plan|prescribe|"
    r"what\s+([a-z\s-]+\s+)?(should|can|does|to|could)\s+(he|she|they|my\s+\w+)\s+(do|eat|follow|take|try|perform)|"
    r"(diet|workout|exercise|meal|fitness|weight[- ]loss)\s+plan|"
    r"exercises?\s+(for|should)|"
    r"how\s+(can|should|could)\s+(he|she|they|my\s+\w+)"
    r")\b",
    re.IGNORECASE,
)

# Off-topic patterns (strictly unrelated non-health queries)
OFF_TOPIC_PATTERNS: Sequence[re.Pattern] = (
    re.compile(
        r"\b(write|create|code|debug|build)\s+(a\s+|an\s+|the\s+|this\s+)?(python|java|javascript|typescript|c\+\+|c#|golang|rust|ruby|php|sql|html|css|bash|docker|react|vue|node)\s+(script|program|code|scraper|app|backend|function|component|algorithm|query|api|service|pipeline|dockerfile)\b",
        re.I,
    ),
    re.compile(
        r"\b(solve|calculate|compute)\s+(this\s+|the\s+)?(math\s+|mathematical\s+)?(integral|derivative|equation|math|calculus|matrix|formula|algebra)\b",
        re.I,
    ),
    re.compile(
        r"\b(who\s+won|what\s+happened\s+in)\s+(the\s+)?(world\s+cup|war\s+of|super\s+bowl|battle\s+of|election\s+of|championship)\b",
        re.I,
    ),
    re.compile(
        r"\b(write\s+an?\s+(essay|story|poem|song|speech|article|paper)\s+about)\b",
        re.I,
    ),
    re.compile(
        r"\b(debug|fix)\s+(this\s+|the\s+)?(docker|compose|kubernetes|git|compiler|syntax|npm|pip|build|exception|error|stack\s*trace)\b",
        re.I,
    ),
)


def is_third_party_health_request(message: str) -> tuple[bool, str | None]:
    """Detect if a user message is asking for personalized health advice/plans for a third party.

    Returns (True, entity_label) if the request is for someone else, (False, None) otherwise.
    """
    text = message.strip()
    if not text:
        return False, None

    # Check if the message contains explicit third-party entity references
    entity_match = THIRD_PARTY_ENTITY_PATTERN.search(text)
    if not entity_match:
        return False, None

    matched_entity = entity_match.group(0).lower()

    # Check if the message asks for personalized coaching / recommendations
    coaching_match = COACHING_REQUEST_PATTERN.search(text)
    if coaching_match:
        return True, matched_entity

    # Direct "for him", "for her", "for them" with plan/routine keywords
    if re.search(r"\b(plan|routine|workout|diet|exercises?|stretches)\s+for\s+(him|her|them)\b", text, re.I):
        return True, matched_entity

    # "what exercises/workout/diet should he/she do/eat/take"
    if re.search(r"\bwhat\s+([a-z\s-]+\s+)?should\s+(he|she|they)\b", text, re.I):
        return True, matched_entity

    # "what [workout/exercises] should [entity] do"
    if re.search(r"\bwhat\s+(exercises?|workout|diet|routine|food|meals?)\s+should\b", text, re.I):
        return True, matched_entity

    return False, None


def contains_third_party_reference(text: str) -> bool:
    """Check if a factual statement or memory candidate is about a third party."""
    if not text:
        return False
    return bool(THIRD_PARTY_ENTITY_PATTERN.search(text))


def is_off_topic_non_health(message: str) -> tuple[bool, str | None]:
    """Check if the user is asking for completely off-topic non-health tasks (e.g. coding, math, history)."""
    text = message.strip()
    for pattern in OFF_TOPIC_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, match.group(0)
    return False, None
