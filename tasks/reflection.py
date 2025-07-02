from celery import shared_task
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Dict, Any
from extensions import db
from models.reflection import Reflection
from models.user import User
from tasks.llm_service import LLMService

logger = logging.getLogger(__name__)

@shared_task
def generate_weekly_reflections():
    """Generate weekly reflections for all users."""
    try:
        logger.info("Starting weekly reflection generation...")
        
        # Get all active users
        users = User.query.filter_by(is_active=True).all()
        generated_count = 0
        
        llm_service = LLMService()
        
        # Calculate period for weekly reflection
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=7)
        period_end = now
        
        for user in users:
            try:
                # Generate reflection prompt
                reflection_prompt = f"""
                Generate a thoughtful weekly reflection for a user. 
                Consider themes of personal growth, learning, and self-awareness.
                Make it encouraging and insightful.
                Keep it concise but meaningful (2-3 paragraphs).
                """
                
                # Get LLM response
                result = llm_service.process_query(reflection_prompt)
                
                if "error" not in result:
                    # Create reflection record
                    reflection = Reflection(
                        user_id=user.id,
                        content=result.get("data", "Weekly reflection generated."),
                        reflection_type="weekly",
                        period_start=period_start,
                        period_end=period_end
                    )
                    
                    db.session.add(reflection)
                    generated_count += 1
                    logger.info(f"Generated weekly reflection for user {user.id}")
                else:
                    logger.error(f"Failed to generate reflection for user {user.id}: {result['error']}")
                    
            except Exception as e:
                logger.error(f"Error generating reflection for user {user.id}: {e}")
                continue
        
        # Commit all reflections
        db.session.commit()
        
        result = {
            "status": "success",
            "generated_count": generated_count,
            "total_users": len(users),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Weekly reflection generation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Weekly reflection generation failed: {e}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@shared_task
def generate_monthly_reflections():
    """Generate monthly reflections for all users."""
    try:
        logger.info("Starting monthly reflection generation...")
        
        # Get all active users
        users = User.query.filter_by(is_active=True).all()
        generated_count = 0
        
        llm_service = LLMService()
        
        # Calculate period for monthly reflection
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=30)
        period_end = now
        
        for user in users:
            try:
                # Generate reflection prompt
                reflection_prompt = f"""
                Generate a comprehensive monthly reflection for a user.
                This should be more detailed than a weekly reflection.
                Include themes of:
                - Personal achievements and milestones
                - Challenges overcome
                - Lessons learned
                - Goals for the next month
                - Overall personal growth assessment
                
                Make it inspiring and actionable (4-5 paragraphs).
                """
                
                # Get LLM response
                result = llm_service.process_query(reflection_prompt)
                
                if "error" not in result:
                    # Create reflection record
                    reflection = Reflection(
                        user_id=user.id,
                        content=result.get("data", "Monthly reflection generated."),
                        reflection_type="monthly",
                        period_start=period_start,
                        period_end=period_end
                    )
                    
                    db.session.add(reflection)
                    generated_count += 1
                    logger.info(f"Generated monthly reflection for user {user.id}")
                else:
                    logger.error(f"Failed to generate monthly reflection for user {user.id}: {result['error']}")
                    
            except Exception as e:
                logger.error(f"Error generating monthly reflection for user {user.id}: {e}")
                continue
        
        # Commit all reflections
        db.session.commit()
        
        result = {
            "status": "success",
            "generated_count": generated_count,
            "total_users": len(users),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Monthly reflection generation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Monthly reflection generation failed: {e}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@shared_task
def generate_personalized_reflection(user_id: int, reflection_type: str = "custom"):
    """Generate a personalized reflection for a specific user."""
    try:
        logger.info(f"Generating personalized reflection for user {user_id}")
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return {
                "status": "error",
                "error": "User not found",
                "timestamp": datetime.now().isoformat()
            }
        
        llm_service = LLMService()
        
        # Calculate period for personalized reflection
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=7)  # Default to weekly period
        period_end = now
        
        # Generate personalized prompt based on user data
        reflection_prompt = f"""
        Generate a personalized reflection for a user.
        This should be tailored and meaningful.
        
        Consider creating a reflection that:
        - Encourages self-reflection and growth
        - Provides actionable insights
        - Is motivational and positive
        - Relates to personal development themes
        
        Make it engaging and relevant (3-4 paragraphs).
        """
        
        # Get LLM response
        result = llm_service.process_query(reflection_prompt)
        
        if "error" not in result:
            # Create reflection record
            reflection = Reflection(
                user_id=user.id,
                content=result.get("data", "Personalized reflection generated."),
                reflection_type=reflection_type,
                period_start=period_start,
                period_end=period_end
            )
            
            db.session.add(reflection)
            db.session.commit()
            
            result = {
                "status": "success",
                "user_id": user_id,
                "reflection_id": reflection.id,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Generated personalized reflection for user {user_id}")
            return result
        else:
            logger.error(f"Failed to generate personalized reflection for user {user_id}: {result['error']}")
            return {
                "status": "error",
                "error": result['error'],
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Personalized reflection generation failed for user {user_id}: {e}")
        db.session.rollback()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        } 