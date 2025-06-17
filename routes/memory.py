from flask import Blueprint, request, jsonify, current_app, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.memory import Memory
from models.user import User
from extensions import db
from schemas.memory import (
    MemoryCreate, MemoryUpdate, MemoryResponse,
    MemoryListResponse, MemoryDeleteResponse
)
import os
from werkzeug.utils import secure_filename

memory_bp = Blueprint('memory', __name__)

class MemoryListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        key = user.encryption_key.encode()
        
        # Get query parameters
        bookmarked = request.args.get('bookmarked', 'false').lower() == 'true'
        search_query = request.args.get('search', '')
        mood = request.args.get('mood')
        tag = request.args.get('tag')
        
        # Start with base query
        query = Memory.query.filter_by(user_id=user_id)
        
        # Apply filters
        if bookmarked:
            query = query.filter_by(is_bookmarked=True)
        
        if search_query:
            query = query.filter(Memory.content.ilike(f'%{search_query}%'))
        
        if mood:
            query = query.filter_by(mood=mood)
        
        if tag:
            query = query.filter(Memory.tags.ilike(f'%{tag}%'))
        
        # Order by created_at desc
        memories = query.order_by(Memory.created_at.desc()).all()
        
        return jsonify([memory.to_dict(key) for memory in memories]), 200

    def post(self):
        try:
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            key = user.encryption_key.encode()
            data = request.get_json()
            print("Encrypting with key:", key)
            print("Content to encrypt:", data['content'])
            memory = Memory(
                user_id=user_id,
                mood=data.get('mood'),
                tags=','.join(data.get('tags', []))
            )
            memory.set_content(data['content'], key)
            db.session.add(memory)
            db.session.commit()
            return jsonify(memory.to_dict(key)), 201
        except Exception as e:
            print("Error in POST /api/memories:", e)
            return jsonify({"error": str(e)}), 500

class MemoryDetailAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, memory_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        key = user.encryption_key.encode()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        return jsonify(memory.to_dict(key)), 200

    def put(self, memory_id):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        key = user.encryption_key.encode()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        data = request.get_json()
        if 'content' in data:
            memory.set_content(data['content'], key)
        if 'mood' in data:
            memory.mood = data['mood']
        if 'tags' in data:
            memory.tags = ','.join(data['tags'])
        db.session.commit()
        return jsonify(memory.to_dict(key)), 200

    def delete(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        db.session.delete(memory)
        db.session.commit()
        return jsonify({'message': 'Memory deleted successfully'}), 200



class MemoryImageUploadAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404

        if 'image' not in request.files:
            return jsonify({'error': 'No image part in request'}), 400

        image = request.files['image']
        if image.filename == '':
            return jsonify({'error': 'No image selected'}), 400

        filename = secure_filename(image.filename)
        upload_folder = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        image.save(file_path)

        memory.image_path = file_path
        db.session.commit()

        return jsonify({'message': 'Image uploaded successfully', 'image_path': file_path}), 200


class MemoryImageDownloadAPI(MethodView):
    decorators = [jwt_required()]
    def get(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        if not memory.image_path:
            return jsonify({'error': 'No image found for this memory'}), 404
        return send_file(memory.image_path, mimetype='image/jpeg')
    


class MemoryTagListAPI(MethodView):
    decorators = [jwt_required()]
    def get(self):
        user_id = get_jwt_identity()
        memories = Memory.query.filter_by(user_id=user_id).all()
        tags = set()
        for memory in memories:
            if memory.tags:
                tags.update(memory.tags.split(','))
        return jsonify(list(tags))
    

class MemoryBookmarkAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({'error': 'Memory not found'}), 404
        
        memory.is_bookmarked = not memory.is_bookmarked
        db.session.commit()
        return jsonify({
            'id': memory.id,
            'is_bookmarked': memory.is_bookmarked
        }), 200

# Register the class-based views
memory_bp.add_url_rule('/', view_func=MemoryListAPI.as_view('memory_list'))
memory_bp.add_url_rule('/<int:memory_id>', view_func=MemoryDetailAPI.as_view('memory_detail')) 
memory_bp.add_url_rule('/<int:memory_id>/image', view_func=MemoryImageUploadAPI.as_view('memory_image_upload'))
memory_bp.add_url_rule('/<int:memory_id>/image/download', view_func=MemoryImageDownloadAPI.as_view('memory_image_download'))
memory_bp.add_url_rule('/tags', view_func=MemoryTagListAPI.as_view('memory_tag_list'))
memory_bp.add_url_rule('/<int:memory_id>/bookmark', view_func=MemoryBookmarkAPI.as_view('memory_bookmark'))