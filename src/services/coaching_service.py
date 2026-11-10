from src.agent.coach import WellnessCoach
from src.database.store import CareStore
from src.llm.provider import LLMProvider


class CoachingService:
    def __init__(self, store: CareStore, llm: LLMProvider) -> None:
        self.coach = WellnessCoach(store, llm)

    def send(self, user_id: str, conversation_id: str, message: str):
        return self.coach.respond(user_id, conversation_id, message)
