import logging

from extensions import db
from models import Prompt, User

logger = logging.getLogger(__name__)


class PromptService:
    """Service for managing daily prompts"""

    def get_active_users(self) -> list:
        """Get all active users"""
        return User.query.filter_by(is_active=True).all()

    def get_random_active_prompt(self) -> Prompt:
        """Get a random active prompt template"""
        return Prompt.query.filter_by(is_active=True).order_by(db.func.random()).first()

    def create_daily_prompt_for_user(self, user_id: int, prompt_text: str) -> Prompt:
        """Create a daily prompt for a specific user"""
        return Prompt.create_daily_prompt(user_id, prompt_text)

    def create_daily_prompts_for_all_users(self) -> dict:
        """Create daily prompts for all active users"""
        users = self.get_active_users()
        prompt_template = self.get_random_active_prompt()

        if not prompt_template:
            return {"success": False, "message": "No active prompt template found"}

        if not users:
            return {"success": False, "message": "No active users found"}

        successful_prompts = 0
        failed_prompts = 0

        for user in users:
            try:
                self.create_daily_prompt_for_user(user.id, prompt_template.text)
                successful_prompts += 1
                logger.info(f"Created daily prompt for user {user.id} ({user.email})")
            except Exception as e:
                failed_prompts += 1
                logger.error(f"Error creating daily prompt for user {user.id} ({user.email}): {e}")
                db.session.rollback()

        return {
            "success": True,
            "successful_prompts": successful_prompts,
            "failed_prompts": failed_prompts,
            "prompt_text": prompt_template.text[:100],
        }
