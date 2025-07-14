import os

from flask import Blueprint, current_app, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from extensions import db
from models.memory import Memory
from models.user import User

memory_bp = Blueprint("memory", __name__)


class MemoryListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        key = user.encryption_key.encode()

        # Get query parameters
        bookmarked = request.args.get("bookmarked", "false").lower() == "true"
        search_query = request.args.get("search", "")
        mood = request.args.get("mood")
        mood_emoji = request.args.get("mood_emoji")
        tag = request.args.get("tag")
        chat_id = request.args.get("chat_id")
        group_by_chat_id = request.args.get("group_by_chat_id", "false").lower() == "true"

        # Pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # Start with base query
        query = Memory.query.filter_by(user_id=user_id)

        # Apply filters
        if bookmarked:
            query = query.filter_by(is_bookmarked=True)

        if mood:
            query = query.filter_by(mood=mood)

        if mood_emoji:
            query = query.filter_by(mood_emoji=mood_emoji)

        if tag:
            query = query.filter(Memory.tags.ilike(f"%{tag}%"))

        if chat_id:
            query = query.filter_by(chat_id=chat_id)

        # Handle search query - get all memories and filter in Python since content is encrypted
        if search_query:
            # Get all memories first (no pagination for search)
            all_memories = query.order_by(Memory.created_at.desc()).all()

            # Filter memories by search query in Python
            filtered_memories = []
            for memory in all_memories:
                try:
                    content = memory.get_content(key)
                    if content and search_query.lower() in content.lower():
                        filtered_memories.append(memory)
                except Exception:
                    # Skip memories with decryption errors
                    continue

            # Apply pagination to filtered results
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_memories = filtered_memories[start_idx:end_idx]

            memories = [memory.to_dict(key) for memory in paginated_memories]

            return (
                jsonify(
                    {
                        "memories": memories,
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": len(filtered_memories),
                            "pages": (len(filtered_memories) + per_page - 1) // per_page,
                            "has_next": end_idx < len(filtered_memories),
                            "has_prev": page > 1,
                        },
                    },
                ),
                200,
            )

        # Handle grouping by chat_id
        if group_by_chat_id:
            # Get all memories for grouping (no pagination)
            all_memories = query.order_by(Memory.created_at.desc()).all()

            # Group memories by chat_id
            grouped_memories = {}
            total_memories = 0

            for memory in all_memories:
                chat_id_key = memory.chat_id or "no_chat_id"
                if chat_id_key not in grouped_memories:
                    grouped_memories[chat_id_key] = {"chat_id": memory.chat_id, "count": 0, "memories": []}

                grouped_memories[chat_id_key]["count"] += 1
                grouped_memories[chat_id_key]["memories"].append(memory.to_dict(key))
                total_memories += 1

            # Convert to list and sort by count descending
            grouped_list = list(grouped_memories.values())
            grouped_list.sort(key=lambda x: x["count"], reverse=True)

            return (
                jsonify(
                    {
                        "memories": grouped_list,
                        "grouped_by_chat_id": True,
                        "total_memories": total_memories,
                        "total_groups": len(grouped_list),
                    },
                ),
                200,
            )

        # Regular pagination (no grouping)
        # Order by created_at desc
        query = query.order_by(Memory.created_at.desc())

        # Apply pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        memories = [memory.to_dict(key) for memory in pagination.items]

        return (
            jsonify(
                {
                    "memories": memories,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": pagination.total,
                        "pages": pagination.pages,
                        "has_next": pagination.has_next,
                        "has_prev": pagination.has_prev,
                    },
                },
            ),
            200,
        )

    def post(self):
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)
            key = user.encryption_key.encode()
            data = request.get_json()

            # Validation
            if not data:
                return jsonify({"error": "Request body is required"}), 400

            if "content" not in data:
                return jsonify({"error": "Content is required"}), 400

            content = data["content"]
            if not isinstance(content, str):
                return jsonify({"error": "Content must be a string"}), 400

            if not content.strip():
                return jsonify({"error": "Content cannot be empty"}), 400

            if "model_response" not in data:
                return jsonify({"error": "Model response is required"}), 400

            memory = Memory(
                user_id=user_id,
                chat_id=data.get("chat_id"),  # Save chat_id if provided
                mood=data.get("mood"),
                mood_emoji=data.get("mood_emoji"),
                tags=",".join(data.get("tags", [])),
            )
            memory.set_content(content, key)
            memory.set_model_response(data["model_response"], user.model_key.encode())
            db.session.add(memory)
            db.session.commit()

            return jsonify({"memory": memory.to_dict(key)}), 201
        except Exception as e:
            print("Error in POST /api/memories:", e)
            return jsonify({"error": str(e)}), 500


class MemoryDetailAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, memory_id):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        key = user.encryption_key.encode()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({"error": "Memory not found"}), 404
        return jsonify({"memory": memory.to_dict(key)}), 200

    def put(self, memory_id):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        key = user.encryption_key.encode()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({"error": "Memory not found"}), 404
        data = request.get_json()
        if "content" in data:
            memory.set_content(data["content"], key)
        if "chat_id" in data:
            memory.chat_id = data["chat_id"]
        if "mood" in data:
            memory.mood = data["mood"]
        if "mood_emoji" in data:
            memory.mood_emoji = data["mood_emoji"]
        if "tags" in data:
            memory.tags = ",".join(data["tags"])
        db.session.commit()
        return (
            jsonify({"message": "Memory updated successfully", "memory": memory.to_dict(key)}),
            200,
        )

    def delete(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({"error": "Memory not found"}), 404
        db.session.delete(memory)
        db.session.commit()
        return jsonify({"message": "Memory deleted successfully"}), 200


class MemoryImageUploadAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({"error": "Memory not found"}), 404

        if "image" not in request.files:
            return jsonify({"error": "No image part in request"}), 400

        image = request.files["image"]
        if image.filename == "":
            return jsonify({"error": "No image selected"}), 400

        filename = secure_filename(image.filename)
        upload_folder = os.path.join(current_app.root_path, "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        image.save(file_path)

        memory.image_path = file_path
        db.session.commit()

        return jsonify({"message": "Image uploaded successfully", "image_path": file_path}), 200


class MemoryImageDownloadAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({"error": "Memory not found"}), 404
        if not memory.image_path:
            return jsonify({"error": "No image found for this memory"}), 404
        return send_file(memory.image_path, mimetype="image/jpeg")


class MemoryTagListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        user_id = get_jwt_identity()
        memories = Memory.query.filter_by(user_id=user_id).all()
        tags = set()
        for memory in memories:
            if memory.tags:
                tags.update(memory.tags.split(","))
        return jsonify(list(tags))


class MemoryMoodListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        user_id = get_jwt_identity()
        memories = Memory.query.filter_by(user_id=user_id).all()
        moods = set()
        for memory in memories:
            if memory.mood:
                moods.add(memory.mood)
        return jsonify(list(moods))


class MemoryChatListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, chat_id):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        key = user.encryption_key.encode()

        # Get memories for the specific chat_id from URL parameter
        memories = Memory.query.filter_by(user_id=user_id, chat_id=chat_id).order_by(Memory.created_at.desc()).all()

        return jsonify([memory.to_dict(key) for memory in memories])


class MemoryBookmarkAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({"error": "Memory not found"}), 404

        memory.is_bookmarked = not memory.is_bookmarked
        db.session.commit()
        return jsonify({"id": memory.id, "is_bookmarked": memory.is_bookmarked}), 200


# Register the class-based views
memory_bp.add_url_rule("/", view_func=MemoryListAPI.as_view("memory_list"))
memory_bp.add_url_rule("/<int:memory_id>", view_func=MemoryDetailAPI.as_view("memory_detail"))
memory_bp.add_url_rule("/<int:memory_id>/image", view_func=MemoryImageUploadAPI.as_view("memory_image_upload"))
memory_bp.add_url_rule(
    "/<int:memory_id>/image/download",
    view_func=MemoryImageDownloadAPI.as_view("memory_image_download"),
)
memory_bp.add_url_rule("/tags", view_func=MemoryTagListAPI.as_view("memory_tag_list"))
memory_bp.add_url_rule("/<int:memory_id>/bookmark", view_func=MemoryBookmarkAPI.as_view("memory_bookmark"))
memory_bp.add_url_rule("/moods", view_func=MemoryMoodListAPI.as_view("memory_mood_list"))
memory_bp.add_url_rule("/chats/<string:chat_id>", view_func=MemoryChatListAPI.as_view("memory_chat_detail"))
