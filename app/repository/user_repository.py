from sqlalchemy.orm import Session
from app.models.user import User
from typing import Protocol, Optional

class UserRepositoryInterface(Protocol):
    def get_user_by_id(self, id: str) -> Optional[User]:
        ...

    def create_user(self, user: User) -> User:
        ...


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, id: str) -> Optional[User]:
        return self.db.get(User, id)

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user