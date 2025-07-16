import logging

from flask import Blueprint, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import Memory, User
from services.memory_weighting import get_memory_weighting_service

logger = logging.getLogger(__name__)

memory_weighting_bp = Blueprint("memory_weighting", __name__)


class WeightMemoryAPI(MethodView):
    decorators = [jwt_required()]

    def post(self):
        """Weight a specific memory using LLM analysis"""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            data = request.get_json()
            memory_id = data.get("memory_id")

            if not memory_id:
                return jsonify({"error": "memory_id is required"}), 400

            # Get the specific memory
            memory = Memory.query.filter_by(user_id=user_id, id=memory_id).first()
            if not memory:
                return jsonify({"error": "Memory not found"}), 404

            # Get memory content
            memory_content = memory._decrypt(memory.encrypted_content, user.encryption_key.encode())
            if not memory_content:
                return jsonify({"error": "Could not decrypt memory content"}), 400

            # Get memory model response
            memory_model_response = memory._decrypt(memory.model_response, user.encryption_key.encode())
            if not memory_model_response:
                return jsonify({"error": "Could not decrypt memory model response"}), 400

            # Get user's tone preference, default to "empathetic" if not set
            user_tone = user.tone if user.tone else "empathetic"

            # Weight the memory
            weighting_service = get_memory_weighting_service()
            weight = weighting_service.weight_memory(memory_content, tone=user_tone)

            # Update memory with new weight
            memory.memory_weight = weight
            db.session.commit()

            logger.info(f"Successfully weighted memory {memory.id} with weight {weight}")

            return jsonify(
                {
                    "success": True,
                    "memory_id": memory.id,
                    "content": memory_content,
                    "model_response": memory_model_response,
                    "weight": weight,
                    "message": f"Memory weighted successfully with weight {weight}",
                },
            )

        except Exception as e:
            logger.error(f"Error weighting memory: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to weight memory: {str(e)}"}), 500


class WeightMultipleMemoriesAPI(MethodView):
    decorators = [jwt_required()]

    def post(self):
        """Weight multiple memories in batch"""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            data = request.get_json()
            memory_ids = data.get("memory_ids", [])

            if not memory_ids:
                return jsonify({"error": "No memory IDs provided"}), 400

            # Get memories
            memories = Memory.query.filter_by(user_id=user_id).filter(Memory.id.in_(memory_ids)).all()

            if not memories:
                return jsonify({"error": "No memories found"}), 404

            # Get user's tone preference, default to "empathetic" if not set
            user_tone = user.tone if user.tone else "empathetic"

            weighting_service = get_memory_weighting_service()
            results = []

            for memory in memories:
                try:
                    # Get memory content
                    memory_content = memory._decrypt(memory.encrypted_content, user.encryption_key.encode())
                    if not memory_content:
                        results.append(
                            {"memory_id": memory.id, "success": False, "error": "Could not decrypt memory content"},
                        )
                        continue

                    # Get memory model response
                    memory_model_response = memory._decrypt(memory.model_response, user.encryption_key.encode())
                    if not memory_model_response:
                        results.append(
                            {
                                "memory_id": memory.id,
                                "success": False,
                                "error": "Could not decrypt memory model response",
                            },
                        )
                        continue

                    # Weight the memory
                    weight = weighting_service.weight_memory(memory_content, tone=user_tone)

                    # Update memory with new weight
                    memory.memory_weight = weight

                    results.append(
                        {
                            "memory_id": memory.id,
                            "success": True,
                            "content": memory_content,
                            "model_response": memory_model_response,
                            "weight": weight,
                        },
                    )

                except Exception as e:
                    logger.error(f"Error weighting memory {memory.id}: {e}")
                    results.append({"memory_id": memory.id, "success": False, "error": str(e)})

            # Commit all changes
            db.session.commit()

            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful

            logger.info(f"Batch weighted {len(memories)} memories: {successful} successful, {failed} failed")

            return jsonify(
                {
                    "success": True,
                    "results": results,
                    "summary": {"total": len(memories), "successful": successful, "failed": failed},
                },
            )

        except Exception as e:
            logger.error(f"Error in batch memory weighting: {e}")
            db.session.rollback()
            return jsonify({"error": f"Failed to weight memories: {str(e)}"}), 500


class MemoriesByWeightAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        """Get memories filtered by minimum weight"""
        try:
            user_id = get_jwt_identity()
            min_weight = request.args.get("min_weight", 7, type=int)

            if not (1 <= min_weight <= 10):
                return jsonify({"error": "min_weight must be between 1 and 10"}), 400

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Get memories with minimum weight
            memories = (
                Memory.query.filter_by(user_id=user_id)
                .filter(Memory.memory_weight >= min_weight)
                .order_by(Memory.memory_weight.desc(), Memory.created_at.desc())
                .limit(50)  # Limit to prevent too many results
                .all()
            )

            memory_list = []
            for memory in memories:
                try:
                    content = memory._decrypt(memory.encrypted_content, user.encryption_key.encode())
                    model_response = memory._decrypt(memory.model_response, user.encryption_key.encode())
                    if content:
                        memory_list.append(
                            {
                                "id": memory.id,
                                "content": content,
                                "model_response": model_response,
                                "weight": memory.memory_weight,
                                "created_at": memory.created_at.isoformat(),
                                "mood_emoji": memory.mood_emoji,
                                "tags": memory.tags.split(",") if memory.tags else [],
                            },
                        )
                except Exception as e:
                    logger.error(f"Error decrypting memory {memory.id}: {e}")

            return jsonify(
                {"success": True, "memories": memory_list, "count": len(memory_list), "min_weight": min_weight},
            )

        except Exception as e:
            logger.error(f"Error getting memories by weight: {e}")
            return jsonify({"error": f"Failed to get memories: {str(e)}"}), 500


class WeightStatisticsAPI(MethodView):
    decorators = [jwt_required()]

    def get(self):
        """Get statistics about memory weights for the user"""
        try:
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)

            if not user:
                return jsonify({"error": "User not found"}), 404

            # Get weight statistics
            from sqlalchemy import func

            stats = (
                db.session.query(
                    func.count(Memory.id).label("total_memories"),
                    func.avg(Memory.memory_weight).label("avg_weight"),
                    func.min(Memory.memory_weight).label("min_weight"),
                    func.max(Memory.memory_weight).label("max_weight"),
                    func.count(Memory.id).filter(Memory.memory_weight >= 7).label("high_weight_count"),
                    func.count(Memory.id).filter(Memory.memory_weight >= 9).label("very_high_weight_count"),
                )
                .filter_by(user_id=user_id)
                .first()
            )

            return jsonify(
                {
                    "success": True,
                    "statistics": {
                        "total_memories": stats.total_memories,
                        "average_weight": round(stats.avg_weight, 2) if stats.avg_weight else 0,
                        "min_weight": stats.min_weight,
                        "max_weight": stats.max_weight,
                        "high_weight_memories": stats.high_weight_count,
                        "very_high_weight_memories": stats.very_high_weight_count,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Error getting weight statistics: {e}")
            return jsonify({"error": f"Failed to get statistics: {str(e)}"}), 500


# Register the routes
memory_weighting_bp.add_url_rule("/weight-memory", view_func=WeightMemoryAPI.as_view("weight_memory"), methods=["POST"])
memory_weighting_bp.add_url_rule(
    "/weight-memories",
    view_func=WeightMultipleMemoriesAPI.as_view("weight_multiple_memories"),
    methods=["POST"],
)
memory_weighting_bp.add_url_rule(
    "/memories-by-weight",
    view_func=MemoriesByWeightAPI.as_view("memories_by_weight"),
    methods=["GET"],
)
memory_weighting_bp.add_url_rule(
    "/weight-stats",
    view_func=WeightStatisticsAPI.as_view("weight_statistics"),
    methods=["GET"],
)
