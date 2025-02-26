from sqlalchemy.orm import Session
import uuid
from typing import Optional

from app.models.user import User as UserModel
from app.schemas.user import UserCreate, User as UserSchema
from app.repository.user_repository import UserRepositoryInterface

class UserService:
    def __init__ (self, user_repository: UserRepositoryInterface):
        self.user_repository = user_repository

    def create_user(self, db: Session, user: UserCreate) -> UserSchema:
        user_uuid = str(uuid.uuid4())
        user = UserModel(uuid=user_uuid, name=user.name, job_type=user.job_type, job=user.job)
        return self.user_repository.create_user(db, user)