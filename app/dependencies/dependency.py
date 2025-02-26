from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.repository.user_repository import UserRepository, UserRepositoryInterface
from app.services.user_service import UserService, UserServiceInterface

def get_user_repository(db: Session = Depends(get_db)) -> UserRepositoryInterface:
    return UserRepository(db)

def get_user_service(
    user_repository: UserRepositoryInterface = Depends(get_user_repository)
) -> UserServiceInterface:
    return UserService(user_repository)