from celery import Celery
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
redis_client = FlaskRedis()

# Initialize Celerys
celery = Celery("whisper_core", include=["tasks.scheduled"])


def configure_celery(app):
    """Configure Celery with Flask app config"""
    # Configure Celery with Flask app config
    celery.conf.update(app.config)

    # Set beat schedule from Flask config
    if "beat_schedule" in app.config:
        celery.conf.beat_schedule = app.config["beat_schedule"]
        print(f"✅ Celery beat schedule configured from Flask: {len(app.config['beat_schedule'])} tasks")
        for task_name, task_config in app.config["beat_schedule"].items():
            print(f"  📅 {task_name}: {task_config['schedule']}s")

    # Register Celery app with Flask extensions
    app.extensions["celery"] = celery

    # Push Flask app context for Celery tasks
    app.app_context().push()
    print("✅ Flask app context pushed for Celery tasks")


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    redis_client.init_app(app)

    limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/1", default_limits=[])
    limiter.init_app(app)

    # Configure Celery
    configure_celery(app)
