import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    SECRET_KEY = os.getenv("SECRET_KEY")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 3000))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
    CONNECTION_STRING = os.getenv("CONNECTION_STRING")
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token")
    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")