import logging
from datetime import datetime

from extensions import db
from models import Memory, Reflection, User
from services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating user summaries"""

    def __init__(self):
        self.llm_client = get_llm_client()

    def get_memories_for_period(self, user_id: int, start_date: datetime, end_date: datetime) -> list:
        """Get memories for a user within a date range"""
        model_key = self._get_user_model_key(user_id)
        memories = (
            Memory.query.filter_by(user_id=user_id)
            .filter(Memory.created_at >= start_date)
            .filter(Memory.created_at <= end_date)
            .order_by(Memory.created_at.desc())
            .all()
        )

        logger.info(
            f"Found {len(memories)} memories for user {user_id} from "
            f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        )

        memory_texts = []
        successful_decryptions = 0
        failed_decryptions = 0

        for memory in memories:
            try:
                val = memory.get_model_response(model_key)
                if val:
                    memory_texts.append(val)
                    successful_decryptions += 1
                else:
                    logger.warning(f"Memory {memory.id} returned None after decryption")
                    failed_decryptions += 1
            except Exception as e:
                logger.error(f"Decryption failed for memory {memory.id}: {e}")
                failed_decryptions += 1

        logger.info(
            f"Successfully decrypted {successful_decryptions} memories, "
            f"failed {failed_decryptions} for user {user_id}",
        )
        return memory_texts

    def generate_summary(self, memories: list, start_date: datetime, end_date: datetime, summary_type: str) -> str:
        """Generate summary from memories using LLM with long polling"""
        if not memories:
            return None

        joined_memories = "\n".join(memories)
        prompt = (
            f"Summarize the following memories from {start_date.strftime('%Y-%m-%d')} "
            f"to {end_date.strftime('%Y-%m-%d')}:\n{joined_memories}"
        )

        try:
            logger.info(f"Generating {summary_type} summary with {len(memories)} memories")
            summary = self.llm_client.generate_with_long_polling(
                prompt=prompt,
                model="llama3:8b",
                max_retries=3,
                retry_delay=1.0,
            )
            logger.info(f"Successfully generated {summary_type} summary")
            return summary
        except Exception as e:
            logger.error(f"Error generating {summary_type} summary: {e}")
            return None

    def save_reflection(
        self,
        user_id: int,
        content: str,
        reflection_type: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Reflection:
        """Save reflection to database"""
        reflection = Reflection(
            user_id=user_id,
            content=content,
            reflection_type=reflection_type,
            period_start=start_date,
            period_end=end_date,
        )
        db.session.add(reflection)
        db.session.commit()
        return reflection

    def get_users_by_summary_type(self, summary_type: str) -> list:
        """Get users who have a specific summary type enabled"""
        if summary_type == "weekly":
            return User.query.filter_by(is_active=True, weekly_summary_enabled=True).all()
        elif summary_type == "monthly":
            return User.query.filter_by(is_active=True, monthly_summary_enabled=True).all()
        else:
            return []

    def _get_user_model_key(self, user_id: int) -> bytes:
        """Get user's model key for decryption"""
        user = db.session.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return None
        return user.model_key.encode()
