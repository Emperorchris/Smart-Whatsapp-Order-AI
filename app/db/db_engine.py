from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import Config
from app.db.base import Base

engine = create_engine(Config.CONNECTION_STRING, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    return engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()