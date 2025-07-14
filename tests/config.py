from config import EnvConfig


class EnvTestConfig(EnvConfig):
    @property
    def DEBUG(self):
        return self._env.bool("DEBUG", True)

    @property
    def COMMIT(self):
        return self._env.bool("COMMIT", False)

    @property
    def CREATE_TEST_DATA(self):
        return self._env.bool("CREATE_TEST_DATA", False)

    @property
    def TEMPLATE_API_KEY(self):
        return self._env.str("TEMPLATE_API_KEY", "1234")

    @property
    def DATABASE_URL(self) -> str:
        """Override to use SQLite file for testing."""
        return "sqlite:///test.db"

    @property
    def REDIS_URL(self) -> str:
        """Override to use a mock Redis URL for testing."""
        return "redis://localhost:6379/0"
