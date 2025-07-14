import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TaskLogger:
    """Utility for consistent task logging"""

    @staticmethod
    def log_task_start(task_name: str, **kwargs):
        """Log task start with optional parameters"""
        current_time = datetime.now(timezone.utc)
        message = f"🚀 {task_name.upper()}_TASK STARTED - {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        if kwargs:
            message += f" - {kwargs}"
        print(message)
        logger.info(message)

    @staticmethod
    def log_task_success(task_name: str, result: str = None, **kwargs):
        """Log task success with optional result and parameters"""
        current_time = datetime.now(timezone.utc)
        message = f"✅ {task_name.upper()}_TASK COMPLETED - {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        if kwargs:
            message += f" - {kwargs}"
        if result:
            message += f" - Result: {result[:100]}..."
        print(message)
        logger.info(message)

    @staticmethod
    def log_task_error(task_name: str, error: str, **kwargs):
        """Log task error with optional parameters"""
        current_time = datetime.now(timezone.utc)
        message = (
            f"❌ {task_name.upper()}_TASK FAILED - {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')} - Error: {error}"
        )
        if kwargs:
            message += f" - {kwargs}"
        print(message)
        logger.error(message)

    @staticmethod
    def log_user_processing(user_id: int, user_email: str, action: str):
        """Log user processing action"""
        message = f"🔄 Processing {action} for user {user_id} ({user_email})"
        print(message)
        logger.info(message)

    @staticmethod
    def log_user_success(user_id: int, user_email: str, action: str, **kwargs):
        """Log successful user processing"""
        message = f"✅ {action} completed for user {user_id} ({user_email})"
        if kwargs:
            message += f" - {kwargs}"
        print(message)
        logger.info(message)

    @staticmethod
    def log_user_error(user_id: int, user_email: str, action: str, error: str):
        """Log user processing error"""
        message = f"❌ Error processing {action} for user {user_id} ({user_email}): {error}"
        print(message)
        logger.error(message)
