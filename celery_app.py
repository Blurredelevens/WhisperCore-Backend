from app import create_app
from extensions import configure_celery

# Create Flask app and configure Celery
flask_app = create_app()
configure_celery(flask_app)
