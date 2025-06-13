from celery import Celery, Task
from celery.schedules import timedelta

from config import AppConfig


def make_schedule(config):
    return {
        "heartbeat": {
            "task": "tasks.scheduled.heartbeat",
            "schedule": timedelta(seconds=config.BEAT_SCHEDULE),
        },
    }


def get_config(app):
    app_config = AppConfig(app)
    config = app_config.CELERY
    config["beat_schedule"] = make_schedule(app_config)
    return config


def celery_init_app(app):
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(get_config(app))
    celery_app.set_default()

    app.extensions["celery"] = celery_app

    return celery_app
