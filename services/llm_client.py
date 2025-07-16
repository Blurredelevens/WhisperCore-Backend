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

    def generate_reflection_and_weight(
        self,
        memory_content: str,
        tone: str = "empathetic",
        model: str = "llama3:8b",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> tuple[str, int]:
        """
        Generate both reflection and weight in a single LLM call

        Args:
            memory_content: The memory content to analyze
            tone: The AI confidant tone (empathetic, supportive, analytical, casual, professional)
            model: The model to use for generation
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds

        Returns:
            Tuple of (reflection_text, weight_number)
        """
        prompt = self._generate_ai_confidant_prompt(memory_content, tone)

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} to generate reflection and weight with tone: {tone}")

                # Use long polling method
                result = self.generate_with_long_polling(
                    prompt=prompt,
                    model=model,
                    max_retries=1,  # Single attempt since we're already in retry loop
                    retry_delay=retry_delay,
                )

                if result:
                    logger.info(f"Successfully generated reflection and weight with {len(result)} characters")
                    reflection, weight = self._extract_reflection_and_weight(result)
                    return reflection, weight
                else:
                    logger.warning("Generation returned empty response")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise ValueError("Generation did not complete successfully")

            except (requests.exceptions.RequestException, TimeoutError, ValueError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise

    def _extract_reflection_and_weight(self, response: str) -> tuple[str, int]:
        """Extract reflection text and weight number from LLM response"""
        try:
            logger.info(f"Raw LLM response: {response}")
            lines = response.strip().split("\n")
            reflection_lines = []
            weight = 0

            logger.info(f"Processing {len(lines)} lines from response")

            for i, line in enumerate(lines):
                line = line.strip()
                logger.info(f"Line {i}: '{line}'")

                if line.startswith("REFLECTION:"):
                    logger.info("Found REFLECTION: marker")
                    # Start collecting reflection text
                    continue
                elif line.startswith("WEIGHT:"):
                    logger.info(f"Found WEIGHT: marker in line: '{line}'")
                    # Extract weight number
                    weight_text = line.replace("WEIGHT:", "").strip()
                    logger.info(f"Weight text after cleanup: '{weight_text}'")
                    import re

                    numbers = re.findall(r"\b\d+\b", weight_text)
                    logger.info(f"Found numbers: {numbers}")
                    if numbers:
                        weight = int(numbers[0])
                        logger.info(f"Extracted weight: {weight}")
                        if not (1 <= weight <= 10):
                            logger.warning(f"Weight {weight} out of range, using default 5")
                            weight = 5
                    else:
                        logger.warning("No numbers found in WEIGHT line")
                    break
                elif (
                    line and not line.startswith("Weight Guidelines") and not line.startswith("Consider these factors")
                ):
                    # Add to reflection if it's not a header
                    reflection_lines.append(line)
                    logger.info(f"Added to reflection: '{line}'")

            reflection = "\n".join(reflection_lines).strip()

            # If no reflection was extracted, use the full response
            if not reflection:
                logger.warning("No reflection extracted, using full response")
                reflection = response.strip()

            logger.info(f"Final extracted reflection ({len(reflection)} chars): {reflection[:100]}...")
            logger.info(f"Final extracted weight: {weight}")
            return reflection, weight

        except Exception as e:
            logger.error(f"Error extracting reflection and weight from response: {e}")
            return response.strip(), 5

    def _generate_ai_confidant_prompt(self, memory_content: str, tone: str = "empathetic") -> str:
        """
        Generate AI confidant prompt for memory reflection and weighting

        Args:
            memory_content: The memory content to analyze
            tone: The AI confidant tone

        Returns:
            Formatted prompt string
        """
        return f"""
    You are WhisperCore, an AI confidant designed to help users process
    their daily experiences with emotional intelligence and personal growth insights.
    Think of yourself as a trusted friend who combines the simplicity of Daylio's mood
    tracking with deep, meaningful AI-powered reflection.

    Your role is to:
    - Capture the emotional essence of the user's experience
    - Provide thoughtful, personalized insights that encourage self-reflection
    - Help users recognize patterns, growth opportunities, and meaningful moments
    - Maintain a consistent, supportive presence that feels both human and intelligent

    Memory to reflect on: {memory_content}
    Your tone: {tone}

    Please respond in the following format:

    REFLECTION:
    [As WhisperCore, provide a {tone} reflection on this memory. Consider:
    - The emotional journey and impact of this experience
    - What this reveals about the user's values, growth, or patterns
    - Potential insights or learning opportunities
    - How this moment fits into their broader life narrative
    - Gentle encouragement or perspective that feels genuinely supportive

    Keep your response warm, insightful, and focused on the user's personal growth.
    Avoid generic advice - make it feel like you truly understand their unique experience.

    WEIGHT: [number]

    Weight Guidelines (1-10):
    - 1-2: Minor daily events, routine activities, simple pleasures
    - 3-4: Regular experiences with mild emotions, small wins or challenges
    - 5-6: Notable experiences with moderate emotions, learning moments
    - 7-8: Significant events with strong emotions, important insights or achievements
    - 9-10: Life-changing events, major achievements, profound insights, or deeply meaningful moments

    Consider these factors when assigning weight:
    - Emotional intensity and depth of feeling
    - Life impact and significance to the user's journey
    - Personal growth potential and learning value
    - Relationship importance and social connection
    - Achievement or milestone value
    - How this moment contributes to their overall well-being

    Return only the reflection text and weight number in the exact format above.
    """

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
