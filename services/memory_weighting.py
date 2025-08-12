import logging

from services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class MemoryWeightingService:
    """Service for weighting memories using LLM analysis"""

    def __init__(self):
        self.llm_client = get_llm_client()

    def weight_memory(self, memory_content: str, tone: str = "empathetic") -> int:
        """Analyze memory content and return a weight from 1-10"""
        try:
            logger.info(f"Analyzing memory weight for content: {memory_content[:100]}...")

            # Use the new single call method that generates both reflection and weight
            reflection, weight = self.llm_client.generate_reflection_and_weight(
                memory_content=memory_content,
                tone=tone,
                model="llama3:8b",
                max_retries=3,
                retry_delay=1.0,
            )

            logger.info(f"Assigned weight {weight} to memory")
            return weight

        except Exception as e:
            logger.error(f"Error weighting memory: {e}")
            # Return default weight of 5 if analysis fails
            return 5

    def batch_weight_memories(self, memories: list) -> list:
        """Weight multiple memories in batch"""
        weighted_memories = []

        for memory in memories:
            try:
                weight = self.weight_memory(memory)
                weighted_memories.append({"content": memory, "weight": weight})
                logger.info(f"Successfully weighted memory with weight {weight}")
            except Exception as e:
                logger.error(f"Failed to weight memory: {e}")
                # Add with default weight
                weighted_memories.append({"content": memory, "weight": 5})

        return weighted_memories


def get_memory_weighting_service() -> MemoryWeightingService:
    """Factory function to get memory weighting service"""
    return MemoryWeightingService()
