import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

from extensions import db
from tasks.prompt_service import PromptService
from tasks.summary_service import SummaryService
from tasks.task_logger import TaskLogger

logger = logging.getLogger(__name__)


@shared_task
def heartbeat():
    """Simple heartbeat task to verify Celery is working."""
    current_time = datetime.now(timezone.utc)
    message = f"💓 HEARTBEAT - {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    print(message)
    logger.info(message)
    return "heartbeat"


@shared_task(name="tasks.scheduled.generate_weekly_summary")
def generate_weekly_summary():
    """Generate weekly summary for all users."""
    return _generate_summary("weekly", 7)


@shared_task(name="tasks.scheduled.generate_monthly_summary")
def generate_monthly_summary():
    """Generate monthly summary for all users."""
    return _generate_summary("monthly", 30)


def _generate_summary(summary_type: str, days: int):
    """Generic summary generation function - DRY implementation"""
    TaskLogger.log_task_start(f"generate_{summary_type}_summary")

    try:
        summary_service = SummaryService()
        current_time = datetime.now(timezone.utc)
        end_date = current_time
        start_date = end_date - timedelta(days=days)

        users = summary_service.get_users_by_summary_type(summary_type)
        print(f"👥 Found {len(users)} users with {summary_type} summaries enabled")

        successful_summaries = 0
        failed_summaries = 0
        skipped_users = 0

        for user in users:
            try:
                TaskLogger.log_user_processing(user.id, user.email, f"{summary_type} summary")

                # Get memories for the period
                memories = summary_service.get_memories_for_period(user.id, start_date, end_date)

                print(
                    f"📝 Found {len(memories)} memories for user {user.id} from "
                    f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                )

                if memories:
                    # Generate summary
                    summary_text = summary_service.generate_summary(memories, start_date, end_date, summary_type)

                    if summary_text:
                        # Save reflection
                        summary_service.save_reflection(user.id, summary_text, summary_type, start_date, end_date)

                        TaskLogger.log_user_success(
                            user.id,
                            user.email,
                            f"{summary_type} summary",
                            period=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                        )
                        successful_summaries += 1
                    else:
                        print(f"⚠️ No summary generated for user {user.id}")
                        skipped_users += 1
                else:
                    print(f"⚠️ No memories found for user {user.id} in the past {days} days")
                    skipped_users += 1

            except Exception as e:
                TaskLogger.log_user_error(user.id, user.email, f"{summary_type} summary", str(e))
                db.session.rollback()
                failed_summaries += 1

        result = (
            f"{summary_type.capitalize()} summaries generated successfully - "
            f"Successful: {successful_summaries}, Failed: {failed_summaries}, Skipped: {skipped_users}"
        )
        TaskLogger.log_task_success(f"generate_{summary_type}_summary", result)
        return result

    except Exception as e:
        TaskLogger.log_task_error(f"generate_{summary_type}_summary", str(e))
        return f"Error generating {summary_type} summaries: {str(e)}"


@shared_task(name="tasks.scheduled.send_daily_prompt")
def send_daily_prompt():
    """Send daily prompt for all users."""
    TaskLogger.log_task_start("send_daily_prompt")

    try:
        prompt_service = PromptService()
        result = prompt_service.create_daily_prompts_for_all_users()

        if result["success"]:
            TaskLogger.log_task_success(
                "send_daily_prompt",
                result=f"Created {result['total_prompts_generated']} prompts",
                successful=result["successful_prompts"],
                failed=result["failed_prompts"],
            )
            return (
                f"Daily prompts created for {result['successful_prompts']} users, "
                f"Total prompts: {result['total_prompts_generated']}, "
                f"Failed: {result['failed_prompts']}"
            )
        else:
            TaskLogger.log_task_error("send_daily_prompt", result["message"])
            return result["message"]

    except Exception as e:
        TaskLogger.log_task_error("send_daily_prompt", str(e))
        return f"Error setting daily prompt: {str(e)}"
