from src.data.health_service import HealthService
from src.database.store import CareStore


class DashboardService:
    def __init__(self, store: CareStore, health_service: HealthService | None = None) -> None:
        self.store = store
        self.health_service = health_service or HealthService()

    def goals_by_status(self, user_id: str) -> dict[str, list]:
        grouped = {"active": [], "completed": [], "needs_attention": [], "paused": []}
        for goal in self.store.list_goals(user_id):
            grouped.setdefault(goal.status, []).append(goal)
        return grouped
