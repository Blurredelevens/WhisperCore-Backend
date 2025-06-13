from flask_migrate import Migrate
from app import create_app, db

flask_app = create_app()
migrate = Migrate(flask_app, db)
celery_app = flask_app.extensions["celery"]
