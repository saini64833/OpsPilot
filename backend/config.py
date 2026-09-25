from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://opspilot:opspilot@db:5432/opspilot"
    HUGGINGFACE_TOKEN: str = ""
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "gemini"  # "gemini", "anthropic", or "openai"
    OCR_CONFIDENCE_THRESHOLD: float = 0.6

    class Config:
        env_file = ".env"


settings = Settings()