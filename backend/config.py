import os

# Manual .env loader to avoid external dependencies
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

load_env()

class Settings:
    PROJECT_NAME: str = "OmniFinance Autonomous Banking Sandbox"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    HUGGING_FACE_TOKEN: str = os.getenv("HUGGING_FACE_TOKEN", "")
    DATABASE_PATH: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "omnifinance.db"
    )
    APP_PORT: int = int(os.getenv("PORT", "7860"))

settings = Settings()

