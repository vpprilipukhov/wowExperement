from typing import Any, Optional, Dict
import json


class CodeGenerator:
    """
    Генератор Python-кода для управления персонажем в WoW.

    Args:
        llm_client: Клиент для работы с языковой моделью
        max_retries: Максимальное количество попыток генерации (по умолчанию 3)
    """

    def __init__(self, llm_client: Any, max_retries: int = 3):
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.error_feedback = []

    def generate_action_code(self, task_description: str, game_context: Dict[str, Any]) -> Optional[str]:
        """
        Генерирует Python-код для выполнения задачи в игре.

        Args:
            task_description: Описание задачи (например, "атаковать врага")
            game_context: Контекст игры (здоровье, локация и т.д.)

        Returns:
            Строка с Python-кодом или None, если генерация не удалась
        """
        for attempt in range(self.max_retries):
            try:
                prompt = self._build_prompt(task_description, game_context)
                response = self.llm_client.generate(prompt)
                code = self._extract_code(response)

                if self._validate_code(code):
                    return code

            except Exception as e:
                self.error_feedback.append(f"Попытка {attempt + 1}: {str(e)}")
                continue

        return None

    def _build_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Строит промпт для LLM на основе задачи и контекста"""
        error_feedback = "\n".join(self.error_feedback[-3:]) if self.error_feedback else "Нет ошибок"

        return f"""
        Ты - AI ассистент, который генерирует Python код для управления персонажем в WoW.
        Задача: {task}

        Контекст игры:
        {json.dumps(context, indent=2)}

        Предыдущие ошибки (для учёта):
        {error_feedback}

        Сгенерируй код, который:
        1. Использует библиотеки pyautogui, cv2, numpy
        2. Корректно обрабатывает возможные ошибки
        3. Читаем и содержит комментарии
        4. Выполняет поставленную задачу

        Верни только код между ```python и ```.
        """

    def _extract_code(self, response: str) -> str:
        """Извлекает код из ответа LLM"""
        if "```python" in response:
            return response.split("```python")[1].split("```")[0].strip()
        return response.strip()

    def _validate_code(self, code: str) -> bool:
        """Проверяет код на безопасность и наличие необходимых импортов"""
        required_imports = {"pyautogui", "cv2", "numpy"}
        dangerous_methods = {"os.system", "subprocess", "eval", "exec"}

        for method in dangerous_methods:
            if method in code:
                raise ValueError(f"Код содержит опасный метод: {method}")

        missing_imports = [imp for imp in required_imports if imp not in code]
        if missing_imports:
            raise ValueError(f"Отсутствуют необходимые импорты: {missing_imports}")

        return True