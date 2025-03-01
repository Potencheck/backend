from sqlalchemy import Column, String
from app.database import Base


class User(Base):
    __tablename__ = 'users'

    uuid = Column(String, primary_key=True, index=True)
    name = Column(String)
    job_type = Column(String)
    job = Column(String)