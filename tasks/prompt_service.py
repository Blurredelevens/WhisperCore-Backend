import logging
from datetime import datetime, timedelta, timezone

from extensions import db
from models import Memory, Prompt, Reflection, User
from services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class PromptService:
    """Service for managing daily prompts"""

    def __init__(self):
        self.llm_client = get_llm_client()

    def get_active_users(self) -> list:
        """Get all active users"""
        return User.query.filter_by(is_active=True).all()

    def get_user_reflections(self, user_id: int, limit: int = 5) -> list:
        """Get recent reflections for a user"""
        return Reflection.query.filter_by(user_id=user_id).order_by(Reflection.created_at.desc()).limit(limit).all()

    def get_user_recent_memories(self, user_id: int, days: int = 1) -> list:
        """Get recent memories for a user from the past specified days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            Memory.query.filter_by(user_id=user_id)
            .filter(Memory.created_at >= cutoff_date)
            .order_by(Memory.created_at.desc())
            .all()
        )

    def get_user_context(self, user: User) -> str:
        """Get user context including reflections and recent memories"""
        reflections = self.get_user_reflections(user.id)
        memories = self.get_user_recent_memories(user.id)

        context_parts = []

        # Add user info
        context_parts.append(f"User: {user.first_name} {user.last_name} ({user.email})")

        # Add reflections if available
        if reflections:
            context_parts.append("\nRecent Reflections:")
            for reflection in reflections:
                period_range = (
                    f"{reflection.period_start.strftime('%Y-%m-%d')} to "
                    f"{reflection.period_end.strftime('%Y-%m-%d')}"
                )
                reflection_preview = f"{reflection.content[:200]}..."
                context_parts.append(f"- {reflection.reflection_type.title()} ({period_range}): {reflection_preview}")

        # Add recent memories if no reflections or as additional context
        if memories:
            context_parts.append("\nRecent Memories:")
            for memory in memories:
                try:
                    # Decrypt memory content
                    content = memory._decrypt(memory.encrypted_content, user.encryption_key.encode())
                    if content:
                        memory_time = memory.created_at.strftime("%Y-%m-%d %H:%M")
                        memory_preview = f"{content[:150]}..."
                        context_parts.append(f"- {memory_time}: {memory_preview}")
                except Exception as e:
                    logger.warning(f"Failed to decrypt memory {memory.id} for user {user.id}: {e}")

        return "\n".join(context_parts)

    def create_llm_prompt(self, user_context: str) -> str:
        """Create the LLM prompt for generating personalized conversation starters"""
        return f"""You are a personal AI confidant and assistant. Based on the following user information,
            generate 10 thoughtful, personalized conversation starters or prompts that would help this person reflect,
            grow, or explore their thoughts and feelings.

            User Context:
            {user_context}

            Generate 10 diverse prompts that could include:
            - Questions about their recent experiences and feelings
            - Prompts for self-reflection and personal growth
            - Creative or imaginative scenarios
            - Questions about their goals, dreams, or challenges
            - Prompts for gratitude or positive thinking
            - Questions about relationships or social interactions
            - Prompts for problem-solving or decision-making

            Make the prompts personal, empathetic, and varied. They should feel like they're coming
            from a caring friend or therapist who knows them well.

            Return only the 10 prompts, one per line, without numbering or additional text."""

    def generate_personalized_prompts(self, user: User) -> list:
        """Generate personalized prompts using LLM"""
        user_context = self.get_user_context(user)
        prompt = self.create_llm_prompt(user_context)

        try:
            response = self.llm_client.generate_with_long_polling(
                prompt=prompt,
                model="llama3:8b",
                max_retries=3,
                retry_delay=1.0,
            )

            if response:
                # Split response into individual prompts and clean them up
                prompts = [line.strip() for line in response.strip().split("\n") if line.strip()]
                # Take first 10 prompts if more were generated
                return prompts[:10]
            else:
                logger.error(f"LLM returned empty response for user {user.id}")
                return []

        except Exception as e:
            logger.error(f"Error generating prompts for user {user.id}: {e}")
            return []

    def create_daily_prompt_for_user(self, user_id: int, prompt_text: str) -> Prompt:
        """Create a daily prompt for a specific user"""
        try:
            prompt = Prompt.create_daily_prompt(user_id, prompt_text)
            logger.info(f"Successfully created daily prompt for user {user_id}")
            return prompt
        except Exception as e:
            logger.error(f"Error creating daily prompt for user {user_id}: {e}")
            raise

    def create_personalized_prompt_for_user(self, user_id: int, prompt_text: str) -> Prompt:
        """Create a personalized prompt for a specific user (allows multiple per day)"""
        try:
            personalized_prompt = Prompt.create_personalized_prompt(user_id, prompt_text)
            logger.info(f"Successfully created personalized prompt for user {user_id}")
            return personalized_prompt
        except Exception as e:
            logger.error(f"Error creating personalized prompt for user {user_id}: {e}")
            raise

    def create_daily_prompts_for_all_users(self) -> dict:
        """Create personalized daily prompts for all active users using LLM"""
        users = self.get_active_users()

        if not users:
            return {"success": False, "message": "No active users found"}

        successful_prompts = 0
        failed_prompts = 0
        total_prompts_generated = 0

        for user in users:
            try:
                # Generate personalized prompts using LLM
                personalized_prompts = self.generate_personalized_prompts(user)

                if personalized_prompts:
                    # Create a prompt for each generated suggestion
                    for prompt_text in personalized_prompts:
                        self.create_personalized_prompt_for_user(user.id, prompt_text)
                        total_prompts_generated += 1

                    successful_prompts += 1
                    logger.info(
                        f"Created {len(personalized_prompts)} personalized prompts for user {user.id} ({user.email})",
                    )
                else:
                    failed_prompts += 1
                    logger.warning(f"No personalized prompts generated for user {user.id} ({user.email})")

            except Exception as e:
                failed_prompts += 1
                logger.error(f"Error creating personalized prompts for user {user.id} ({user.email}): {e}")
                db.session.rollback()

        return {
            "success": True,
            "successful_prompts": successful_prompts,
            "failed_prompts": failed_prompts,
            "total_prompts_generated": total_prompts_generated,
            "message": f"Generated {total_prompts_generated} personalized prompts for {successful_prompts} users",
        }
