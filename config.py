"""Configuration management for LinkedIn Job Automation System."""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="LinkedIn Job Automation", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    
    # Google Sheets
    google_sheets_credentials_path: str = Field(
        default="config/credentials.json", 
        env="GOOGLE_SHEETS_CREDENTIALS_PATH"
    )
    google_sheets_id: Optional[str] = Field(default=None, env="GOOGLE_SHEETS_ID")
    
    # LinkedIn (Optional)
    linkedin_email: Optional[str] = Field(default=None, env="LINKEDIN_EMAIL")
    linkedin_password: Optional[str] = Field(default=None, env="LINKEDIN_PASSWORD")
    linkedin_url: str = Field(default="https://www.linkedin.com/login", env="LINKEDIN_URL")
    
    # Groq
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", env="GROQ_MODEL")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./linkedin_jobs.db", 
        env="DATABASE_URL"
    )
    
    # Search Configuration
    default_location: str = Field(default="United States", env="DEFAULT_LOCATION")
    default_job_type: str = Field(default="full-time", env="DEFAULT_JOB_TYPE")
    max_results_per_search: int = Field(default=50, env="MAX_RESULTS_PER_SEARCH")
    search_delay_seconds: int = Field(default=5, env="SEARCH_DELAY_SECONDS")
    
    # Resume Configuration
    resume_file_path: Optional[str] = Field(default=None, env="RESUME_FILE_PATH")
    user_skills: str = Field(default="", env="USER_SKILLS")
    
    # Browser Configuration
    browser_headless: bool = Field(default=False, env="BROWSER_HEADLESS")
    browser_timeout: int = Field(default=30000, env="BROWSER_TIMEOUT")
    
    @property
    def skills_list(self) -> List[str]:
        """Get skills as a list."""
        if isinstance(self.user_skills, str) and self.user_skills:
            return [skill.strip() for skill in self.user_skills.split(",") if skill.strip()]
        return []
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


# Create global settings instance
settings = Settings()

# Project paths
PROJECT_ROOT = Path(__file__).parent
LOGS_DIR = PROJECT_ROOT / "logs"
STATIC_DIR = PROJECT_ROOT / "static"

# Create necessary directories
LOGS_DIR.mkdir(exist_ok=True)

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": settings.log_level,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "app.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": settings.log_level,
        },
    },
    "root": {
        "level": settings.log_level,
        "handlers": ["console", "file"],
    },
}