from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.reflection import Reflection
from flask.views import MethodView
from extensions import db
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)
reflection_bp = Blueprint('reflection', __name__)

class ReflectionCreateAPI(MethodView):
    decorators = [jwt_required()]
    
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data or not data.get('content') or not data.get('reflection_type'):
            return jsonify({'error': 'Content and reflection type are required'}), 400
        if data['reflection_type'] not in ['weekly', 'monthly']:
            return jsonify({'error': 'Invalid reflection type'}), 400
        reflection = Reflection(
            user_id=user_id,
            content=data['content'],
            reflection_type=data['reflection_type'],
            period_start=data.get('period_start', datetime.now(timezone.utc)),
            period_end=data.get('period_end', datetime.now(timezone.utc) + timedelta(days=7 if data['reflection_type'] == 'weekly' else 30))
        )
        db.session.add(reflection)
        db.session.commit()
        return jsonify(reflection.to_dict()), 201

class ReflectionListAPI(MethodView):
    decorators = [jwt_required()]
    
    def get(self):
        user_id = get_jwt_identity()
        reflection_type = request.args.get('type')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        query = Reflection.query.filter_by(user_id=user_id)
        if reflection_type:
            query = query.filter_by(reflection_type=reflection_type)

        reflections = query.order_by(Reflection.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            "reflections": [reflection.to_dict() for reflection in reflections.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": reflections.total,
                "pages": reflections.pages
            }
        }), 200

class ReflectionDetailAPI(MethodView):
    decorators = [jwt_required()]
    
    def get(self, reflection_id):
        user_id = get_jwt_identity()
        reflection = Reflection.query.filter_by(id=reflection_id, user_id=user_id).first()
        if not reflection:
            return jsonify({'error': 'Reflection not found'}), 404
        return jsonify(reflection.to_dict()), 200

class ReflectionDeleteAPI(MethodView):
    decorators = [jwt_required()]
    
    def delete(self, reflection_id):
        user_id = get_jwt_identity()
        reflection = Reflection.query.filter_by(id=reflection_id, user_id=user_id).first()
        if not reflection:
            return jsonify({'error': 'Reflection not found'}), 404
        db.session.delete(reflection)
        db.session.commit()
        return jsonify({'message': 'Reflection deleted successfully'}), 200

reflection_bp.add_url_rule('/', view_func=ReflectionListAPI.as_view('reflection_list'))
reflection_bp.add_url_rule('/<int:reflection_id>', view_func=ReflectionDetailAPI.as_view('reflection_detail')) 
reflection_bp.add_url_rule('/<int:reflection_id>', view_func=ReflectionDeleteAPI.as_view('reflection_delete'))
reflection_bp.add_url_rule('/', view_func=ReflectionCreateAPI.as_view('reflection_create'))