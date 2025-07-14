from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Dict

from environs import Env


class Config(ABC):
    @property
    @abstractmethod
    def FLASK_APP(self) -> str:
        pass

    @property
    @abstractmethod
    def FLASK_ENV(self) -> str:
        pass

    @property
    @abstractmethod
    def SECRET_KEY(self) -> str:
        pass

    @property
    @abstractmethod
    def JWT_SECRET_KEY(self) -> str:
        pass

    @property
    @abstractmethod
    def JWT_ACCESS_TOKEN_EXPIRES(self) -> timedelta:
        pass

    @property
    @abstractmethod
    def JWT_REFRESH_TOKEN_EXPIRES(self) -> timedelta:
        pass

    @property
    @abstractmethod
    def DATABASE_URL(self) -> str:
        pass

    @property
    @abstractmethod
    def REDIS_URL(self) -> str:
        pass

    @property
    @abstractmethod
    def CORS_ORIGINS(self) -> list:
        pass

    @property
    @abstractmethod
    def DEBUG(self) -> bool:
        pass

    @property
    @abstractmethod
    def BEAT_SCHEDULE(self) -> int:
        pass

    @property
    @abstractmethod
    def WEEKLY_SUMMARY_SCHEDULE(self) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def MONTHLY_SUMMARY_SCHEDULE(self) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def DAILY_PROMPT_SCHEDULE(self) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def MEMORY_MAX_LENGTH(self) -> int:
        pass

    @property
    @abstractmethod
    def MEMORY_ENCRYPTION_KEY(self) -> str:
        pass

    @property
    @abstractmethod
    def LLM_API_URL(self) -> str:
        pass

    def get_config(self) -> Dict[str, Any]:
        print("Loaded MEMORY_ENCRYPTION_KEY:", self.MEMORY_ENCRYPTION_KEY)
        return {
            "FLASK_APP": self.FLASK_APP,
            "FLASK_ENV": self.FLASK_ENV,
            "SECRET_KEY": self.SECRET_KEY,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
            "JWT_ACCESS_TOKEN_EXPIRES": self.JWT_ACCESS_TOKEN_EXPIRES,
            "JWT_REFRESH_TOKEN_EXPIRES": self.JWT_REFRESH_TOKEN_EXPIRES,
            "SQLALCHEMY_DATABASE_URI": self.DATABASE_URL,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "CORS_ORIGINS": self.CORS_ORIGINS,
            "DEBUG": self.DEBUG,
            "REDIS_URL": self.REDIS_URL,
            "MEMORY_MAX_LENGTH": self.MEMORY_MAX_LENGTH,
            "MEMORY_ENCRYPTION_KEY": self.MEMORY_ENCRYPTION_KEY,
            # Celery configuration using new format
            "broker_url": self.CELERY_BROKER_URL,
            "result_backend": self.CELERY_RESULT_BACKEND,
            "task_ignore_result": self.TASK_IGNORE_RESULT,
            "broker_connection_retry_on_startup": True,
            "beat_schedule": {
                "heartbeat": {
                    "task": "tasks.scheduled.heartbeat",
                    "schedule": 120.0,  # 2 minutes
                },
                "generate_weekly_summary": {
                    "task": "tasks.scheduled.generate_weekly_summary",
                    "schedule": 120.0,  # 2 minutes for testing (weekly)
                },
                "generate_monthly_summary": {
                    "task": "tasks.scheduled.generate_monthly_summary",
                    "schedule": 180.0,  # 3 minutes for testing (monthly)
                },
                "send_daily_prompt": {
                    "task": "tasks.scheduled.send_daily_prompt",
                    "schedule": 240.0,  # 4 minutes for testing (daily)
                },
            },
        }


class EnvConfig(Config):
    def __init__(self):
        self._env = Env()
        self._env.read_env()

    @property
    def FLASK_APP(self) -> str:
        return self._env.str("FLASK_APP", "app.py")

    @property
    def FLASK_ENV(self) -> str:
        return self._env.str("FLASK_ENV", "development")

    @property
    def SECRET_KEY(self) -> str:
        return self._env.str("SECRET_KEY")

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self._env.str("JWT_SECRET_KEY")

    @property
    def JWT_ACCESS_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(days=1)

    @property
    def JWT_REFRESH_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(days=30)

    @property
    def DATABASE_URL(self) -> str:
        return self._env.str("DATABASE_URL")

    @property
    def REDIS_URL(self) -> str:
        return self._env.str("REDIS_URL")

    @property
    def CORS_ORIGINS(self) -> list:
        return self._env.list("CORS_ORIGINS")

    @property
    def DEBUG(self) -> bool:
        return self._env.bool("DEBUG", False)

    @property
    def BEAT_SCHEDULE(self) -> int:
        return self._env.int("BEAT_SCHEDULE", 0)

    @property
    def WEEKLY_SUMMARY_SCHEDULE(self) -> Dict[str, Any]:
        return {"task": "tasks.scheduled.generate_weekly_summary", "schedule": 120.0}  # 2 minutes for testing

    @property
    def MONTHLY_SUMMARY_SCHEDULE(self) -> Dict[str, Any]:
        return {"task": "tasks.scheduled.generate_monthly_summary", "schedule": 180.0}  # 3 minutes for testing

    @property
    def DAILY_PROMPT_SCHEDULE(self) -> Dict[str, Any]:
        return {"task": "tasks.scheduled.send_daily_prompt", "schedule": 240.0}  # 4 minutes for testing

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self._env.str("CELERY_BROKER_URL", "redis://redis:6379/0")

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self._env.str("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

    @property
    def TASK_IGNORE_RESULT(self) -> bool:
        return self._env.bool("TASK_IGNORE_RESULT", True)

    @property
    def MEMORY_MAX_LENGTH(self) -> int:
        return self._env.int("MEMORY_MAX_LENGTH", 1000)

    @property
    def MEMORY_ENCRYPTION_KEY(self) -> str:
        return self._env.str("MEMORY_ENCRYPTION_KEY", "PRE_3J4rxzhDJyjQ_L3Q1Sx8OmAD85CGvrJRToF-rrA=")

    @property
    def LLM_API_URL(self) -> str:
        return self._env.str("LLM_API_URL", "http://localhost:8000")


class AppConfig(Config):
    def __init__(self, current_app):
        self._config = current_app.config

    @property
    def FLASK_APP(self) -> str:
        return self._config.get("FLASK_APP", "app.py")

    @property
    def FLASK_ENV(self) -> str:
        return self._config.get("FLASK_ENV", "development")

    @property
    def SECRET_KEY(self) -> str:
        return self._config.get("SECRET_KEY")

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self._config.get("JWT_SECRET_KEY")

    @property
    def JWT_ACCESS_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(days=1)

    @property
    def JWT_REFRESH_TOKEN_EXPIRES(self) -> timedelta:
        return timedelta(days=30)

    @property
    def DATABASE_URL(self) -> str:
        return self._config.get("DATABASE_URL")

    @property
    def REDIS_URL(self) -> str:
        return self._config.get("REDIS_URL")

    @property
    def CORS_ORIGINS(self) -> list:
        return self._config.get("CORS_ORIGINS", [])

    @property
    def DEBUG(self) -> bool:
        return self._config.get("DEBUG", False)

    @property
    def BEAT_SCHEDULE(self) -> int:
        return self._config.get("BEAT_SCHEDULE", 0)

    @property
    def WEEKLY_SUMMARY_SCHEDULE(self) -> Dict[str, Any]:
        return {"task": "tasks.scheduled.generate_weekly_summary", "schedule": 120.0}  # 2 minutes for testing

    @property
    def MONTHLY_SUMMARY_SCHEDULE(self) -> Dict[str, Any]:
        return {"task": "tasks.scheduled.generate_monthly_summary", "schedule": 180.0}  # 3 minutes for testing

    @property
    def DAILY_PROMPT_SCHEDULE(self) -> Dict[str, Any]:
        return {"task": "tasks.scheduled.send_daily_prompt", "schedule": 240.0}  # 4 minutes for testing

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self._config.get("REDIS_URL", "redis://redis:6379/0")

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self._config.get("REDIS_URL", "redis://redis:6379/0")

    @property
    def TASK_IGNORE_RESULT(self) -> bool:
        return self._config.get("TASK_IGNORE_RESULT", True)

    @property
    def MEMORY_MAX_LENGTH(self) -> int:
        return self._config.get("MEMORY_MAX_LENGTH", 1000)

    @property
    def MEMORY_ENCRYPTION_KEY(self) -> str:
        return self._config.get("MEMORY_ENCRYPTION_KEY", "PRE_3J4rxzhDJyjQ_L3Q1Sx8OmAD85CGvrJRToF-rrA=")

    @property
    def LLM_API_URL(self) -> str:
        return self._config.get("LLM_API_URL", "http://localhost:8000")
