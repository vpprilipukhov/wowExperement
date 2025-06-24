from langchain_core.runnables import Runnable
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionPlanner:
    """Улучшенный планировщик действий с расширенной логикой"""

    def __init__(self):
        try:
            from agents.llm_provider import LLMProvider
            self.llm_provider = LLMProvider()
            self.llm_adapter = LLMAdapter(self.llm_provider)
            self.last_action = None
            self.action_history = []
            logger.info("ActionPlanner инициализирован с улучшенной логикой")
        except Exception as e:
            logger.error(f"Ошибка инициализации: {str(e)}", exc_info=True)
            raise

    def plan_action(
            self,
            game_state: Dict[str, Any],
            history: Optional[List[str]] = None,
            inventory: Optional[List[str]] = None,
            abilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Улучшенный метод планирования с логированием и валидацией"""
        try:
            # 1. Подготовка контекста
            context = self._prepare_context(game_state, history, inventory, abilities)

            # 2. Генерация промпта
            prompt = self._generate_prompt(context)
            logger.debug(f"Сформирован промпт: {prompt}")

            # 3. Запрос к LLM
            start_time = datetime.now()
            response = self.llm_adapter.invoke(prompt)
            latency = (datetime.now() - start_time).total_seconds()
            logger.info(f"LLM ответил за {latency:.2f} сек")

            # 4. Парсинг и валидация
            result = self._parse_response(response)
            self._validate_action(result, context)

            # 5. Логирование действия
            self._log_action(result, context)
            return result

        except Exception as e:
            error_msg = f"Ошибка планирования: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "action": None,
                "reason": error_msg
            }

    def _prepare_context(self, game_state, history, inventory, abilities):
        """Структурирует контекст для LLM"""
        return {
            "timestamp": datetime.now().isoformat(),
            "game_state": game_state,
            "history": history or [],
            "inventory": inventory or [],
            "abilities": abilities or [],
            "last_action": self.last_action
        }

    def _generate_prompt(self, context):
        """Генерирует структурированный промпт"""
        return {
            "system_message": self._get_system_prompt(),
            "user_message": self._get_user_message(context)
        }

    def _get_system_prompt(self):
        """Возвращает системный промпт"""
        return """Ты профессиональный AI-ассистент для World of Warcraft. Ты должен:
1. Анализировать состояние игры
2. Предлагать оптимальные действия
3. Четко следовать формату ответа

Формат ответа:
```json
{
    "action": "тип_действия",
    "target": {"type": "тип_цели", "position": [x,y]},
    "reason": "логическое обоснование"
}```"""

    def _get_user_message(self, context):
        """Формирует пользовательское сообщение"""
        game_state = context["game_state"]
        return f"""Текущее состояние:
- Позиция: {game_state.get('position', 'неизвестно')}
- Здоровье: {game_state.get('health', 100)}%
- Враги: {len(game_state.get('enemies', []))}
- NPC: {len(game_state.get('npcs', []))}
- Инвентарь: {len(context['inventory'])} предметов
- Навыки: {', '.join(context['abilities']) or 'нет данных'}

Последнее действие: {context['last_action'] or 'нет'}"""

    def _parse_response(self, response):
        """Парсит ответ с улучшенной обработкой ошибок"""
        try:
            content = response["result"]["alternatives"][0]["message"]["text"]
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка парсинга: {str(e)}\nОтвет: {content}")
            raise ValueError("Неверный формат ответа")

    def _validate_action(self, action, context):
        """Проверяет валидность действия"""
        required_keys = {"action", "target", "reason"}
        if not all(key in action for key in required_keys):
            raise ValueError(f"Ответ не содержит все обязательные поля: {required_keys}")

        # Дополнительные проверки
        if action["action"] not in ["attack", "move", "interact", "loot"]:
            raise ValueError(f"Недопустимое действие: {action['action']}")

    def _log_action(self, action, context):
        """Логирует успешное действие"""
        self.last_action = action
        self.action_history.append({
            "timestamp": context["timestamp"],
            "action": action,
            "context": context
        })
        logger.info(f"Запланировано действие: {action['action']} -> {action['target']}")


class LLMAdapter(Runnable):
    """Обновленный адаптер с кэшированием"""

    def __init__(self, llm_provider):
        self.llm_provider = llm_provider
        self.cache = {}

    def invoke(self, input: Dict[str, Any], config: Optional[Dict] = None) -> Dict[str, Any]:
        cache_key = json.dumps(input, sort_keys=True)
        if cache_key in self.cache:
            logger.debug("Использован кэшированный ответ")
            return self.cache[cache_key]

        response = self.llm_provider.generate_completion([
            {"role": "system", "text": input["system_message"]},
            {"role": "user", "text": input["user_message"]}
        ])
        self.cache[cache_key] = response
        return response