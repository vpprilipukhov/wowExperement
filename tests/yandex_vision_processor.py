"""
YandexVisionProcessor_FinalWorking.py - полностью рабочая версия
"""

import os
import yaml
import json
import base64
import logging
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vision_processor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigLoader:
    """Загрузчик конфигурации с улучшенной обработкой ошибок"""

    @staticmethod
    def load_config():
        """Загружает и валидирует конфиг"""
        try:
            config_path = Path(__file__).parent.parent / "config.yaml"
            logger.info(f"Попытка загрузить конфиг из: {config_path}")

            if not config_path.exists():
                logger.error("Файл config.yaml не найден")
                return None

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Проверка структуры конфига
            if not config or 'yandex' not in config or 'vision' not in config['yandex']:
                logger.error("Неверная структура конфига. Ожидается раздел yandex.vision")
                return None

            vision_config = config['yandex']['vision']

            # Проверка обязательных полей
            if not all(key in vision_config for key in ['oauth_token', 'folder_id']):
                logger.error("В разделе yandex.vision отсутствуют oauth_token или folder_id")
                return None

            # Проверка значений
            if not vision_config['oauth_token'] or not isinstance(vision_config['oauth_token'], str):
                logger.error("oauth_token должен быть непустой строкой")
                return None

            if not vision_config['folder_id'] or not isinstance(vision_config['folder_id'], str):
                logger.error("folder_id должен быть непустой строкой")
                return None

            # Получаем путь к скриншотам
            screenshots_dir = config.get('screenshots', {}).get('dir', 'screenshots')
            if not screenshots_dir or not isinstance(screenshots_dir, str):
                screenshots_dir = 'screenshots'

            return {
                'oauth_token': vision_config['oauth_token'],
                'folder_id': vision_config['folder_id'],
                'screenshots_dir': screenshots_dir
            }

        except yaml.YAMLError as e:
            logger.error(f"Ошибка парсинга YAML: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка загрузки конфига: {str(e)}")
            return None

class YandexVisionProcessor:
    def __init__(self, config):
        """Инициализация с проверкой всех параметров"""
        self.oauth_token = config['oauth_token']
        self.folder_id = config['folder_id']
        self.api_url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"

        # Обработка пути к скриншотам
        screenshots_dir = config.get('screenshots_dir', 'screenshots')
        self.screenshots_dir = (Path(__file__).parent.parent / screenshots_dir).resolve()
        self.screenshots_dir.mkdir(exist_ok=True)

        logger.info(f"Папка скриншотов: {self.screenshots_dir}")
        logger.debug(f"Используется folder_id: {self.folder_id}")

    def process(self):
        """Основной рабочий цикл"""
        try:
            # 1. Получаем скриншот
            screenshot = self._get_latest_screenshot()
            if not screenshot:
                logger.warning("Не найдено ни одного скриншота")
                return None

            logger.info(f"Обработка скриншота: {screenshot.name}")

            # 2. Подготавливаем изображение
            image_data = self._prepare_image(screenshot)
            if not image_data:
                logger.error("Не удалось подготовить изображение")
                return None

            # 3. Отправляем в API
            api_response = self._call_vision_api(image_data)
            if not api_response:
                logger.error("Ошибка при вызове Vision API")
                return None

            # 4. Парсим результат
            result = self._parse_response(api_response)

            if not result:
                logger.warning("Не удалось распознать HP/Mana")

            return result

        except Exception as e:
            logger.error(f"Критическая ошибка обработки: {str(e)}", exc_info=True)
            return None

    def _get_latest_screenshot(self):
        """Находит последний скриншот"""
        try:
            screenshots = list(self.screenshots_dir.glob("wow_*.png"))
            if not screenshots:
                logger.warning("Нет доступных скриншотов")
                return None

            return max(screenshots, key=lambda x: x.stat().st_mtime)
        except Exception as e:
            logger.error(f"Ошибка поиска скриншота: {str(e)}")
            return None

    def _prepare_image(self, image_path):
        """Подготавливает изображение для API"""
        try:
            with Image.open(image_path) as img:
                # Оптимизация размера
                if img.size[0] > 1920 or img.size[1] > 1080:
                    img.thumbnail((1920, 1080))

                # Конвертация в base64
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue()).decode('ascii')
        except Exception as e:
            logger.error(f"Ошибка подготовки изображения: {str(e)}")
            return None

    def _call_vision_api(self, image_base64):
        """Вызывает Vision API с расширенным логированием"""
        try:
            headers = {
                "Authorization": f"Bearer {self.oauth_token}",
                "Content-Type": "application/json"
            }

            body = {
                "folderId": self.folder_id,
                "analyzeSpecs": [{
                    "content": image_base64,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "textDetectionConfig": {
                            "languageCodes": ["en"],
                            "model": "page"
                        }
                    }]
                }]
            }

            logger.info("Отправка запроса к Vision API...")
            logger.debug(f"Размер тела запроса: {len(json.dumps(body))} байт")

            response = requests.post(
                self.api_url,
                headers=headers,
                json=body,
                timeout=15
            )

            logger.debug(f"Статус ответа: {response.status_code}")
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка API: {str(e)}"
            if e.response:
                error_msg += f", статус: {e.response.status_code}, ответ: {e.response.text[:200]}"
                if e.response.status_code == 401:
                    error_msg += "\nПроверьте правильность oauth_token и folder_id"
            logger.error(error_msg)
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка API: {str(e)}")
            return None

    def _parse_response(self, api_response):
        """Парсит ответ API с проверкой структуры"""
        try:
            blocks = api_response["results"][0]["results"][0]["textDetection"]["pages"][0]["blocks"]

            result = {"hp": None, "mana": None}
            for block in blocks:
                text = block["lines"][0]["text"].lower()
                if "hp" in text:
                    result["hp"] = self._parse_resource(text)
                elif "mana" in text:
                    result["mana"] = self._parse_resource(text)

            return result
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа API: {str(e)}")
            return None

    def _parse_resource(self, text):
        """Парсит значения HP/Mana"""
        try:
            import re
            match = re.search(r'(\d+)\s*/\s*(\d+)', text)
            if not match:
                return None

            return {
                "current": int(match.group(1)),
                "max": int(match.group(2))
            }
        except Exception as e:
            logger.warning(f"Ошибка парсинга значений: {str(e)}")
            return None

def main():
    """Точка входа с подробными инструкциями"""
    print("=== Анализатор скриншотов WOW ===")
    print("Версия 3.0 (финальная рабочая)")

    try:
        # 1. Загрузка конфигурации
        print("\n[1/4] Загрузка конфигурации...")
        config = ConfigLoader.load_config()
        if not config:
            print("\nОШИБКА: Не удалось загрузить конфигурацию")
            print("Проверьте файл config.yaml в корне проекта:")
            print("- Наличие раздела yandex.vision")
            print("- Наличие oauth_token и folder_id")
            print(f"\nОжидаемый путь: {Path(__file__).parent.parent / 'config.yaml'}")
            return

        # 2. Инициализация процессора
        print("[2/4] Инициализация процессора...")
        processor = YandexVisionProcessor(config)

        # 3. Обработка скриншота
        print("[3/4] Обработка скриншота...")
        result = processor.process()

        # 4. Вывод результатов
        print("\n[4/4] Результаты анализа:")
        if result:
            if result["hp"]:
                print(f"HP: {result['hp']['current']}/{result['hp']['max']}")
            else:
                print("HP: не распознано")

            if result["mana"]:
                print(f"Mana: {result['mana']['current']}/{result['mana']['max']}")
            else:
                print("Mana: не распознано")
        else:
            print("Не удалось получить результаты. Проверьте логи.")

        print("\nОбработка завершена. Подробности в vision_processor.log")

    except Exception as e:
        print(f"\nКРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        print("Пожалуйста, проверьте логи для деталей.")
        logger.critical("Критическая ошибка в main()", exc_info=True)

if __name__ == "__main__":
    # Проверка зависимостей
    try:
        import yaml
        import requests
    except ImportError as e:
        print(f"ОШИБКА: Не установлена зависимость - {str(e)}")
        print("Установите необходимые пакеты:")
        print("pip install pyyaml requests")
        exit(1)

    main()