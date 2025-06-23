from celery import shared_task
from extensions import celery
from groq import Groq
import os
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_query(self, query):
    logger.info(f"Starting process_query task with query: {query}")
    try:
        api_key = "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"
        logger.info(f"GROQ_API_KEY present: {bool(api_key)}")
        
        if not api_key:
            logger.error("GROQ_API_KEY not found in environment")
            raise ValueError("GROQ_API_KEY not found in environment")
            
        groq_client = Groq(
            api_key=api_key,
            base_url="https://api.groq.com/v1"
        )
        
        logger.info("Making request to Groq API...")
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=1024,
            stream=False
        )
        logger.info("Successfully received response from Groq API")
        return {"data": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"Error in process_query: {str(e)}", exc_info=True)
        return {"error": f"Error processing query: {str(e)}"}
