import json
import logging
from datetime import datetime
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import User
from services.export_service import ExportService

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


class AITonesAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        """Get available AI tones with descriptions from database."""
        try:
            user_id = get_jwt_identity()
            tones = User.get_ai_tones(user_id)

            return jsonify(
                {
                    "success": True,
                    "tones": tones,
                },
            )

        except Exception as e:
            logger.error(f"Error getting AI tones: {e}")
            return jsonify({"error": f"Failed to get AI tones: {str(e)}"}), 500


class ExportFormatsAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        """Get available export formats."""
        try:
            formats = ExportService.get_export_formats()
            return jsonify(
                {
                    "success": True,
                    "formats": formats,
                },
            )

        except Exception as e:
            logger.error(f"Error getting export formats: {e}")
            return jsonify({"error": f"Failed to get export formats: {str(e)}"}), 500


class DataExportAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, format_type):
        """Export user data in the specified format."""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Validate format
            available_formats = [fmt["format"] for fmt in ExportService.get_export_formats()]
            if format_type not in available_formats:
                return jsonify({"error": f"Unsupported format. Available formats: {', '.join(available_formats)}"}), 400

            # Get user's encryption key
            encryption_key = user.encryption_key.encode()

            # Generate export data
            if format_type == "json":
                export_data = ExportService.export_user_memories_json(user_id, encryption_key)
                content = json.dumps(export_data, indent=2, ensure_ascii=False)
                filename = f"whispercore_memories_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                mimetype = "application/json"
            elif format_type == "txt":
                content = ExportService.export_user_memories_txt(user_id, encryption_key)
                filename = f"whispercore_memories_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
                mimetype = "text/plain"
            else:
                return jsonify({"error": "Unsupported format"}), 400

            # Create file-like object
            file_obj = BytesIO(content.encode("utf-8"))
            file_obj.seek(0)

            logger.info(f"User {user_id} exported memories in {format_type} format")

            return send_file(file_obj, mimetype=mimetype, as_attachment=True, download_name=filename)

        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return jsonify({"error": f"Failed to export data: {str(e)}"}), 500


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

settings_bp.add_url_rule(
    "/ai-tones",
    view_func=AITonesAPI.as_view("ai_tones"),
    methods=["GET"],
)


settings_bp.add_url_rule(
    "/export/formats",
    view_func=ExportFormatsAPI.as_view("export_formats"),
    methods=["GET"],
)

settings_bp.add_url_rule(
    "/export/<format_type>",
    view_func=DataExportAPI.as_view("data_export"),
    methods=["GET"],
)
