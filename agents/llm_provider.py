# agents/llm_provider.py - Унифицированный LLM провайдер для Yandex GPT
import requests
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Абстрактный базовый класс для LLM провайдеров"""

    @abstractmethod
    def generate(self, system_message: str, user_message: str) -> str:
        """
        Генерирует ответ на основе системного и пользовательского сообщений
        :param system_message: Инструкции для AI
        :param user_message: Пользовательский запрос
        :return: Текст ответа от LLM
        """
        pass


class YandexGPTProvider(BaseLLMProvider):
    """Реализация провайдера для Yandex GPT API"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Инициализация провайдера
        :param config_path: Путь к файлу конфигурации (по умолчанию ищет в родительской директории)
        """
        self._load_config(config_path)
        self._validate_config()
        self.session = requests.Session()
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1"
        self.model_uri = f"gpt://{self.folder_id}/yandexgpt-lite"
        logger.info("YandexGPTProvider инициализирован")

    def _load_config(self, config_path: Optional[Path] = None) -> None:
        """Загружает конфигурацию из YAML файла"""
        try:
            if config_path is None:
                config_path = Path(__file__).parent.parent / "config.yaml"

            logger.debug(f"Загрузка конфигурации из {config_path}")

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            yandex_cfg = config.get("yandex_cloud", {})
            self.api_key = yandex_cfg.get("api_key", "")
            self.folder_id = yandex_cfg.get("folder_id", "")

            if not self.api_key or not self.folder_id:
                raise ValueError("Не найдены api_key или folder_id в config.yaml")

        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {str(e)}")
            raise

    def _validate_config(self) -> None:
        """Проверяет валидность конфигурации"""
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError("Не задан API ключ для Yandex GPT")
        logger.debug("Конфигурация успешно проверена")

    def generate(self, system_message: str, user_message: str) -> str:
        """
        Основной метод для генерации ответа
        :param system_message: Системное сообщение (роль AI)
        :param user_message: Пользовательский запрос
        :return: Текст ответа от LLM
        """
        messages = [
            {"role": "system", "text": system_message},
            {"role": "user", "text": user_message}
        ]

        try:
            response = self._get_completion(messages)
            return self._process_response(response)
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {str(e)}")
            raise

    def _get_completion(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Внутренний метод для взаимодействия с Yandex GPT API
        :param messages: Список сообщений в формате API
        :return: Ответ API в формате JSON
        """
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "modelUri": self.model_uri,
            "messages": messages,
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": "1000"
            }
        }

        logger.debug(f"Отправка запроса к Yandex GPT: {json.dumps(data, indent=2)}")

        try:
            response = self.session.post(
                f"{self.base_url}/completion",
                json=data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка запроса к Yandex GPT API: {str(e)}"
            if hasattr(e, 'response') and e.response:
                error_msg += f"\nДетали: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _process_response(self, response: Dict[str, Any]) -> str:
        """
        Обрабатывает ответ API и извлекает текст
        :param response: Ответ от API
        :return: Текст ответа
        """
        try:
            result = response.get('result', {})
            if not result:
                raise ValueError("Пустой ответ от API")

            message = result.get('alternatives', [{}])[0].get('message', {})
            text = message.get('text', '').strip()

            if not text:
                raise ValueError("Ответ не содержит текста")

            logger.debug(f"Получен ответ от LLM: {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"Ошибка обработки ответа: {str(e)}\nОтвет: {response}")
            raise ValueError(f"Не удалось обработать ответ API: {str(e)}")

    # Метод для обратной совместимости (можно удалить после рефакторинга)
    def get_completion(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Совместимость со старым кодом"""
        logger.warning("Используется устаревший метод get_completion()")
        return self._get_completion(messages)

    def get_llm(self):
        """Совместимость со старым кодом"""
        logger.warning("Используется устаревший метод get_llm()")
        return self