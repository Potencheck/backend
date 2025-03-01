import uuid
from typing import Protocol, Optional

from app.models.user import User as UserModel
from app.schemas.user import UserCreate, User as UserSchema
from app.repository.user_repository import UserRepositoryInterface


class UserServiceInterface(Protocol):
    def create_user(self, user: UserCreate) -> str:
        ...

    def get_user_by_id(self, id: str) -> Optional[UserSchema]:
        ...


class UserService(UserServiceInterface):
    def __init__(self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository

    def create_user(self, user: UserCreate) -> str:
        user_uuid = str(uuid.uuid4())
        user_model = UserModel(
            uuid=user_uuid,
            name=user.name,
            job_type=user.job_type,
            job=user.job
        )
        self.user_repository.create_user(user_model)
        return user_uuid

    def get_user_by_id(self, id: str) -> Optional[UserSchema]:
        user = self.user_repository.get_user_by_id(id)
        if not user:
            return None
        return UserSchema.from_orm(user)