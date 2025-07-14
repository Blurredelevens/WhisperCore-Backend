from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.memory import Memory
from models.user import User
from tasks.llm_service import LLMService
from models.reflection import Reflection
from extensions import db
from datetime import datetime, timezone

summary_bp = Blueprint('summary', __name__)

def get_recent_memories(user_id, count):
    user_id = int(user_id)
    user = db.session.get(User, user_id)
    encryption_key = user.encryption_key.encode()
    model_key = user.model_key.encode()
    memories = (
        Memory.query
        .filter_by(user_id=user_id)
        .order_by(Memory.created_at.desc())
        .limit(count)
        .all()
    )
    
    results = []
    for m in memories:
        print(f"Memory ID: {m.id}, model_response: {m.model_response[:50]}...")  # Print first 50 bytes
        try:
            val = m.get_model_response(model_key)
            print(f"Decrypted value for memory {m.id}: {val}")
            if val:
                results.append(val)
        except Exception as e:
            print(f"Decryption failed for memory {m.id}: {e}")
    return results

def build_summary_prompt(memories, summary_type="weekly"):
    joined_memories = "\n".join(memories)
    if summary_type == "weekly":
        instruction = "Summarize the following memories for the week:"
    else:
        instruction = "Summarize the following memories for the month:"
    return f"{instruction}\n{joined_memories}"

class SummaryAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, summary_type):
        user_id = get_jwt_identity()
        if summary_type not in ["weekly", "monthly"]:
            return jsonify({"error": "Invalid summary type"}), 400
        if summary_type == "weekly":
            count = 7
        elif summary_type == "monthly":
            count = 30 
        else:
            return jsonify({"error": "Invalid summary type"}), 400
        memories = get_recent_memories(user_id, count)
        if not memories:
            return jsonify({"error": "No memories found for summary."}), 404
        prompt = build_summary_prompt(memories, summary_type)
        llm_service = LLMService()
        summary = llm_service.process_query(prompt)

        # Extract the summary text
        summary_text = None
        if isinstance(summary, dict) and 'data' in summary and isinstance(summary['data'], dict) and 'text' in summary['data']:
            summary_text = summary['data']['text']
        elif isinstance(summary, dict) and 'text' in summary:
            summary_text = summary['text']
        elif isinstance(summary, str):
            summary_text = summary
        else:
            summary_text = str(summary)

        return jsonify({
            "summary": summary,
            "summary_type": summary_type
        })
        
summary_bp.add_url_rule('/<summary_type>', view_func=SummaryAPI.as_view('summary_api'))
