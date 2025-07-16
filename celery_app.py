from app import create_app
from extensions import celery

# Create Flask app
flask_app = create_app()


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


# Configure Celery with Flask app
configure_celery(flask_app)

# Expose the celery app for Celery CLI
# This is what `-A celery_app.celery` expects!
celery = celery
