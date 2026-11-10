from src.auth.authentication import AuthSession
from src.database.store import CareStore


class UserService:
    def __init__(self, store: CareStore) -> None:
        self.store = store

    def identity(self, session: AuthSession) -> dict[str, str]:
        return {"id": session.user.id, "email": session.user.email}
