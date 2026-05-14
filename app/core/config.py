import os
from dotenv import load_dotenv
import cloudinary

load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_LLM_MODEL = os.getenv("ANTHROPIC_LLM_MODEL", "claude-haiku-4-5")
    OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-5.0")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
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
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "NGN")
    # CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")
    # CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    # CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    # CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    
    
    
class CloudinaryConfig:
    CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    
cloudinary.config(
    cloudinary_url=CloudinaryConfig.CLOUDINARY_URL
)
