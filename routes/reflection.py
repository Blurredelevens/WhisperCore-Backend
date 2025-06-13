from flask import Blueprint, request, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.reflection import Reflection
from app import db
from datetime import datetime, timedelta

reflection_bp = Blueprint('reflection', __name__)

class ReflectionListAPI(MethodView):
    decorators = [jwt_required()]
    def get(self):
        user_id = get_jwt_identity()
        reflection_type = request.args.get('type')
        query = Reflection.query.filter_by(user_id=user_id)
        if reflection_type:
            query = query.filter_by(reflection_type=reflection_type)
        reflections = query.order_by(Reflection.created_at.desc()).all()
        return jsonify([reflection.to_dict() for reflection in reflections]), 200
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
            period_start=data.get('period_start', datetime.utcnow()),
            period_end=data.get('period_end', datetime.utcnow() + timedelta(days=7 if data['reflection_type'] == 'weekly' else 30))
        )
        db.session.add(reflection)
        db.session.commit()
        return jsonify(reflection.to_dict()), 201

class ReflectionDetailAPI(MethodView):
    decorators = [jwt_required()]
    def get(self, reflection_id):
        user_id = get_jwt_identity()
        reflection = Reflection.query.filter_by(id=reflection_id, user_id=user_id).first()
        if not reflection:
            return jsonify({'error': 'Reflection not found'}), 404
        return jsonify(reflection.to_dict()), 200
    def delete(self, reflection_id):
        user_id = get_jwt_identity()
        reflection = Reflection.query.filter_by(id=reflection_id, user_id=user_id).first()
        if not reflection:
            return jsonify({'error': 'Reflection not found'}), 404
        db.session.delete(reflection)
        db.session.commit()
        return jsonify({'message': 'Reflection deleted successfully'}), 200

# Register the class-based views
reflection_bp.add_url_rule('/', view_func=ReflectionListAPI.as_view('reflection_list'))
reflection_bp.add_url_rule('/<int:reflection_id>', view_func=ReflectionDetailAPI.as_view('reflection_detail')) 