import logging
from datetime import datetime
from typing import Dict, List

from models import Memory, User

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting user data in various formats."""

    @staticmethod
    def export_user_memories_json(user_id: int, encryption_key: str) -> Dict:
        """
        Export user memories in JSON format.

        Args:
            user_id: The user ID to export memories for
            encryption_key: The encryption key to decrypt memory content

        Returns:
            Dictionary containing the export data
        """
        try:
            # Get user and their memories
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")

            memories = Memory.query.filter_by(user_id=user_id).order_by(Memory.created_at.desc()).all()

            # Prepare export data
            export_data = {
                "export_info": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                    "user_email": user.email,
                    "user_name": user.full_name,
                    "total_memories": len(memories),
                    "format": "json",
                },
                "memories": [],
            }

            # Process each memory
            for memory in memories:
                try:
                    memory_data = memory.to_dict(encryption_key)
                    export_data["memories"].append(memory_data)
                except Exception as e:
                    logger.error(f"Error processing memory {memory.id}: {e}")
                    # Add memory with error info
                    export_data["memories"].append(
                        {
                            "id": memory.id,
                            "error": f"Failed to decrypt memory: {str(e)}",
                            "created_at": memory.created_at.isoformat() if memory.created_at else None,
                            "tags": memory.tags.split(",") if memory.tags else [],
                            "mood_emoji": memory.mood_emoji,
                            "is_bookmarked": memory.is_bookmarked,
                            "memory_weight": memory.memory_weight,
                        },
                    )

            return export_data

        except Exception as e:
            logger.error(f"Error exporting user memories: {e}")
            raise

    @staticmethod
    def export_user_memories_txt(user_id: int, encryption_key: str) -> str:
        """
        Export user memories in human-readable TXT format.

        Args:
            user_id: The user ID to export memories for
            encryption_key: The encryption key to decrypt memory content

        Returns:
            String containing the formatted export data
        """
        try:
            # Get user and their memories
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")

            memories = Memory.query.filter_by(user_id=user_id).order_by(Memory.created_at.desc()).all()

            # Build the text content
            lines = []

            # Header
            lines.append("=" * 80)
            lines.append("WHISPERCORE - MEMORY EXPORT")
            lines.append("=" * 80)
            lines.append(f"User: {user.full_name} ({user.email})")
            lines.append(f"Export Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            lines.append(f"Total Memories: {len(memories)}")
            lines.append("")

            if not memories:
                lines.append("No memories found.")
                return "\n".join(lines)

            # Process each memory
            for i, memory in enumerate(memories, 1):
                lines.append("-" * 60)
                lines.append(f"MEMORY #{i} (ID: {memory.id})")
                lines.append("-" * 60)

                # Basic info
                lines.append(
                    f"Date: {memory.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if memory.created_at else 'Unknown'}",
                )

                # Tags
                if memory.tags:
                    tags = [tag.strip() for tag in memory.tags.split(",") if tag.strip()]
                    if tags:
                        lines.append(f"Tags: {', '.join(tags)}")

                # Memory weight
                if memory.memory_weight > 0:
                    lines.append(f"Memory Weight: {memory.memory_weight}/10")

                # Bookmarked status
                if memory.is_bookmarked:
                    lines.append("Bookmarked: Yes")

                # Content
                lines.append("")
                lines.append("CONTENT:")
                lines.append("-" * 20)
                try:
                    content = memory._decrypt(memory.encrypted_content, encryption_key)
                    if content:
                        lines.append(content)
                    else:
                        lines.append("[Content could not be decrypted]")
                except Exception as e:
                    lines.append(f"[Error decrypting content: {str(e)}]")

                # Model response
                try:
                    model_response = memory._decrypt(memory.model_response, encryption_key)
                    if model_response:
                        lines.append("")
                        lines.append("AI REFLECTION:")
                        lines.append("-" * 20)
                        lines.append(model_response)
                except Exception:
                    # Silently skip model response if it can't be decrypted
                    pass

                lines.append("")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error exporting user memories to TXT: {e}")
            raise

    @staticmethod
    def get_export_formats() -> List[Dict[str, str]]:
        """Get available export formats."""
        return [
            {
                "format": "json",
                "extension": ".json",
                "description": "Structured JSON format with all memory data",
                "content_type": "application/json",
            },
            {
                "format": "txt",
                "extension": ".txt",
                "description": "Human-readable text format",
                "content_type": "text/plain",
            },
        ]
