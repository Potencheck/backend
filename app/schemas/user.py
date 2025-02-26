from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    # 사용자 기본 정보 스키마
    name: str
    job_type: str
    job: str

class UserCreate(UserBase):
    # 사용자 생성 요청 스키마
    pass

class User(UserBase):
    UUID: str

    class Config:
        orm_mode = True