from pydantic import BaseModel
from typing import List
from app.schemas.user import UserBase

class CareerModel(BaseModel):
    job: str
    company: str
    description: str

class CareerRequest(BaseModel):
    user: UserBase
    career: List[CareerModel]
    activities: List[str]
    certifications: List[str]