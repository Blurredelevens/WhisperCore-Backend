from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models.prompt import Prompt
from models.user import User

prompt_bp = Blueprint("prompt", __name__)


class PromptListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        prompts = Prompt.get_all()
        return jsonify([p.to_dict() for p in prompts]), 200

    def post(self):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user or not getattr(user, "is_admin", False):
            return jsonify({"error": "Admin privileges required"}), 403
        data = request.get_json()
        prompt = Prompt()
        prompt.from_dict(data)
        prompt.user_id = user_id
        prompt.save()
        return jsonify(prompt.to_dict()), 201


class PromptDetailAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, prompt_id):
        prompt = Prompt.get_by_id(prompt_id)
        if not prompt:
            return jsonify({"error": "Prompt not found"}), 404
        return jsonify(prompt.to_dict()), 200

    def put(self, prompt_id):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user or not getattr(user, "is_admin", False):
            return jsonify({"error": "Admin privileges required"}), 403
        prompt = Prompt.get_by_id(prompt_id)
        if not prompt:
            return jsonify({"error": "Prompt not found"}), 404
        data = request.get_json()
        prompt.user_id = user_id
        prompt.update(data)
        return jsonify(prompt.to_dict()), 200

    def delete(self, prompt_id):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user or not getattr(user, "is_admin", False):
            return jsonify({"error": "Admin privileges required"}), 403
        prompt = Prompt.get_by_id(prompt_id)
        if not prompt:
            return jsonify({"error": "Prompt not found"}), 404
        if str(prompt.user_id) != str(user_id):
            return jsonify({"error": "Unauthorized"}), 403
        prompt.delete()
        return jsonify({"message": "Prompt deleted"}), 200


class TodayPromptAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        user_id = get_jwt_identity()
        daily_prompt = Prompt.get_today_prompt(user_id)

        if daily_prompt:
            return (
                jsonify(
                    {
                        "prompt": daily_prompt.text,
                        "prompt_id": daily_prompt.id,
                        "prompt_date": daily_prompt.created_at.isoformat(),
                    },
                ),
                200,
            )
        else:
            return jsonify({"prompt": None, "message": "No prompt set for today."}), 404


# Register endpoints
prompt_bp.add_url_rule("/", view_func=PromptListAPI.as_view("prompt_list"))
prompt_bp.add_url_rule("/<int:prompt_id>", view_func=PromptDetailAPI.as_view("prompt_detail"))
prompt_bp.add_url_rule("/today", view_func=TodayPromptAPI.as_view("today_prompt"))
