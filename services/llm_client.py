import logging
import time

import requests

from schemas.llm import LLMGenerateRequest, LLMGenerateResponse, LLMModelsResponse

# Configure logging for Docker
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add console handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class LLMClient:
    """HTTP client for LLM API with long polling support"""

    def __init__(self, base_url: str, timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def get_models(self) -> LLMModelsResponse:
        """Get available models from the LLM API"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=30)
            response.raise_for_status()

            # Validate response with Pydantic schema
            data = response.json()
            models_response = LLMModelsResponse(**data)
            logger.info(f"Retrieved {len(models_response.models)} models from LLM API")
            return models_response

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting models: {e}")
            raise
        except Exception as e:
            logger.error(f"Error validating models response: {e}")
            raise

    def generate_text(self, prompt: str, model: str = "llama3:8b", stream: bool = False) -> LLMGenerateResponse:
        """
        Generate text using the LLM API with long polling

        Args:
            prompt: The input prompt
            model: The model to use for generation
            stream: Whether to stream the response

        Returns:
            LLMGenerateResponse containing the generated response
        """
        # Validate request with Pydantic schema
        request_data = LLMGenerateRequest(model=model, prompt=prompt, stream=stream)

        try:
            logger.info(f"Sending request to LLM API: {self.base_url}/api/generate")
            logger.info(f"Request payload: {request_data.model_dump()}")

            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=request_data.model_dump(),
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Validate response with Pydantic schema
            data = response.json()
            generate_response = LLMGenerateResponse(**data)
            logger.info(f"LLM API response received: {generate_response.model} - Done: {generate_response.done}")
            return generate_response

        except requests.exceptions.Timeout:
            logger.error("LLM API request timed out")
            raise TimeoutError("LLM API request timed out")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling LLM API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error validating LLM API response: {e}")
            raise

    def generate_with_long_polling(
        self,
        prompt: str,
        model: str = "llama3:8b",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> str:
        """
        Generate text with long polling and retry logic

        Args:
            prompt: The input prompt
            model: The model to use for generation
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds

        Returns:
            Generated text response
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} to generate text")

                result = self.generate_text(prompt, model, stream=False)

                # Extract the response text from the validated result
                if result.done and result.response:
                    logger.info(f"Successfully generated text with {len(result.response)} characters")
                    return result.response
                else:
                    logger.warning(f"Generation not complete or empty response: done={result.done}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise ValueError("Generation did not complete successfully")

            except (requests.exceptions.RequestException, TimeoutError, ValueError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise

    def health_check(self) -> bool:
        """Check if the LLM API is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                # Try to validate the response
                data = response.json()
                LLMModelsResponse(**data)  # This will raise if invalid
                return True
            return False
        except (requests.exceptions.RequestException, Exception):
            return False


def get_llm_client() -> LLMClient:
    """Factory function to get LLM client with config from AppConfig"""
    try:
        # Get config directly from AppConfig
        from config import EnvConfig

        config = EnvConfig()
        base_url = config.LLM_API_URL
        logger.info(f"Using LLM API URL from AppConfig: {base_url}")

        return LLMClient(base_url)
    except Exception as e:
        # Fallback to default if AppConfig fails
        logger.warning(f"Failed to get config from AppConfig: {e}, using default LLM API URL")
        return LLMClient("http://localhost:8000")
