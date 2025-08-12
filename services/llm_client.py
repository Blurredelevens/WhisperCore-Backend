import json
import logging
import re
import time
from typing import Generator, List

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
    """HTTP client for LLM API with long polling and streaming support"""

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

    def generate_text_stream(
        self,
        prompt: str,
        model: str = "llama3:8b",
        images: List[str] = None,
    ) -> Generator[str, None, None]:
        """
        Generate text using the LLM API with streaming

        Args:
            prompt: The input prompt
            model: The model to use for generation
            images: Optional list of base64 encoded images for vision models

        Yields:
            Generated text chunks as they become available
        """
        # Validate request with Pydantic schema
        request_data = LLMGenerateRequest(model=model, prompt=prompt, stream=True, images=images)

        try:
            logger.info(f"Sending streaming request to LLM API: {self.base_url}/api/generate")

            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=request_data.model_dump(),
                timeout=self.timeout,
                stream=True,  # Enable streaming
            )
            response.raise_for_status()

            # Process streaming response
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse JSON from each line
                        data = json.loads(line.decode("utf-8"))

                        # Extract response text from streaming data
                        if "response" in data:
                            chunk = data["response"]
                            if chunk:
                                yield chunk

                        # Check if generation is complete
                        if data.get("done", False):
                            logger.info("Streaming generation completed")
                            break

                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse streaming response: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing streaming chunk: {e}")
                        continue

        except requests.exceptions.Timeout:
            logger.error("LLM API streaming request timed out")
            raise TimeoutError("LLM API streaming request timed out")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling LLM API streaming: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise

    def generate_text(
        self,
        prompt: str,
        model: str = "llama3:8b",
        stream: bool = False,
        images: List[str] = None,
    ) -> LLMGenerateResponse:
        """
        Generate text using the LLM API with long polling

        Args:
            prompt: The input prompt
            model: The model to use for generation
            stream: Whether to stream the response
            images: Optional list of base64 encoded images for vision models

        Returns:
            LLMGenerateResponse containing the generated response
        """
        # Validate request with Pydantic schema
        request_data = LLMGenerateRequest(model=model, prompt=prompt, stream=stream, images=images)

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
        images: List[str] = None,
    ) -> str:
        """
        Generate text with long polling and retry logic

        Args:
            prompt: The input prompt
            model: The model to use for generation
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            images: Optional list of base64 encoded images for vision models

        Returns:
            Generated text response
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} to generate text")

                result = self.generate_text(prompt, model, stream=False, images=images)

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

    def generate_reflection_and_weight_stream(
        self,
        memory_content: str,
        tone: str = "empathetic",
        model: str = "llama3:8b",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        image_base64: str = None,
    ) -> Generator[dict, None, None]:
        """
        Generate both reflection and weight with streaming support, improved whitespace handling.

        Args:
            memory_content: The memory content to analyze
            tone: The AI confidant tone (empathetic, supportive, analytical, casual,
            professional, Happy, Sad, Angry, Harsh etc)
            model: The model to use for generation
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            image_base64: Optional base64 string of an attached image

        Yields:
            Dictionary with streaming data: {"type": "chunk", "content": "...", "done": False}
        """
        # Check if this is a vision model
        is_vision_model = any(
            vision_model in model.lower()
            for vision_model in ["vision", "llava", "llama3.1", "claude", "gpt-4v", "gemini"]
        )

        if is_vision_model and image_base64:
            # For vision models, pass images separately and don't include in prompt
            prompt = self._generate_ai_confidant_prompt(memory_content, tone)
            images = [image_base64]
        else:
            # For text-only models, include image as base64 in prompt (current behavior)
            prompt = self._generate_ai_confidant_prompt(memory_content, tone, image_base64=image_base64)
            images = None

        print("Prompt", prompt)

        for attempt in range(max_retries):
            try:
                # Use streaming method with buffer to catch weight text that spans chunks
                full_response = ""
                buffer = ""
                for chunk in self.generate_text_stream(prompt=prompt, model=model, images=images):
                    full_response += chunk
                    buffer += chunk

                    # Remove ANY text containing "weight" (case insensitive)
                    filtered_buffer = re.sub(r"[^.]*weight[^.]*\.?", "", buffer, flags=re.IGNORECASE)

                    # Remove "weighs in at" and similar phrases
                    filtered_buffer = re.sub(r"[^.]*weighs?[^.]*\.?", "", filtered_buffer, flags=re.IGNORECASE)

                    # Remove tags section (TAGS: tag1, tag2, tag3)
                    filtered_buffer = re.sub(r"TAGS:\s*.+", "", filtered_buffer, flags=re.IGNORECASE)

                    # Also remove standalone numbers 1-10 that might be weight indicators
                    filtered_buffer = re.sub(r"\b([1-9]|10)\b", "", filtered_buffer)

                    # Remove leftover asterisks from bold formatting
                    filtered_buffer = re.sub(r"\*+$", "", filtered_buffer)

                    # Check for non-empty, non-whitespace content
                    if filtered_buffer.strip():
                        yield {
                            "type": "chunk",
                            "content": filtered_buffer,
                            "done": False,
                            "attempt": attempt + 1,
                            "tone": tone,
                        }
                        buffer = ""

                # After the streaming loop completes, process the full response
                if full_response:
                    reflection, weight, tags = self._extract_reflection_weight_and_tags(full_response)
                    reflection = re.sub(r"[^.]*weight[^.]*\.?", "", reflection, flags=re.IGNORECASE)
                    reflection = re.sub(r"[^.]*weighs?[^.]*\.?", "", reflection, flags=re.IGNORECASE)
                    reflection = re.sub(r"\b([1-9]|10)\b", "", reflection)
                    reflection = re.sub(r"\*+$", "", reflection)

                    yield {
                        "type": "complete",
                        "reflection": reflection,
                        "weight": weight,
                        "tags": tags,
                        "done": True,
                        "attempt": attempt + 1,
                        "tone": tone,
                    }
                    return
                else:
                    logger.warning("Streaming generation returned empty response")
                    yield {
                        "type": "complete",
                        "reflection": "",
                        "weight": 0,
                        "tags": [],
                        "done": True,
                        "attempt": attempt + 1,
                        "tone": tone,
                    }
                    return

            except (requests.exceptions.RequestException, TimeoutError, ValueError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                yield {"type": "error", "error": str(e), "attempt": attempt + 1, "done": True}
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise

    def generate_reflection_weight_and_tags(
        self,
        memory_content: str,
        tone: str = "empathetic",
        model: str = "llama3:8b",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        image_base64: str = None,
    ) -> tuple[str, int, list[str]]:
        """
        Generate reflection, weight, and tags in a single LLM call

        Args:
            memory_content: The memory content to analyze
            tone: The AI confidant tone (empathetic, supportive, analytical, casual, professional)
            model: The model to use for generation
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            image_base64: Optional base64 string of an attached image

        Returns:
            Tuple of (reflection_text, weight_number, tags_list)
        """
        # Check if this is a vision model
        is_vision_model = any(
            vision_model in model.lower()
            for vision_model in ["vision", "llava", "llama3.1", "claude", "gpt-4v", "gemini"]
        )

        if is_vision_model and image_base64:
            # For vision models, pass images separately and don't include in prompt
            prompt = self._generate_ai_confidant_prompt(memory_content, tone)
            images = [image_base64]
        else:
            # For text-only models, include image as base64 in prompt (current behavior)
            prompt = self._generate_ai_confidant_prompt(memory_content, tone, image_base64=image_base64)
            images = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} to generate reflection and weight with tone: {tone}")

                # Use long polling method
                result = self.generate_with_long_polling(
                    prompt=prompt,
                    model=model,
                    max_retries=1,
                    retry_delay=retry_delay,
                    images=images,
                )

                if result:
                    logger.info(f"Successfully generated reflection and weight with {len(result)} characters")
                    reflection, weight, tags = self._extract_reflection_weight_and_tags(result)
                    return reflection, weight, tags
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

    def _extract_reflection_weight_and_tags(self, response: str) -> tuple[str, int, list[str]]:
        """Extract reflection text, weight number, and tags from LLM response"""
        try:
            logger.info(f"Raw LLM response: {response}")

            # Look for various weight patterns in the response
            weight = 0
            tags = []
            reflection = response.strip()

            # Extract tags first (TAGS: tag1, tag2, tag3)
            tags_match = re.search(r"TAGS:\s*(.+)", response, re.IGNORECASE)
            if tags_match:
                tags_text = tags_match.group(1).strip()
                # Split by comma and clean up each tag
                tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
                logger.info(f"Found tags: {tags}")
                # Remove the tags section from reflection
                reflection = re.sub(r"TAGS:\s*.+", "", reflection, flags=re.IGNORECASE)

            # Pattern 1: "Weight: X" or "**Weight: X**"
            weight_match = re.search(r"\*?\*?Weight:\s*(\d+)\*?\*?", response, re.IGNORECASE)
            if weight_match:
                weight = int(weight_match.group(1))
                logger.info(f"Found weight pattern 1: {weight}")
                # Remove the weight pattern
                reflection = re.sub(r"\*?\*?Weight:\s*\d+\*?\*?", "", reflection, flags=re.IGNORECASE)

            # Pattern 2: "This memory holds a weight of X"
            if weight == 0:
                weight_match = re.search(r"This memory holds a weight of (\d+)", response, re.IGNORECASE)
                if weight_match:
                    weight = int(weight_match.group(1))
                    logger.info(f"Found weight pattern 2: {weight}")
                    # Remove the weight pattern
                    reflection = re.sub(r"This memory holds a weight of \d+\.?", "", reflection, flags=re.IGNORECASE)

            # Pattern 3: Standalone number at the end (1-10)
            if weight == 0:
                weight_match = re.search(r"\b([1-9]|10)\s*$", response.strip())
                if weight_match:
                    weight = int(weight_match.group(1))
                    logger.info(f"Found weight pattern 3: {weight}")
                    # Remove the number at the end
                    reflection = re.sub(r"\b([1-9]|10)\s*$", "", reflection.strip())

            # Validate weight range
            if weight > 0 and not (1 <= weight <= 10):
                logger.warning(f"Weight {weight} out of range, using default 0")
                weight = 0

            # Final cleanup of reflection
            reflection = reflection.strip()

            # If no reflection was extracted, use the full response
            if not reflection:
                logger.warning("No reflection extracted, using full response")
                reflection = response.strip()

            logger.info(f"Final extracted reflection ({len(reflection)} chars): {reflection[:100]}...")
            logger.info(f"Final extracted weight: {weight}")
            logger.info(f"Final extracted tags: {tags}")
            return reflection, weight, tags

        except Exception as e:
            logger.error(f"Error extracting reflection, weight, and tags from response: {e}")
            return response.strip(), 0, []

    def _generate_ai_confidant_prompt(
        self,
        memory_content: str,
        tone: str = "empathetic",
        image_base64: str = None,
    ) -> str:
        """
        Generate AI confidant prompt for memory reflection and weighting

        Args:
            memory_content: The memory content to analyze
            tone: The AI confidant tone  (empathetic, supportive, analytical, casual,
            professional, Happy, Sad, Angry, Harsh etc)
            image_base64: Optional base64 string of an attached image

        Returns:
            Formatted prompt string
        """
        image_section = f"\nAttached image (base64): {image_base64}\n" if image_base64 else ""
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
    {image_section}

    Please provide a {tone} reflection on this memory. Consider:
    - The emotional journey and impact of this experience
    - What this reveals about the user's values, growth, or patterns
    - Potential insights or learning opportunities
    - How this moment fits into their broader life narrative
    - Gentle encouragement or perspective that feels genuinely supportive

    Keep your response warm, insightful, and focused on the user's personal growth.
    Avoid generic advice - make it feel like you truly understand their unique experience.

    Weight Guidelines (1-10):
    - 1-2: Minor daily events, routine activities, simple pleasures, Sad, Angry, Harsh
    - 3-4: Regular experiences with mild emotions, small wins or challenges, Happy, Sad, Angry, Harsh
    - 5-6: Notable experiences with moderate emotions,
    learning moments, Happy, Sad, Angry, Harsh
    - 7-8: Significant events with strong emotions,
    important insights or achievements, Happy, Sad, Angry, Harsh
    - 9-10: Life-changing events, major achievements,
    profound insights, or deeply meaningful moments, Happy, Sad, Angry, Harsh

    Consider these factors when assigning weight:
    - Emotional intensity and depth of feeling
    - Life impact and significance to the user's journey
    - Personal growth potential and learning value
    - Relationship importance and social connection
    - Achievement or milestone value
    - How this moment contributes to their overall well-being

    TAGS: After your reflection, provide 3-5 relevant tags
    that capture the key themes, emotions, or categories of this memory.
    Use simple, descriptive words or short phrases separated by commas.

    FORMAT:
    1. Write your reflection
    2. Add a single number (1-10) for weight
    3. Add tags in format: TAGS: tag1, tag2, tag3
    """

    def health_check(self) -> bool:
        """Check if the LLM API is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                LLMModelsResponse(**data)
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
