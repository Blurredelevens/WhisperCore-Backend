import logging

from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import Memory, User
from services.llm_client import get_llm_client

task_bp = Blueprint("task", __name__)

logger = logging.getLogger(__name__)


class TaskAPI(MethodView):
    decorators = [jwt_required()]

    def post(self):
        print("Request received")
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        key = user.encryption_key.encode()
        data = request.get_json()

        if not data or "content" not in data:
            return jsonify({"error": "Missing 'content' in request body"}), 400

        # Create memory first
        memory = Memory(user_id=user_id, chat_id=data.get("chat_id"), mood_emoji=data.get("mood_emoji"))
        memory.set_content(data["content"], key)
        db.session.add(memory)
        db.session.commit()

        try:
            # Use LLM client to generate both reflection and weight in a single call
            logger.info("Creating LLM client...")
            llm_client = get_llm_client()
            logger.info(f"LLM client created successfully with base URL: {llm_client.base_url}")

            # Get user's tone preference, default to "empathetic" if not set
            user_tone = user.tone if user.tone else "empathetic"

            # Generate both reflection and weight using single LLM call
            logger.info(f"Starting LLM generation for reflection and weight with content: {data['content'][:100]}...")
            reflection_text, weight = llm_client.generate_reflection_and_weight(
                memory_content=data["content"],
                tone=user_tone,
                model="llama3:8b",
                max_retries=3,
                retry_delay=1.0,
            )
            logger.info(
                f"LLM generation completed successfully. Reflection length: {len(reflection_text)}, Weight: {weight}",
            )
            logger.info(f"Extracted weight type: {type(weight)}, value: {weight}")

            # Update memory with weight and save the reflection
            logger.info(f"Before update - Memory weight: {memory.memory_weight}")
            memory.memory_weight = weight
            logger.info(f"After update - Memory weight: {memory.memory_weight}")
            memory.set_model_response(reflection_text, key)

            # Verify the weight is set before commit
            logger.info(f"Before commit - Memory weight: {memory.memory_weight}")
            db.session.commit()
            logger.info(f"After commit - Memory weight: {memory.memory_weight}")

            # Refresh from database to verify
            db.session.refresh(memory)
            logger.info(f"After refresh - Memory weight: {memory.memory_weight}")

            logger.info(f"Memory updated with weight {weight} and reflection saved to memory ID: {memory.id}")

            return (
                jsonify(
                    {
                        "message": "Task completed successfully",
                        "status": "completed",
                        "response": reflection_text,
                        "memory_id": memory.id,
                        "memory_weight": weight,
                        "chat_id": data.get("chat_id"),
                        "mood_emoji": data.get("mood_emoji"),
                    },
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error processing task: {str(e)}")
            logger.exception("Full traceback:")
            return jsonify({"error": f"Error processing task: {str(e)}"}), 500


# Register the blueprint
task_bp.add_url_rule(
    "/query",
    view_func=TaskAPI.as_view("task"),
    methods=["POST"],
)
