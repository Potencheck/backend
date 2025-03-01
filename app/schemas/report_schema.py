from pydantic import BaseModel
from typing import List
from app.schemas.user import UserBase


class TrendJDItem(BaseModel):
    name: str
    keyword: int

class PersonalSkillItem(BaseModel):
    skill: str
    description: str

class CareerInputSchema(BaseModel):
    user: UserBase
    career_fitness: int
    trend_jd: List[TrendJDItem]
    trend_skill: List[str]
    my_trend_skill: List[str]
    personal_skill: List[PersonalSkillItem]
    ai_summary: str
    ai_review: str

class ReportInput(BaseModel):
    user: UserBase
    career_fitness: int
    trend_jd: List[TrendJDItem]
    trend_skill: List[str]
    my_trend_skill: List[str]
    personal_skill: List[PersonalSkillItem]
    ai_summary: str
    ai_review: str

class Report(ReportInput):
    id: str
