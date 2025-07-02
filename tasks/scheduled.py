# tasks/scheduled.py
from celery import shared_task
import time
from tasks.llm_service import LLMService
import logging

logger = logging.getLogger(__name__)

@shared_task
def heartbeat():
    print(f"Heartbeat - {time.ctime()}")
    """Simple heartbeat task to verify Celery is working."""
    return "heartbeat"

@shared_task(name="tasks.scheduled.process_query_task")
def process_query_task(query_data):
    try:
        from app import create_app
        flask_app = create_app()
        with flask_app.app_context():
            llm_service = LLMService()
            
            if isinstance(query_data, dict):
                query = query_data.get("query", "")
            else:
                query = query_data

            result = llm_service.process_query(query)
            logger.info(f"Query task completed successfully")
            return result
    except Exception as e:
        logger.error(f"Error in process_query_task: {str(e)}")
        return f"Error processing query: {str(e)}"
