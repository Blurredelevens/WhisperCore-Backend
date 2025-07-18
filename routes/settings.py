import logging

from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import User

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings", __name__)


class SettingsAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        """Get user settings."""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            return jsonify(
                {
                    "success": True,
                    "settings": {
                        "notifications_enabled": user.notifications_enabled,
                        "chatbot_name": user.chatbot_name,
                        "tone": user.tone,
                        "weekly_summary_enabled": user.weekly_summary_enabled,
                        "monthly_summary_enabled": user.monthly_summary_enabled,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return jsonify({"error": f"Failed to get settings: {str(e)}"}), 500

    def put(self):
        """Update user settings."""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400

            # Update notification settings
            if "notifications_enabled" in data:
                user.notifications_enabled = bool(data["notifications_enabled"])

            # Update chatbot name
            if "chatbot_name" in data:
                chatbot_name = data["chatbot_name"].strip()
                if not chatbot_name:
                    return jsonify({"error": "Chatbot name cannot be empty"}), 400
                if len(chatbot_name) > 50:
                    return jsonify({"error": "Chatbot name must be 50 characters or less"}), 400
                user.chatbot_name = chatbot_name

            # Update tone
            if "tone" in data:
                tone = data["tone"].strip()
                if not tone:
                    return jsonify({"error": "Tone cannot be empty"}), 400

                user.tone = tone

            # Update summary settings
            if "weekly_summary_enabled" in data:
                user.weekly_summary_enabled = bool(data["weekly_summary_enabled"])

            if "monthly_summary_enabled" in data:
                user.monthly_summary_enabled = bool(data["monthly_summary_enabled"])

            db.session.commit()

            logger.info(f"User {user_id} updated settings: {data}")

            return jsonify(
                {
                    "success": True,
                    "message": "Settings updated successfully",
                    "settings": {
                        "notifications_enabled": user.notifications_enabled,
                        "chatbot_name": user.chatbot_name,
                        "tone": user.tone,
                        "weekly_summary_enabled": user.weekly_summary_enabled,
                        "monthly_summary_enabled": user.monthly_summary_enabled,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to update settings: {str(e)}"}), 500


class NotificationToggleAPI(MethodView):
    decorators = [jwt_required()]

    def post(self):
        """Toggle notification settings."""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            data = request.get_json()
            if not data or "notifications_enabled" not in data:
                return jsonify({"error": "notifications_enabled field is required"}), 400

            user.notifications_enabled = bool(data["notifications_enabled"])
            db.session.commit()

            logger.info(f"User {user_id} toggled notifications to: {user.notifications_enabled}")

            return jsonify(
                {
                    "success": True,
                    "message": f"Notifications {'enabled' if user.notifications_enabled else 'disabled'} successfully",
                    "notifications_enabled": user.notifications_enabled,
                },
            )

        except Exception as e:
            logger.error(f"Error toggling notifications: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to toggle notifications: {str(e)}"}), 500


# Register the blueprints
settings_bp.add_url_rule(
    "",
    view_func=SettingsAPI.as_view("settings"),
    methods=["GET", "PUT"],
)

settings_bp.add_url_rule(
    "/notifications/toggle",
    view_func=NotificationToggleAPI.as_view("notification_toggle"),
    methods=["POST"],
)
