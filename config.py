import os
import secrets
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Use PostgreSQL on Render (DATABASE_URL env var), SQLite locally
    database_url = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "hotel.db")}'
    # Render gives postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API chính thức hoặc server local tương thích OpenAI.
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '').strip()
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', '').strip() or 'https://api.openai.com/v1'
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', '').strip()
    OPENAI_MAX_OUTPUT_TOKENS = os.environ.get('OPENAI_MAX_OUTPUT_TOKENS', '').strip()
    # Bỏ trống để tự chọn: OpenAI dùng max_completion_tokens, local dùng max_tokens.
    OPENAI_TOKEN_PARAMETER = os.environ.get('OPENAI_TOKEN_PARAMETER', '').strip()
