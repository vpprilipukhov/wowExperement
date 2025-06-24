import requests
import yaml
from pathlib import Path
from typing import Dict, Any, List
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_response(prompt: str) -> Dict[str, Any]:
    try:
        # Здесь будет реальная реализация API вызова
        logger.info(f"Генерация ответа для промпта: {prompt[:50]}...")
        return {
            'text': 'Пример ответа от LLM',
            'status': 'success'
        }
    except Exception as e:
        logger.error(f"Ошибка LLM: {str(e)}")
        return {'status': 'error'}


class LLMProvider:
    """Класс для работы с Yandex GPT API"""

    def __init__(self):
        """Инициализация провайдера LLM"""
        self._load_config()
        self.session = requests.Session()
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1"
        self.model_uri = f"gpt://{self.folder_id}/yandexgpt-lite"
        logger.info("LLMProvider инициализирован")

    def _load_config(self):
        """Загружает конфигурацию из config.yaml"""
        try:
            config_path = Path(__file__).parent.parent / "config.yaml"
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

    def _validate_config(self):
        if not self.api_key or self.api_key == "your_api_key_here":
            raise ValueError("Не задан API ключ для Yandex GPT")

    def get_completion(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Основной метод для получения ответа от Yandex GPT API

        Args:
            messages: Список сообщений в формате:
                    [{"role": "user|assistant", "text": "сообщение"}]

        Returns:
            Ответ API в формате JSON
        """
        try:
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
            response = self.session.post(
                f"{self.base_url}/completion",
                json=data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка запроса: {str(e)}"
            if hasattr(e, 'response') and e.response:
                error_msg += f"\nДетали: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    # Метод для совместимости
    def get_llm(self):
        """Возвращает текущий экземпляр для совместимости"""
        return self