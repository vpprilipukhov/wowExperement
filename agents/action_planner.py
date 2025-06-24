from langchain_core.runnables import Runnable
from typing import Dict, Any, Optional, List
import logging
import json

logger = logging.getLogger(__name__)


class LLMAdapter(Runnable):
    """Адаптер для LLMProvider для совместимости с LangChain"""

    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    def invoke(self, input: Dict[str, Any], config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Выполняет запрос к языковой модели

        Args:
            input: Входные данные в формате:
                  {
                      "system_message": системный промпт,
                      "user_message": пользовательский запрос
                  }
            config: Опциональные параметры конфигурации

        Returns:
            Ответ от языковой модели
        """
        messages = [
            {"role": "system", "text": input["system_message"]},
            {"role": "user", "text": input["user_message"]}
        ]
        return self.llm_provider.generate_completion(messages)


class ActionPlanner:
    """Планировщик действий для WoW бота"""

    def __init__(self):
        try:
            from agents.llm_provider import LLMProvider
            self.llm_provider = LLMProvider()
            self.llm_adapter = LLMAdapter(self.llm_provider)
            logger.info("ActionPlanner успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации ActionPlanner: {str(e)}")
            raise

    def plan_action(
            self,
            game_state: Dict[str, Any],
            history: Optional[List[str]] = None,
            inventory: Optional[List[str]] = None,
            abilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Генерирует действие на основе состояния игры

        Args:
            game_state: Текущее состояние персонажа
            history: История последних действий
            inventory: Список предметов в инвентаре
            abilities: Доступные навыки

        Returns:
            Словарь с результатом:
            {
                "action": предложенное действие,
                "reason": обоснование,
                "status": "success"|"failed"
            }
        """
        try:
            # Формируем системный промпт
            system_message = """Ты AI-ассистент в World of Warcraft. Анализируй:
- Состояние: {game_state}
- Историю: {history}
- Инвентарь: {inventory}
- Навыки: {abilities}

Формат ответа:
Действие: [конкретная команда]
Причина: [логическое обоснование]"""

            # Подготавливаем данные
            history_str = "\n".join(history) if history else "Нет данных"
            inventory_str = "\n".join(inventory) if inventory else "Инвентарь пуст"
            abilities_str = "\n".join(abilities) if abilities else "Нет данных о навыках"

            # Формируем запрос
            request_data = {
                "system_message": system_message.format(
                    game_state=json.dumps(game_state, indent=2),
                    history=history_str,
                    inventory=inventory_str,
                    abilities=abilities_str
                ),
                "user_message": "Проанализируй ситуацию и предложи оптимальное действие"
            }

            # Выполняем запрос
            response = self.llm_adapter.invoke(request_data)
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Ошибка при планировании действия: {str(e)}")
            return {
                "action": None,
                "reason": str(e),
                "status": "failed"
            }

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, str]:
        """
        Анализирует ответ от языковой модели

        Args:
            response: Ответ от LLM

        Returns:
            Словарь с распарсенными данными

        Raises:
            ValueError: Если ответ не соответствует формату
        """
        try:
            content = response["result"]["alternatives"][0]["message"]["text"]

            # Парсим действие и причину
            action = None
            reason = None
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('Действие:'):
                    action = line[9:].strip()
                elif line.startswith('Причина:'):
                    reason = line[8:].strip()

            if not action or not reason:
                raise ValueError("Ответ не содержит действие и/или причину")

            return {
                "action": action,
                "reason": reason,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Ошибка парсинга ответа: {str(e)}\nОтвет: {response}")
            raise ValueError(f"Неверный формат ответа: {str(e)}")