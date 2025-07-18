import logging
from datetime import datetime, timedelta, timezone

from models import Memory, Notification, User

logger = logging.getLogger(__name__)


def check_inactive_users_and_create_reminders():
    """Check for inactive users and create weekly check-in reminders."""
    try:
        # Get all active users with notifications enabled
        users = User.query.filter_by(is_active=True, notifications_enabled=True).all()

        inactive_users = []
        reminders_created = 0

        for user in users:
            # Check if user has been inactive for 7 days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

            recent_memory = Memory.query.filter_by(user_id=user.id).filter(Memory.created_at >= cutoff_date).first()

            if not recent_memory:
                inactive_users.append(user.id)

                # Check if we already have a recent weekly check-in reminder
                recent_reminder = (
                    Notification.query.filter_by(user_id=user.id, notification_type="weekly_checkin")
                    .filter(Notification.created_at >= cutoff_date)
                    .first()
                )

                if not recent_reminder:
                    # Create weekly check-in reminder
                    Notification.create_weekly_checkin_reminder(
                        user_id=user.id,
                        scheduled_for=datetime.now(timezone.utc),
                    )
                    reminders_created += 1
                    logger.info(f"Created weekly check-in reminder for inactive user {user.id}")

        logger.info(
            f"Notification check completed: {len(inactive_users)} inactive users found, "
            f"{reminders_created} reminders created",
        )
        return {
            "inactive_users_count": len(inactive_users),
            "reminders_created": reminders_created,
            "inactive_user_ids": inactive_users,
        }

    except Exception as e:
        logger.error(f"Error checking inactive users: {e}")
        raise
