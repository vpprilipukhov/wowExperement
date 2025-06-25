# agents/action_planner.py - Планировщик действий с исправленной обработкой истории
import logging
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)


class ActionPlanner:
    def __init__(self, llm_provider):
        """Инициализация планировщика действий"""
        self.llm_provider = llm_provider
        logger.info("ActionPlanner инициализирован")

    def plan_action(self, context: Dict[str, Any]) -> Dict:
        """Планирует следующее действие на основе контекста"""
        logger.debug("Начало планирования действия")

        try:
            prompt = self._build_prompt(context)
            logger.debug(f"Сформирован промпт: {prompt}")

            response = self.llm_provider.generate(
                system_message=prompt["system_message"],
                user_message=prompt["user_message"]
            )

            action = self._parse_response(response)
            logger.info(f"Успешно запланировано действие: {action}")

            return {
                "status": "success",
                "action": action,
                "reason": "Действие успешно запланировано"
            }

        except Exception as e:
            logger.error(f"Ошибка планирования: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e)
            }

    def _build_prompt(self, context: Dict[str, Any]) -> Dict:
        """Формирует промпт для LLM с безопасной обработкой истории"""
        system_message = (
            "Ты профессиональный AI-ассистент для World of Warcraft. Ты должен:\n"
            "1. Анализировать состояние игры\n"
            "2. Предлагать оптимальные действия\n"
            "3. Четко следовать формату ответа\n\n"
            "Формат ответа:\n"
            "```json\n"
            "{\n"
            '    "action": "тип_действия",\n'
            '    "target": {"type": "тип_цели", "position": [x,y]},\n'
            '    "reason": "логическое обоснование"\n'
            "}\n"
            "```"
        )

        # Безопасное получение последнего действия
        history = context.get('history', [])
        last_action = "нет" if not history else history[-1].get('action', 'нет')

        user_message = (
            f"Текущее состояние:\n"
            f"- Позиция: {context.get('game_state', {}).get('position', 'неизвестно')}\n"
            f"- Здоровье: {context.get('game_state', {}).get('health', 'нет данных')}\n"
            f"- Враги: {len(context.get('game_state', {}).get('enemies', []))}\n"
            f"- NPC: {len(context.get('game_state', {}).get('npcs', []))}\n"
            f"- Инвентарь: {len(context.get('inventory', []))} предметов\n"
            f"- Навыки: {len(context.get('abilities', [])) if context.get('abilities') else 'нет данных'}\n\n"
            f"Последнее действие: {last_action}"
        )

        return {
            "system_message": system_message,
            "user_message": user_message
        }

    def _parse_response(self, response: str) -> Dict:
        """Парсит и валидирует ответ от LLM"""
        try:
            # Удаление возможных markdown-блоков
            cleaned_response = response.replace("```json", "").replace("```", "").strip()
            action = json.loads(cleaned_response)

            # Валидация обязательных полей
            required_fields = ["action", "target", "reason"]
            for field in required_fields:
                if field not in action:
                    raise ValueError(f"Отсутствует обязательное поле: {field}")

            return action

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            raise ValueError("Некорректный формат ответа от LLM")
        except Exception as e:
            logger.error(f"Ошибка валидации ответа: {e}")
            raise

    # Метод для обратной совместимости
    def get_llm(self):
        """Возвращает текущий экземпляр LLM провайдера"""
        return self.llm_provider