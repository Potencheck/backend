import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB 연결 정보 구성
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
DB_NAME = os.getenv("MONGO_DB", "poten_check_db")

# 인증 정보가 있는 연결 문자열 생성
if MONGO_USER and MONGO_PASSWORD:
    MONGO_DETAILS = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}"
else:
    MONGO_DETAILS = f"mongodb://{MONGO_HOST}:{MONGO_PORT}"

# Motor 클라이언트 생성 및 데이터베이스 선택
client = AsyncIOMotorClient(MONGO_DETAILS)
db = client[DB_NAME]

def get_db():
    return db

def get_collection(collection_name: str):
    return db[collection_name]