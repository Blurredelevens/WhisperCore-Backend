from datetime import datetime, timezone

from extensions import db


class Notification(db.Model):
    """Notification model for user notifications and reminders."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Notification content
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # Notification type and status
    notification_type = db.Column(db.String(50), nullable=False, default="reminder")  # reminder, summary, etc.
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_sent = db.Column(db.Boolean, default=False, nullable=False)

    # Scheduling
    scheduled_for = db.Column(db.DateTime, nullable=True)  # When to send the notification
    sent_at = db.Column(db.DateTime, nullable=True)  # When it was actually sent

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", backref="notifications")

    def __repr__(self):
        return f"<Notification {self.id} for user {self.user_id}>"

    def to_dict(self):
        """Convert notification object to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "is_sent": self.is_sent,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.updated_at = datetime.now(timezone.utc)

    def mark_as_sent(self):
        """Mark notification as sent."""
        self.is_sent = True
        self.sent_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def save(self):
        """Save the notification to the database."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Delete the notification from the database."""
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_unread_notifications(user_id, limit=10):
        """Get unread notifications for a user."""
        return (
            Notification.query.filter_by(user_id=user_id, is_read=False)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_pending_notifications():
        """Get notifications that are scheduled to be sent."""
        now = datetime.now(timezone.utc)
        return (
            Notification.query.filter(Notification.scheduled_for <= now, Notification.is_sent.is_(False))
            .order_by(Notification.scheduled_for.asc())
            .all()
        )

    @staticmethod
    def create_weekly_checkin_reminder(user_id, scheduled_for=None):
        """Create a weekly check-in reminder notification."""
        if scheduled_for is None:
            scheduled_for = datetime.now(timezone.utc)

        notification = Notification(
            user_id=user_id,
            title="Weekly Check-in Reminder",
            message=(
                "Hey there! It's been a while since your last reflection. "
                "How about taking a moment to check in with yourself?"
            ),
            notification_type="weekly_checkin",
            scheduled_for=scheduled_for,
        )

        notification.save()
        return notification

    @staticmethod
    def get_user_notification_count(user_id):
        """Get count of unread notifications for a user."""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
