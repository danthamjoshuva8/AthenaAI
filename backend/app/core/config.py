from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    # ==========================================
    # Database
    # ==========================================

    POSTGRES_USER = os.getenv("POSTGRES_USER")

    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    POSTGRES_DB = os.getenv("POSTGRES_DB")

    POSTGRES_HOST = os.getenv("POSTGRES_HOST")

    POSTGRES_PORT = os.getenv("POSTGRES_PORT")

    DATABASE_URL = os.getenv("DATABASE_URL")

    # ==========================================
    # AI
    # ==========================================

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")


settings = Settings()