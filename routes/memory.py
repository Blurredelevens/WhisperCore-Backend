import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from extensions import db
from models.memory import Memory
from models.memory_image import MemoryImage
from models.user import User
from services.image_service import get_image_response, upload_image

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
        mood_emoji = request.args.get("mood_emoji")
        tag = request.args.get("tag")
        memory_weight = request.args.get("memory_weight")
        group_by_chat_id = request.args.get("group_by_chat_id", "false").lower() == "true"
        has_images = request.args.get("has_images")

        # Pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # Start with base query
        query = Memory.query.filter_by(user_id=user_id)
        # Apply filters
        if bookmarked:
            query = query.filter_by(is_bookmarked=True)

        if mood_emoji:
            query = query.filter(func.upper(Memory.mood_emoji) == mood_emoji.upper())

        if tag:
            query = query.filter(func.upper(Memory.tags) == tag.upper())

        if memory_weight:
            query = query.filter_by(memory_weight=memory_weight)

        # Filter by images
        if has_images is not None:
            has_images_bool = has_images.lower() == "true"
            if has_images_bool:
                # Get memories that have images

                query = query.filter(func.trim(func.lower(MemoryImage.image_path)) != "")
            else:
                # Get memories that don't have images
                query = query.outerjoin(Memory.images).filter(Memory.images.is_(None))

        # Handle search query - get all memories and filter in Python since content is encrypted
        if search_query:
            # Get all memories first (no pagination for search)
            all_memories = query.order_by(Memory.created_at.desc()).all()

            # Filter memories by search query in Python
            filtered_memories = []
            for memory in all_memories:
                try:
                    content = memory._decrypt(memory.encrypted_content, key)
                    model_response = memory._decrypt(memory.model_response, key)
                    normalized_content = re.sub(r"\s+", " ", content).strip() if content else ""
                    normalized_model_response = re.sub(r"\s+", " ", model_response).strip() if model_response else ""
                    if (
                        search_query.lower() in normalized_content.lower()
                        or search_query.lower() in normalized_model_response.lower()
                    ):
                        filtered_memories.append(memory)
                except Exception as e:
                    print(f"Decryption error: {e}")
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
            # Get all memories for grouping (no pagination) - already ordered by created_at desc
            all_memories = query.order_by(Memory.chat_id.desc(), Memory.created_at.desc()).all()

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

            # Convert to list and sort by most recent memory creation date (newest first)
            # Memories within each group are already ordered by created_at desc (newest first)
            grouped_list = list(grouped_memories.values())
            grouped_list.sort(key=lambda x: x["memories"][0]["created_at"], reverse=True)

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
                chat_id=data.get("chat_id"),
                mood_emoji=data.get("mood_emoji"),
                tags=",".join(data.get("tags", [])),
            )
            memory.set_content(content, key)
            memory.set_model_response(data["model_response"], key)
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

        image = request.files.get("image")
        if image.filename == "":
            return jsonify({"error": "No image selected"}), 400

        try:
            # Upload image using the new MemoryImage model
            _, image_path = upload_image(image, folder="memories", user_id=user_id, memory_id=memory_id)

            if image_path:
                # Create MemoryImage record
                memory_image = MemoryImage(memory_id=memory_id, user_id=user_id, image_path=image_path)
                db.session.add(memory_image)
                db.session.commit()

                return jsonify({"message": "Image uploaded successfully.", "image": memory_image.to_dict()}), 201
            else:
                return jsonify({"error": "Failed to upload image"}), 500

        except Exception as e:
            print(f"Error uploading memory image: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to upload image: {str(e)}"}), 500


class MemoryImageDownloadAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, memory_id):
        user_id = get_jwt_identity()
        memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
        if not memory:
            return jsonify({"error": "Memory not found"}), 404

        # Get the first image for this memory (for backward compatibility)
        memory_image = MemoryImage.query.filter_by(memory_id=memory_id, user_id=user_id).first()

        if not memory_image or not memory_image.image_path:
            return jsonify({"error": "No image found for this memory"}), 404

        return get_image_response(memory_image.image_path)


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
            if memory.mood_emoji:
                normalized_mood = memory.mood_emoji.strip().upper()
                moods.add(normalized_mood)
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


class MemoryTrendAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        key = user.encryption_key.encode()

        # Get all memories for the user
        memories = Memory.query.filter_by(user_id=user_id).order_by(Memory.created_at.desc()).all()

        if not memories:
            return (
                jsonify(
                    {
                        "stats": {
                            "total_entries": 0,
                            "current_streak": 0,
                            "average_mood": "No data",
                            "top_categories": [],
                            "mood_distribution": {},
                        },
                        "weekly_trend": [],
                        "monthly_insights": {
                            "most_productive_day": "No data",
                            "most_common_mood": "No data",
                            "total_words_written": 0,
                            "average_entries_per_day": 0,
                        },
                    },
                ),
                200,
            )

        # Calculate basic stats
        total_entries = len(memories)

        # Calculate current streak
        current_streak = self._calculate_current_streak(memories)

        # Calculate mood distribution and average
        mood_distribution, average_mood = self._calculate_mood_stats(memories)

        # Calculate top categories (tags)
        top_categories = self._calculate_top_categories(memories)

        # Calculate weekly trend
        weekly_trend = self._calculate_weekly_trend(memories, key)

        # Calculate monthly insights
        monthly_insights = self._calculate_monthly_insights(memories, key)

        return (
            jsonify(
                {
                    "stats": {
                        "total_entries": total_entries,
                        "current_streak": current_streak,
                        "average_mood": average_mood,
                        "top_categories": top_categories,
                        "mood_distribution": mood_distribution,
                    },
                    "weekly_trend": weekly_trend,
                    "monthly_insights": monthly_insights,
                },
            ),
            200,
        )

    def _calculate_current_streak(self, memories):
        """Calculate current streak of consecutive days with entries"""
        if not memories:
            return 0

        # Sort memories by date (newest first)
        sorted_memories = sorted(memories, key=lambda x: x.created_at.date(), reverse=True)

        streak = 0
        current_date = datetime.now(timezone.utc).date()

        for memory in sorted_memories:
            memory_date = memory.created_at.date()
            days_diff = (current_date - memory_date).days

            if days_diff == streak:
                streak += 1
            elif days_diff > streak:
                break

        return streak

    def _calculate_mood_stats(self, memories):
        """Calculate mood distribution and average mood using memory_weight"""
        mood_counts = {}
        total_mood_entries = 0
        total_weight = 0

        # Count mood emojis and sum memory_weight
        for memory in memories:
            if memory.mood_emoji:
                # Normalize mood emoji to uppercase and trim whitespace for case-insensitive counting
                normalized_mood = memory.mood_emoji.strip().upper()
                mood_counts[normalized_mood] = mood_counts.get(normalized_mood, 0) + 1
                total_mood_entries += 1
                total_weight += memory.memory_weight or 0

        # Calculate average mood using memory_weight
        if total_mood_entries > 0:
            average_weight = total_weight / total_mood_entries

            # Map average_weight to mood name
            if average_weight >= 8:
                average_mood = "Happy"
            elif average_weight >= 6:
                average_mood = "Good"
            elif average_weight >= 4:
                average_mood = "Okay"
            elif average_weight >= 2:
                average_mood = "Down"
            else:
                average_mood = "Bad"
        else:
            average_mood = "No data"

        return mood_counts, average_mood

    def _calculate_top_categories(self, memories):
        """Return top 5 tags as list of single-key dicts: [{'TAG': count}, ...]"""
        tag_counts = {}

        for memory in memories:
            if memory.tags:
                tags = memory.tags.split(",")
                for tag in tags:
                    tag = tag.strip()
                    if tag:
                        tag_upper = tag.upper()
                        tag_counts[tag_upper] = tag_counts.get(tag_upper, 0) + 1

        # Sort by count descending and take top 5
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        top_5 = sorted_tags[:5]

        # Convert to desired format
        return [{tag: count} for tag, count in top_5]

    def _calculate_weekly_trend(self, memories, key):
        """Calculate weekly trend for the last 7 days"""
        weekly_trend = []
        today = datetime.now(timezone.utc).date()

        for i in range(7):
            date = today - timedelta(days=i)
            day_memories = [m for m in memories if m.created_at.date() == date]

            # Skip if there are no memories for the day
            if not day_memories:
                continue

            # Calculate mood counts
            mood_counts = {}
            for memory in day_memories:
                mood = memory.mood_emoji
                if mood and mood.strip():
                    mood_upper = mood.strip().upper()
                    mood_counts[mood_upper] = mood_counts.get(mood_upper, 0) + 1

            # Skip this day if no valid mood is found
            if not mood_counts:
                continue

            # Determine most common mood
            most_common_mood = max(mood_counts.items(), key=lambda x: x[1])[0]

            weekly_trend.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "mood": most_common_mood,
                    "entry_count": len(day_memories),
                },
            )

        return list(reversed(weekly_trend))

    def _calculate_monthly_insights(self, memories, key):
        """Calculate monthly insights"""
        if not memories:
            return {
                "most_productive_day": "No data",
                "most_common_mood": "No data",
                "total_words_written": 0,
                "average_entries_per_day": 0,
            }

        # Calculate most productive day
        day_counts = {}
        for memory in memories:
            day_name = memory.created_at.strftime("%A")
            day_counts[day_name] = day_counts.get(day_name, 0) + 1

        most_productive_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else "No data"

        # Calculate most common mood
        mood_counts = {}
        for memory in memories:
            if memory.mood_emoji:
                normalized_mood = memory.mood_emoji.strip().upper()
                mood_counts[normalized_mood] = mood_counts.get(normalized_mood, 0) + 1

        most_common_mood = max(mood_counts.items(), key=lambda x: x[1])[0] if mood_counts else "No data"

        # Calculate total words written
        total_words = 0
        for memory in memories:
            try:
                content = memory._decrypt(memory.encrypted_content, key)
                if content:
                    total_words += len(content.split())
            except Exception:
                continue

        # Calculate average entries per day
        if memories:
            first_memory_date = min(memory.created_at.date() for memory in memories)
            last_memory_date = max(memory.created_at.date() for memory in memories)
            days_span = (last_memory_date - first_memory_date).days + 1
            average_entries_per_day = len(memories) / days_span if days_span > 0 else 0
        else:
            average_entries_per_day = 0

        return {
            "most_productive_day": most_productive_day,
            "most_common_mood": most_common_mood,
            "total_words_written": total_words,
            "average_entries_per_day": round(average_entries_per_day, 1),
        }


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
memory_bp.add_url_rule("/trends", view_func=MemoryTrendAPI.as_view("memory_trends"))
