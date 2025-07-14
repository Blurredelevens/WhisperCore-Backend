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
redis_client = FlaskRedis()

# Initialize Celery
celery = Celery(
    'whisper_core',
    include=[
        'tasks.llm_service',
        'tasks.scheduled'
    ]
)
 



def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    redis_client.init_app(app)
    
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="redis://redis:6379/1",
        default_limits=[]
    )
    limiter.init_app(app)
    
    celery.conf.update(app.config)
    
    # Import tasks after extensions are initialized to avoid circular imports
    import tasks.llm_service
    import tasks.scheduled