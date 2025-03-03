from sqlmodel import create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

CLOUD_SQL_HOST = os.getenv("CLOUD_SQL_HOST")
CLOUD_SQL_USER = os.getenv("CLOUD_SQL_USER")
CLOUD_SQL_PASSWORD = os.getenv("CLOUD_SQL_PASSWORD")
CLOUD_SQL_DATABASE = os.getenv("CLOUD_SQL_DATABASE")

DATABASE_URL = f"mysql+pymysql://{CLOUD_SQL_USER}:{CLOUD_SQL_PASSWORD}@{CLOUD_SQL_HOST}/{CLOUD_SQL_DATABASE}"

engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session 