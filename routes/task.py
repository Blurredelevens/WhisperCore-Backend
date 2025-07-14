import json
import logging

from celery.result import AsyncResult
from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import celery, db
from models import Memory, User

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

        memory = Memory(user_id=user_id, chat_id=data.get("chat_id"), mood_emoji=data.get("mood_emoji"))
        memory.set_content(data["content"], key)
        db.session.add(memory)
        db.session.commit()

        try:
            task = celery.send_task("tasks.scheduled.process_query_task", args=[data["content"]])
            return jsonify({"message": "Task started successfully", "status": "processing", "task_id": task.id}), 202
        except Exception as e:
            return jsonify({"error": f"Error starting task: {str(e)}"}), 500


class TaskStatusAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, task_id):
        user_id = get_jwt_identity()
        task_result = AsyncResult(task_id, app=celery)

        if task_result.state == "PENDING":
            response = {
                "task_id": task_id,
                "state": task_result.state,
                "status": "Task is scheduled and waiting to be processed.",
            }
        elif task_result.state == "SUCCESS":
            result_data = task_result.result

            try:
                memories = Memory.query.filter_by(user_id=user_id).order_by(Memory.created_at.desc()).limit(1).all()
                if memories:
                    memory = memories[0]
                    if not memory.model_response or memory.model_response == b"":
                        user = User.query.get(user_id)
                        key = user.encryption_key.encode()

                        if isinstance(result_data, dict) and "data" in result_data:
                            if isinstance(result_data["data"], dict) and "text" in result_data["data"]:
                                response_text = result_data["data"]["text"]
                            elif isinstance(result_data["data"], str):
                                response_text = result_data["data"]
                            else:
                                response_text = json.dumps(result_data["data"])
                        elif isinstance(result_data, dict):
                            response_text = json.dumps(result_data)
                        else:
                            response_text = str(result_data)

                        memory.set_model_response(response_text, key)
                        db.session.commit()
                        print(f"Saved response to memory {memory.id} via TaskStatusAPI")
            except Exception as e:
                print(f"Error saving response in TaskStatusAPI: {e}")

            response = {
                "task_id": task_id,
                "state": task_result.state,
                "status": "Task completed successfully",
                "data": result_data,
            }
        elif task_result.state == "FAILURE":
            response = {
                "task_id": task_id,
                "state": task_result.state,
                "status": "Task failed",
                "error": str(task_result.info),
            }
        else:
            response = {"task_id": task_id, "state": task_result.state, "status": "Task is in progress..."}

        return jsonify(response)


# Register the blueprint

task_bp.add_url_rule(
    "/query",
    view_func=TaskAPI.as_view("task"),
    methods=["POST"],
)
task_bp.add_url_rule(
    "/<task_id>",
    view_func=TaskStatusAPI.as_view("task_status"),
    methods=["GET"],
)
