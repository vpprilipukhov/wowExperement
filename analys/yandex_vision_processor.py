"""
Обработчик скриншотов WoW через Yandex Vision API
Версия 4.1 - Исправление путей и добавление гибкости
"""

import os
import sys
import base64
import logging
import requests
import json
from pathlib import Path
from typing import Dict, Any

from utils.yandexIAMTokenManager import YandexIAMTokenManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wow_vision_processor.log"),
        logging.StreamHandler()
    ]
)



class YandexVisionProcessor:
    """Основной обработчик для анализа скриншотов WoW"""

    def __init__(self, token_manager: YandexIAMTokenManager):
        self.logger = logging.getLogger("YandexVisionProcessor")
        self.token_manager = token_manager
        self.logger.info("Инициализация обработчика скриншотов WoW")

    def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Анализирует изображение через Yandex Vision API
        Возвращает полный ответ API
        """
        try:
            # Подготовка запроса
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            payload = {
                "folderId": self.token_manager.folder_id,
                "analyze_specs": [{
                    "content": base64_image,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "text_detection_config": {
                            "language_codes": ["*"],
                            "model": "page"
                        }
                    }]
                }]
            }

            # Отправка запроса
            iam_token = self.token_manager.get_iam_token()
            if not iam_token:
                return {}

            response = requests.post(
                "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze",
                headers={"Authorization": f"Bearer {iam_token}"},
                json=payload,
                timeout=15
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            self.logger.error(f"Ошибка обработки изображения: {str(e)}")
            return {}

def main():
    """Основная функция для тестирования"""
    logging.info("=== Запуск обработчика скриншотов WoW ===")

    try:
        # Инициализация токен-менеджера
        token_manager = YandexIAMTokenManager()

        # Проверка подключения
        if not token_manager.test_connection():
            logging.error("Не удалось установить соединение с Yandex Cloud API")
            sys.exit(1)

        # Инициализация процессора
        processor = YandexVisionProcessor(token_manager)

        # Путь к тестовому изображению
        current_dir = Path(__file__).parent.parent
        image_path = current_dir / "screenshots" / "wow_20250627_031801.png"

        if not image_path.exists():
            logging.error(f"Тестовое изображение не найдено: {image_path}")
            # Список доступных изображений
            screenshots_dir = current_dir / "screenshots"
            if screenshots_dir.exists():
                available_images = os.listdir(screenshots_dir)
                logging.info(f"Доступные изображения в screenshots: {available_images}")
            sys.exit(1)

        # Загрузка изображения
        with open(image_path, "rb") as f:
            image_data = f.read()

        logging.info(f"Изображение загружено: {image_path} ({len(image_data)} байт)")

        # Обработка изображения
        api_response = processor.process_image(image_data)

        # Сохранение сырого ответа для анализа
        output_path = current_dir / "vision_response.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(api_response, f, indent=2, ensure_ascii=False)

        logging.info(f"Ответ API сохранен в {output_path}")

    except Exception as e:
        logging.exception("Критическая ошибка при выполнении")
        sys.exit(1)

if __name__ == "__main__":
    main()