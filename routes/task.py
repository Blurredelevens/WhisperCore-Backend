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
            # Use LLM client with long polling instead of Celery task
            logger.info("Creating LLM client...")
            llm_client = get_llm_client()
            logger.info(f"LLM client created successfully with base URL: {llm_client.base_url}")

            # Generate response using long polling
            logger.info(f"Starting LLM generation with prompt: {data['content'][:100]}...")
            response_text = llm_client.generate_with_long_polling(
                prompt=data["content"],
                model="llama3:8b",
                max_retries=3,
                retry_delay=1.0,
            )
            logger.info(f"LLM generation completed successfully. Response length: {len(response_text)}")

            # Save the response to memory using the same encryption key
            logger.info("Saving response to memory...")
            memory.set_model_response(response_text, key)  # Use the same key as content
            db.session.commit()
            logger.info(f"Response saved to memory ID: {memory.id}")

            return (
                jsonify(
                    {
                        "message": "Task completed successfully",
                        "status": "completed",
                        "response": response_text,
                        "memory_id": memory.id,
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
