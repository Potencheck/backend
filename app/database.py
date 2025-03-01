import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB 연결 문자열을 .env에서 가져오거나 기본값 사용
MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "poten_check_db")

# Motor 클라이언트 생성 및 데이터베이스 선택
client = AsyncIOMotorClient(MONGO_DETAILS)
db = client[DB_NAME]

def get_db():
    return db

def get_collection(collection_name: str):
    return db[collection_name]