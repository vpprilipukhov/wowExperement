from agents.llm_provider import LLMProvider
import json
import logging


class LLMAssistant:
    def __init__(self):
        self.llm = LLMProvider()
        self.logger = logging.getLogger(__name__)

    def generate_movement_plan(self, enemies):
        """Запрашивает у LLM план передвижения"""
        try:
            prompt = f"""Сгенерируй маршрут для обхода {len(enemies)} врагов. 
            Координаты: {enemies}. Верни только JSON вида:
            {{"path": [[x1,y1], [x2,y2], ...}}"""

            response = self.llm.get_completion([{"role": "user", "text": prompt}])
            return json.loads(response)

        except Exception as e:
            self.logger.error(f"LLM error: {str(e)}")
            return {"path": enemies}  # Fallback - простой путь по порядку