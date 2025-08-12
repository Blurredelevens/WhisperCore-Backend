import json
import logging

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import Memory, User  # Assuming this import is correct
from models.memory_image import MemoryImage
from services.image_service import upload_image
from services.llm_client import get_llm_client

task_bp = Blueprint("task", __name__)

logger = logging.getLogger(__name__)


class TaskAPI(MethodView):
    decorators = [jwt_required()]

    def post(self):
        print("Request received")
        user_id = get_jwt_identity()
        try:
            user = User.query.get(user_id)  # Use User.query for better error handling
            if not user:
                return jsonify({"error": "User not found"}), 404
            key = user.encryption_key.encode()

            if request.content_type and request.content_type.startswith("multipart/form-data"):
                data = request.form.to_dict()
                image = request.files.get("image")
            else:
                data = request.get_json() or {}
                image = None

            if not data or "content" not in data:
                return jsonify({"error": "Missing 'content' in request body"}), 400

            stream_response = data.get("stream", False)

            if not stream_response and data.get("stream") is not False:
                stream_response = True

            memory = Memory(
                user_id=user_id,
                chat_id=data.get("chat_id"),
                mood_emoji=data.get("mood_emoji"),
            )
            memory.set_content(data["content"], key)
            db.session.add(memory)
            db.session.commit()

            image_base64, image_path = upload_image(image, folder="memories", user_id=user_id, memory_id=memory.id)

            if image_path:
                memory_image = MemoryImage(memory_id=memory.id, user_id=user_id, image_path=image_path)
                db.session.add(memory_image)
                db.session.commit()

            llm_client = get_llm_client()
            user_tone = user.tone if user.tone else "empathetic"
            model = "llama3:8b"

            if stream_response:
                return self._handle_streaming_response(
                    llm_client,
                    data["content"],
                    user_tone,
                    model,
                    image_base64,
                    memory,
                    key,
                    data,
                )
            else:
                return self._handle_regular_response(
                    llm_client,
                    data["content"],
                    user_tone,
                    model,
                    image_base64,
                    memory,
                    key,
                    data,
                    image_path,
                    user_id,
                )

        except Exception as e:
            logger.error(f"Error processing task: {str(e)}")
            logger.exception("Full traceback:")
            db.session.rollback()
            return jsonify({"error": f"Error processing task: {str(e)}"}), 500

    def _handle_streaming_response(self, llm_client, content, user_tone, model, image_base64, memory, key, data):
        """Handle streaming response for real-time output"""

        def generate_stream():
            try:
                chunk_count = 0

                for chunk_data in llm_client.generate_reflection_and_weight_stream(
                    memory_content=content,
                    tone=user_tone,
                    model=model,
                    max_retries=3,
                    retry_delay=1.0,
                    image_base64=image_base64,
                ):
                    chunk_count += 1

                    if chunk_data["type"] == "chunk":
                        chunk_data_json = {
                            "type": "chunk",
                            "content": chunk_data["content"],
                            "done": False,
                        }
                        chunk_message = f"data: {json.dumps(chunk_data_json)}\n\n"
                        yield chunk_message
                    elif chunk_data["type"] == "complete":
                        memory.memory_weight = chunk_data["weight"]
                        memory.set_model_response(chunk_data["reflection"], key)

                        # Save tags to database
                        if chunk_data.get("tags"):
                            memory.tags = ",".join(chunk_data["tags"])

                        db.session.commit()

                        completion_data = {
                            "type": "complete",
                            "reflection": chunk_data["reflection"],
                            "weight": chunk_data["weight"],
                            "tags": chunk_data.get("tags", []),
                            "memory_id": memory.id,
                            "done": True,
                        }
                        completion_message = f"data: {json.dumps(completion_data)}\n\n"
                        yield completion_message
                        break
                    elif chunk_data["type"] == "error":
                        error_message = (
                            f"data: {json.dumps({'type': 'error', 'error': chunk_data['error'], 'done': True})}\n\n"
                        )
                        yield error_message
                        break

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'done': True})}\n\n"

        return Response(
            stream_with_context(generate_stream()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    def _handle_regular_response(
        self,
        llm_client,
        content,
        user_tone,
        model,
        image_base64,
        memory,
        key,
        data,
        image_path,
        user_id,
    ):
        """Handle regular (non-streaming) response"""

        reflection_text, weight, tags = llm_client.generate_reflection_weight_and_tags(
            memory_content=content,
            tone=user_tone,
            model=model,
            max_retries=3,
            retry_delay=1.0,
            image_base64=image_base64,
        )

        memory.memory_weight = weight
        memory.set_model_response(reflection_text, key)

        # Save tags to database
        if tags:
            memory.tags = ",".join(tags)

        db.session.commit()
        db.session.refresh(memory)

        memory_images = []
        if image_path:
            memory_image = MemoryImage.query.filter_by(memory_id=memory.id, user_id=user_id).first()
            if memory_image:
                memory_images.append(memory_image.to_dict())

        return (
            jsonify(
                {
                    "message": "Task completed successfully",
                    "status": "completed",
                    "response": reflection_text,
                    "memory_id": memory.id,
                    "memory_weight": weight,
                    "ai_tone": user_tone,
                    "chat_id": data.get("chat_id"),
                    "mood_emoji": data.get("mood_emoji"),
                    "images": memory_images,
                    "tags": tags,
                    "image_path": image_path,
                },
            ),
            200,
        )


# Register the blueprint
task_bp.add_url_rule(
    "/query",
    view_func=TaskAPI.as_view("task"),
    methods=["POST"],
)
