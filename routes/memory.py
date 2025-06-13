from flask import Blueprint, request, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.memory import Memory
from app import db
from schemas.memory import (
    MemoryCreate, MemoryUpdate, MemoryResponse,
    MemoryListResponse, MemoryDeleteResponse
)

memory_bp = Blueprint('memory', __name__)

class MemoryListAPI(MethodView):
    decorators = [jwt_required()]
    def get(self):
        user_id = get_jwt_identity()
        memories = Memory.query.filter_by(user_id=user_id).order_by(Memory.created_at.desc()).all()
        return MemoryListResponse(
            memories=[MemoryResponse.model_validate(memory.to_dict()) for memory in memories]
        ).model_dump(), 200

    def post(self):
        try:
            data = MemoryCreate.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': str(e)}), 400

        user_id = get_jwt_identity()
        memory = Memory(
            user_id=user_id,
            content=data.content,
            mood=data.mood,
            tags=','.join(data.tags) if data.tags else None
        )
        
        db.session.add(memory)
        db.session.commit()
        
        return MemoryResponse.model_validate(memory.to_dict()).model_dump(), 201

class MemoryDetailAPI(MethodView):
    decorators = [jwt_required()]
    def get(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        
        return MemoryResponse.model_validate(memory.to_dict()).model_dump(), 200

    def put(self, memory_id):
        try:
            data = MemoryUpdate.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': str(e)}), 400

        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        
        if data.content is not None:
            memory.content = data.content
        if data.mood is not None:
            memory.mood = data.mood
        if data.tags is not None:
            memory.tags = ','.join(data.tags)
        
        db.session.commit()
        
        return MemoryResponse.model_validate(memory.to_dict()).model_dump(), 200

    def delete(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        
        db.session.delete(memory)
        db.session.commit()
        
        return MemoryDeleteResponse(message='Memory deleted successfully').model_dump(), 200

# Register the class-based views
memory_bp.add_url_rule('/', view_func=MemoryListAPI.as_view('memory_list'))
memory_bp.add_url_rule('/<int:memory_id>', view_func=MemoryDetailAPI.as_view('memory_detail')) 