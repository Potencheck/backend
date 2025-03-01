from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    # 사용자 기본 정보 스키마
    name: str
    exp: str  # job_type 대신 exp 사용
    job: str

class UserCreate(UserBase):
    name: str
    exp: str  # job_type 대신 exp 사용
    job: str

class User(UserBase):
    UUID: str

    class Config:
        orm_mode = True