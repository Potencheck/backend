from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.dependency import get_user_service
from app.schemas import UserCreate
from app.services.user_service import UserServiceInterface

router = APIRouter(
    prefix="/user",
    tags= ["users"]
)

@router.post("/data", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_user(
        user: UserCreate,
        user_service: UserServiceInterface =Depends(get_user_service)
):
    user_id = user_service.create_user(user)
    return {"id": user_id}

