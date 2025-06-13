# tasks/scheduled.py
from celery import shared_task
import time

@shared_task
def heartbeat():
    print(f"Heartbeat - {time.ctime()}")
    """Simple heartbeat task to verify Celery is working."""
    return "heartbeat"
