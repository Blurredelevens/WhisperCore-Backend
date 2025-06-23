from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_redis import FlaskRedis
from celery import Celery

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
redis_client = FlaskRedis()

# Initialize Celery
celery = Celery(
    'whisper_core',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0',
    include=['tasks.reflection', 'tasks.maintenance', 'tasks.query']
)

def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    redis_client.init_app(app)
    
    # Configure Celery
    celery.conf.update(app.config)