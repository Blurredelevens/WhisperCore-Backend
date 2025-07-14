import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from extensions import db
from models.memory import Memory
from models.prompt import Prompt
from models.reflection import Reflection
from models.user import User


# Remove test.db before the test session starts
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    db_path = os.path.join(os.path.dirname(__file__), "..", "test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    yield
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test session."""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Use test configuration
    from tests.config import EnvTestConfig

    app = create_app(config_class=EnvTestConfig)
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret-key",
            "JWT_SECRET_KEY": "test-jwt-secret-key",
            "WTF_CSRF_ENABLED": False,
        },
    )

    with app.app_context():
        # Create all tables
        db.create_all()
        yield app
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """Create a fresh database session for each test."""
    with app.app_context():
        # Create a new session for this test
        session = db.session
        yield session
        # Rollback any changes made during the test
        session.rollback()
        # Clear all data from tables to ensure isolation
        try:
            for table in reversed(db.metadata.sorted_tables):
                session.execute(table.delete())
            session.commit()
        except Exception:
            # If tables don't exist yet, just rollback
            session.rollback()


@pytest.fixture
def user(db_session):
    """Create a test user."""
    # Check if user already exists
    existing_user = db_session.query(User).filter_by(email="test@example.com").first()
    if existing_user:
        return existing_user

    user = User(email="test@example.com", first_name="Test", last_name="User", is_active=True, email_verified=True)
    user.set_password("Testpassword123!")
    user.set_passphrase("testpassphrase123")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    """Create a test admin user."""
    # Check if admin user already exists
    existing_admin = db_session.query(User).filter_by(email="admin@example.com").first()
    if existing_admin:
        return existing_admin

    user = User(
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_active=True,
        email_verified=True,
        is_admin=True,
    )
    user.set_password("Adminpassword123!")
    user.set_passphrase("adminpassphrase123")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def inactive_user(db_session):
    """Create an inactive test user."""
    # Check if inactive user already exists
    existing_user = db_session.query(User).filter_by(email="inactive@example.com").first()
    if existing_user:
        return existing_user

    user = User(
        email="inactive@example.com",
        first_name="Inactive",
        last_name="User",
        is_active=False,
        email_verified=True,
    )
    user.set_password("Testpassword123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def locked_user(db_session):
    """Create a locked test user."""
    # Check if locked user already exists
    existing_user = db_session.query(User).filter_by(email="locked@example.com").first()
    if existing_user:
        return existing_user

    user = User(
        email="locked@example.com",
        first_name="Locked",
        last_name="User",
        is_active=True,
        email_verified=True,
        failed_login_attempts=5,
        locked_until=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    user.set_password("Testpassword123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def memory(db_session, user):
    """Create a test memory."""
    memory = Memory(user_id=user.id, chat_id="test-chat-123")
    memory.set_content("This is a test memory content.", user.encryption_key.encode())
    db_session.add(memory)
    db_session.commit()
    return memory


@pytest.fixture
def reflection(db_session, user):
    """Create a test reflection."""
    reflection = Reflection(
        user_id=user.id,
        content="This is a test reflection content.",
        reflection_type="weekly",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
    )
    db_session.add(reflection)
    db_session.commit()
    return reflection


@pytest.fixture
def prompt(db_session, user):
    """Create a test prompt."""
    prompt = Prompt(text="What are your thoughts on today?", is_active=True, user_id=user.id)
    db_session.add(prompt)
    db_session.commit()
    return prompt


@pytest.fixture
def access_token(user):
    """Create an access token for the test user."""
    return create_access_token(identity=str(user.id))


@pytest.fixture
def auth_headers(access_token):
    """Create authentication headers."""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_access_token(admin_user):
    """Create an access token for the admin user."""
    return create_access_token(identity=str(admin_user.id))


@pytest.fixture
def admin_auth_headers(admin_access_token):
    """Create authentication headers for admin."""
    return {"Authorization": f"Bearer {admin_access_token}"}


@pytest.fixture
def mock_celery(monkeypatch):
    """Mock Celery for testing."""

    class MockCelery:
        def send_task(self, task_name, args=None, kwargs=None):
            return type("MockTask", (), {"id": "mock-task-id"})()

    monkeypatch.setattr("extensions.celery", MockCelery())


@pytest.fixture
def mock_llm_client(monkeypatch):
    """Mock LLM client for testing."""

    class MockLLMClient:
        def generate_with_long_polling(self, prompt, model="llama3:8b", max_retries=3, retry_delay=1.0):
            return "Mock LLM response"

        def generate_text(self, prompt, model="llama3:8b", stream=False):
            from datetime import datetime, timezone

            from schemas.llm import LLMGenerateResponse

            return LLMGenerateResponse(
                model=model,
                created_at=datetime.now(timezone.utc),
                response="Mock LLM response",
                done=True,
            )

    monkeypatch.setattr("services.llm_client.get_llm_client", lambda: MockLLMClient())


@pytest.fixture
def mock_voice_service(monkeypatch):
    """Mock voice service for testing."""

    class MockVoiceService:
        def validate_audio_format(self, format):
            return True

        def base64_audio_to_text(self, audio_data, format):
            return {"success": True, "text": "Mock transcribed text", "method": "mock"}

    monkeypatch.setattr("services.voice_service.VoiceService", MockVoiceService)


@pytest.fixture
def sample_audio_base64():
    """Saample base64 encoded audio for testing."""
    return "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m99OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+9+OWT"  # noqa: E501


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing."""

    class MockRedis:
        def __init__(self):
            self.data = {}

        def set(self, key, value):
            self.data[key] = value

        def get(self, key):
            return self.data.get(key)

        def delete(self, key):
            if key in self.data:
                del self.data[key]

    mock_redis_instance = MockRedis()
    monkeypatch.setattr("extensions.redis_client", mock_redis_instance)
    return mock_redis_instance


@pytest.fixture(autouse=True)
def setup_test_environment(app):
    """Setup test environment variables."""
    os.environ["FLASK_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["GROQ_API_KEY"] = "test-groq-api-key"
