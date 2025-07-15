import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import Memory, User
from services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

summary_bp = Blueprint("summary", __name__)


def get_recent_memories(user_id, start_date, end_date):
    """Get memories for a user within a date range"""
    user = db.session.get(User, user_id)
    encryption_key = user.encryption_key.encode()
    memories = (
        Memory.query.filter_by(user_id=user_id)
        .filter(Memory.created_at >= start_date)
        .filter(Memory.created_at <= end_date)
        .order_by(Memory.created_at.desc())
        .all()
    )

    memory_texts = []
    for memory in memories:
        try:
            val = memory._decrypt(memory.model_response, encryption_key)
            if val:
                memory_texts.append(val)
        except Exception as e:
            logger.error(f"Decryption failed for memory {memory.id}: {e}")

    return memory_texts


def build_summary_prompt(memories, summary_type="weekly"):
    """Build a prompt for summary generation"""
    joined_memories = "\n".join(memories)
    return f"Summarize the following memories for a {summary_type} summary:\n{joined_memories}"


class SummaryAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, summary_type):
        user_id = get_jwt_identity()

        if summary_type == "weekly":
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
            end_date = datetime.now(timezone.utc)
        elif summary_type == "monthly":
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
            end_date = datetime.now(timezone.utc)
        else:
            return jsonify({"error": "Invalid summary type"}), 400

        memories = get_recent_memories(user_id, start_date, end_date)
        if not memories:
            return jsonify({"error": "No memories found for summary."}), 404

        prompt = build_summary_prompt(memories, summary_type)

        try:
            # Use the new LLM client with long polling
            llm_client = get_llm_client()
            summary_text = llm_client.generate_with_long_polling(
                prompt=prompt,
                model="llama3:8b",
                max_retries=3,
                retry_delay=1.0,
            )

            logger.info(f"Successfully generated {summary_type} summary")

            return jsonify({"summary": summary_text, "summary_type": summary_type})

        except Exception as e:
            logger.error(f"Error generating {summary_type} summary: {e}")
            return jsonify({"error": f"Error generating summary: {str(e)}"}), 500


summary_bp.add_url_rule("/<summary_type>", view_func=SummaryAPI.as_view("summary_api"))
