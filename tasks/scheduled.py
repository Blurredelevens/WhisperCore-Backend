from celery import shared_task
import time
from tasks.llm_service import LLMService
import logging
from models import User, Reflection
import json
from datetime import datetime, timezone
from routes.summary import get_recent_memories, build_summary_prompt
from models.prompt import Prompt
from extensions import db, redis_client

logger = logging.getLogger(__name__)

@shared_task
def heartbeat():
    print(f"Heartbeat - {time.ctime()}")
    """Simple heartbeat task to verify Celery is working."""
    return "heartbeat"

@shared_task(name="tasks.scheduled.process_query_task")
def process_query_task(query_data):
    try:
            llm_service = LLMService()
            
            if isinstance(query_data, dict):
                query = query_data.get("query", "")
            else:
                query = query_data

            result = llm_service.process_query(query)
            print(f"Query task completed successfully, result: {result}")
            logger.info(f"Query task completed successfully")
            return result
    except Exception as e:
        logger.error(f"Error in process_query_task: {str(e)}")
        return f"Error processing query: {str(e)}"


@shared_task(name="tasks.scheduled.generate_weekly_summary")
def generate_weekly_summary():
    """Generate weekly summary for all users."""
    try:
            
            # Get all users
            users = User.query.all()
            
            for user in users:
                try:
                    # Use the same logic as the API endpoint
                    memories = get_recent_memories(user.id, count=7)
                    
                    if memories:
                        # Build prompt using the same function
                        prompt = build_summary_prompt(memories, "weekly")
                        
                        # Generate summary
                        llm_service = LLMService()
                        summary = llm_service.process_query(prompt)
                        
                        # Extract summary text (same logic as API)
                        summary_text = None
                        if isinstance(summary, dict) and 'data' in summary and isinstance(summary['data'], dict) and 'text' in summary['data']:
                            summary_text = summary['data']['text']
                        elif isinstance(summary, dict) and 'text' in summary:
                            summary_text = summary['text']
                        elif isinstance(summary, str):
                            summary_text = summary
                        else:
                            summary_text = str(summary)
                        
                        # Save to Reflection model
                        now = datetime.now(timezone.utc)
                        reflection = Reflection(
                            user_id=user.id,
                            content=summary_text,
                            reflection_type="weekly",
                            period_start=now,
                            period_end=now
                        )
                        db.session.add(reflection)
                        db.session.commit()
                        
                        print(f"Weekly summary generated for user {user.id}")
                    else:
                        print(f"No memories found for user {user.id}")
                        
                except Exception as e:
                    print(f"Error generating weekly summary for user {user.id}: {e}")
                    db.session.rollback()
            
            print("Weekly summary generation completed")
            return "Weekly summaries generated successfully"
            
    except Exception as e:
        print(f"Error in generate_weekly_summary: {str(e)}")
        logger.error(f"Error in generate_weekly_summary: {str(e)}")
        return f"Error generating weekly summaries: {str(e)}"

@shared_task(name="tasks.scheduled.generate_monthly_summary")
def generate_monthly_summary():
    """Generate monthly summary for all users."""
    try:
            
            # Import the summary functions from routes
            from routes.summary import get_recent_memories, build_summary_prompt
            
            # Get all users
            users = User.query.all()
            
            for user in users:
                try:
                    # Use the same logic as the API endpoint
                    memories = get_recent_memories(user.id, count=30)
                    
                    if memories:
                        # Build prompt using the same function
                        prompt = build_summary_prompt(memories, "monthly")
                        
                        # Generate summary
                        llm_service = LLMService()
                        summary = llm_service.process_query(prompt)
                        
                        # Extract summary text (same logic as API)
                        summary_text = None
                        if isinstance(summary, dict) and 'data' in summary and isinstance(summary['data'], dict) and 'text' in summary['data']:
                            summary_text = summary['data']['text']
                        elif isinstance(summary, dict) and 'text' in summary:
                            summary_text = summary['text']
                        elif isinstance(summary, str):
                            summary_text = summary
                        else:
                            summary_text = str(summary)
                        
                        # Save to Reflection model
                        now = datetime.now(timezone.utc)
                        reflection = Reflection(
                            user_id=user.id,
                            content=summary_text,
                            reflection_type="monthly",
                            period_start=now,
                            period_end=now
                        )
                        db.session.add(reflection)
                        db.session.commit()
                        
                        print(f"Monthly summary generated for user {user.id}")
                    else:
                        print(f"No memories found for user {user.id}")
                        
                except Exception as e:
                    print(f"Error generating monthly summary for user {user.id}: {e}")
                    db.session.rollback()
            
            print("Monthly summary generation completed")
            return "Monthly summaries generated successfully"
            
    except Exception as e:
        print(f"Error in generate_monthly_summary: {str(e)}")
        logger.error(f"Error in generate_monthly_summary: {str(e)}")
        return f"Error generating monthly summaries: {str(e)}"

@shared_task(name="tasks.scheduled.send_daily_prompt")
def send_daily_prompt():
        prompt = Prompt.query.filter_by(is_active=True).order_by(db.func.random()).first()
        if prompt:
            # Store in Redis for the day
            redis_client.set('daily_prompt', prompt.text)
            print(f"Set daily prompt: {prompt.text}")
        else:
            print("No active prompt found.")
