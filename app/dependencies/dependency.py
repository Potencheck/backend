from fastapi import Depends
from app.database import get_db
from app.services.career_service import CareerServiceInterface, CareerService

def get_career_service() -> CareerServiceInterface:
    return CareerService()