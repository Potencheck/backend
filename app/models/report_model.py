from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class UserModel(BaseModel):
    name: str
    job_type: str
    job: str

class TrendJDModel(BaseModel):
    name: str
    keyword: int

class PersonalSkillModel(BaseModel):
    skill: str
    description: str

class DocumentModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="id")
    user: UserModel
    career_fitness: int
    trend_jd: List[TrendJDModel]
    trend_skill: List[str]
    my_trend_skill: List[str]
    personal_skill: List[PersonalSkillModel]
    ai_summary: str
    ai_review: str

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True