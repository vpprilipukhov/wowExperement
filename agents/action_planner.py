# action_planner.py - Планировщик действий с использованием LLM
import logging
from typing import Dict, Any
import json


class ActionPlanner:
    def __init__(self, llm_provider):
        """
        Инициализация планировщика действий
        :param llm_provider: Провайдер LLM (должен иметь метод 'generate')
        """
        self.logger = logging.getLogger(__name__)
        self.llm_provider = llm_provider
        self.logger.info("ActionPlanner инициализирован")

    def plan_action(self, context: Dict[str, Any]) -> Dict:
        """
        Планирует следующее действие на основе контекста
        :param context: Контекст игры
        :return: Запланированное действие
        """
        self.logger.debug("Начало планирования действия")

        try:
            # 1. Формирование промпта
            prompt = self._build_prompt(context)
            self.logger.debug(f"Сформирован промпт: {prompt}")

            # 2. Запрос к LLM
            response = self._call_llm(prompt)
            self.logger.debug(f"Ответ LLM: {response}")

            # 3. Парсинг и валидация ответа
            action = self._parse_response(response)
            self.logger.info(f"Успешно запланировано действие: {action}")

            return {
                "status": "success",
                "action": action,
                "reason": "Действие успешно запланировано"
            }

        except Exception as e:
            self.logger.error(f"Ошибка планирования: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "reason": str(e)
            }

    def _build_prompt(self, context: Dict[str, Any]) -> Dict:
        """
        Формирует промпт для LLM на основе контекста
        :param context: Контекст игры
        :return: Промпт в формате для LLM
        """
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

        user_message = (
            f"Текущее состояние:\n"
            f"- Позиция: {context.get('game_state', {}).get('position', 'неизвестно')}\n"
            f"- Здоровье: {context.get('game_state', {}).get('health', 'нет данных')}\n"
            f"- Враги: {len(context.get('game_state', {}).get('enemies', []))}\n"
            f"- NPC: {len(context.get('game_state', {}).get('npcs', []))}\n"
            f"- Инвентарь: {len(context.get('inventory', []))} предметов\n"
            f"- Навыки: {len(context.get('abilities', [])) if context.get('abilities') else 'нет данных'}\n\n"
            f"Последнее действие: {context.get('history', [{}])[-1].get('action', 'нет')}"
        )

        return {
            "system_message": system_message,
            "user_message": user_message
        }

    def _call_llm(self, prompt: Dict) -> str:
        """
        Вызывает LLM с заданным промптом
        :param prompt: Промпт для LLM
        :return: Ответ LLM
        """
        self.logger.debug("Вызов LLM...")

        try:
            # Используем метод 'generate' вместо 'generate_completion'
            response = self.llm_provider.generate(
                system_message=prompt["system_message"],
                user_message=prompt["user_message"]
            )
            return response
        except AttributeError:
            self.logger.error("Некорректный провайдер LLM: отсутствует метод 'generate'")
            raise ValueError("Провайдер LLM должен иметь метод 'generate'")

    def _parse_response(self, response: str) -> Dict:
        """
        Парсит ответ LLM и валидирует его
        :param response: Ответ от LLM
        :return: Распарсенное действие
        """
        self.logger.debug("Парсинг ответа LLM...")

        try:
            # Удаляем возможные markdown-код блоки
            cleaned_response = response.replace("```json", "").replace("```", "").strip()
            action = json.loads(cleaned_response)

            # Базовая валидация
            required_fields = ["action", "target", "reason"]
            for field in required_fields:
                if field not in action:
                    raise ValueError(f"Отсутствует обязательное поле: {field}")

            return action
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка парсинга JSON: {e}")
            raise ValueError("Некорректный формат ответа от LLM")
        except Exception as e:
            self.logger.error(f"Ошибка валидации ответа: {e}")
            raise