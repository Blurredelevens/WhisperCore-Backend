import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import Memory, Notification, User

logger = logging.getLogger(__name__)

notification_bp = Blueprint("notification", __name__)


def check_user_inactivity(user_id, days_threshold=7):
    """Check if user has been inactive for the specified number of days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

    # Check for recent memories
    recent_memory = Memory.query.filter_by(user_id=user_id).filter(Memory.created_at >= cutoff_date).first()

    return recent_memory is None


class NotificationAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        """Get user's notifications."""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Check if notifications are enabled
            if not user.notifications_enabled:
                return jsonify(
                    {"success": True, "notifications": [], "unread_count": 0, "message": "Notifications are disabled"},
                )

            # Get query parameters
            limit = request.args.get("limit", 10, type=int)
            unread_only = request.args.get("unread_only", "false").lower() == "true"

            if unread_only:
                notifications = Notification.get_unread_notifications(user_id, limit)
            else:
                notifications = (
                    Notification.query.filter_by(user_id=user_id)
                    .order_by(Notification.created_at.desc())
                    .limit(limit)
                    .all()
                )

            unread_count = Notification.get_user_notification_count(user_id)

            return jsonify(
                {
                    "success": True,
                    "notifications": [notification.to_dict() for notification in notifications],
                    "unread_count": unread_count,
                },
            )

        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return jsonify({"error": f"Failed to get notifications: {str(e)}"}), 500

    def post(self):
        """Create a new notification (for testing or manual creation)."""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400

            required_fields = ["title", "message"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            notification = Notification(
                user_id=user_id,
                title=data["title"],
                message=data["message"],
                notification_type=data.get("notification_type", "reminder"),
                scheduled_for=data.get("scheduled_for"),
            )

            notification.save()

            logger.info(f"Created notification {notification.id} for user {user_id}")

            return jsonify(
                {
                    "success": True,
                    "message": "Notification created successfully",
                    "notification": notification.to_dict(),
                },
            )

        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to create notification: {str(e)}"}), 500


class NotificationDetailAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, notification_id):
        """Get a specific notification."""
        try:
            user_id = get_jwt_identity()

            notification = db.session.get(Notification, notification_id)
            if not notification or notification.user_id != user_id:
                return jsonify({"error": "Notification not found"}), 404

            return jsonify({"success": True, "notification": notification.to_dict()})

        except Exception as e:
            logger.error(f"Error getting notification {notification_id}: {e}")
            return jsonify({"error": f"Failed to get notification: {str(e)}"}), 500

    def put(self, notification_id):
        """Mark notification as read."""
        try:
            user_id = get_jwt_identity()

            notification = db.session.get(Notification, notification_id)
            if not notification or notification.user_id != user_id:
                return jsonify({"error": "Notification not found"}), 404

            notification.mark_as_read()
            db.session.commit()

            logger.info(f"Marked notification {notification_id} as read for user {user_id}")

            return jsonify(
                {"success": True, "message": "Notification marked as read", "notification": notification.to_dict()},
            )

        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to mark notification as read: {str(e)}"}), 500

    def delete(self, notification_id):
        """Delete a notification."""
        try:
            user_id = get_jwt_identity()

            notification = db.session.get(Notification, notification_id)
            if not notification or notification.user_id != user_id:
                return jsonify({"error": "Notification not found"}), 404

            notification.delete()

            logger.info(f"Deleted notification {notification_id} for user {user_id}")

            return jsonify({"success": True, "message": "Notification deleted successfully"})

        except Exception as e:
            logger.error(f"Error deleting notification {notification_id}: {e}")
            return jsonify({"error": f"Failed to delete notification: {str(e)}"}), 500


class NotificationBulkAPI(MethodView):
    decorators = [jwt_required()]

    def put(self):
        """Mark multiple notifications as read."""
        try:
            user_id = get_jwt_identity()

            data = request.get_json()
            if not data or "notification_ids" not in data:
                return jsonify({"error": "notification_ids field is required"}), 400

            notification_ids = data["notification_ids"]
            if not isinstance(notification_ids, list):
                return jsonify({"error": "notification_ids must be a list"}), 400

            # Get notifications that belong to the user
            notifications = Notification.query.filter(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
            ).all()

            for notification in notifications:
                notification.mark_as_read()

            db.session.commit()

            logger.info(f"Marked {len(notifications)} notifications as read for user {user_id}")

            return jsonify({"success": True, "message": f"Marked {len(notifications)} notifications as read"})

        except Exception as e:
            logger.error(f"Error marking notifications as read: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to mark notifications as read: {str(e)}"}), 500


class WeeklyCheckinAPI(MethodView):
    decorators = [jwt_required()]

    def post(self):
        """Create a weekly check-in reminder for the current user."""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Check if notifications are enabled
            if not user.notifications_enabled:
                return jsonify({"success": False, "message": "Notifications are disabled for this user"}), 400

            # Check if user has been inactive
            if not check_user_inactivity(user_id, days_threshold=7):
                return (
                    jsonify(
                        {"success": False, "message": "User has been active recently, no check-in reminder needed"},
                    ),
                    400,
                )

            # Schedule the reminder for now (or you can schedule it for a specific time)
            scheduled_for = datetime.now(timezone.utc)

            notification = Notification.create_weekly_checkin_reminder(user_id=user_id, scheduled_for=scheduled_for)

            logger.info(f"Created weekly check-in reminder for user {user_id}")

            return jsonify(
                {
                    "success": True,
                    "message": "Weekly check-in reminder created successfully",
                    "notification": notification.to_dict(),
                },
            )

        except Exception as e:
            logger.error(f"Error creating weekly check-in reminder: {e}")
            return jsonify({"error": f"Failed to create weekly check-in reminder: {str(e)}"}), 500


# Register the blueprints
notification_bp.add_url_rule(
    "/",
    view_func=NotificationAPI.as_view("notifications"),
    methods=["GET", "POST"],
)

notification_bp.add_url_rule(
    "/<int:notification_id>",
    view_func=NotificationDetailAPI.as_view("notification_detail"),
    methods=["GET", "PUT", "DELETE"],
)

notification_bp.add_url_rule(
    "/bulk/read",
    view_func=NotificationBulkAPI.as_view("notification_bulk"),
    methods=["PUT"],
)

notification_bp.add_url_rule(
    "/weekly-checkin",
    view_func=WeeklyCheckinAPI.as_view("weekly_checkin"),
    methods=["POST"],
)
