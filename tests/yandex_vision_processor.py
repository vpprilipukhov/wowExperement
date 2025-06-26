import base64
import json
import logging
import os
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
import io
import hashlib
import argparse

import requests


class YandexVisionProcessor:
    """
    Обработчик изображений через Yandex Vision API
    Документация: https://cloud.yandex.ru/docs/vision/quickstart
    """

    def __init__(self, folder_id: str, api_key: str,
                 default_languages: List[str] = ["en", "ru"],
                 timeout: int = 10,
                 max_retries: int = 3,
                 max_image_size: int = 4 * 1024 * 1024,  # 4 МБ
                 max_image_dimension: int = 1280):
        """
        Инициализация процессора

        :param folder_id: ID каталога Yandex Cloud
        :param api_key: API-ключ сервисного аккаунта (40 символов)
        :param default_languages: языки для распознавания текста
        :param timeout: таймаут запроса в секундах
        :param max_retries: максимальное количество попыток повтора
        :param max_image_size: максимальный размер изображения в байтах
        :param max_image_dimension: максимальный размер большей стороны изображения в пикселях
        """
        # Инициализация логгера
        self.logger = logging.getLogger("YandexVisionProcessor")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Сохраняем параметры
        self.folder_id = folder_id
        self.api_key = api_key
        self.default_languages = default_languages
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_image_size = max_image_size
        self.max_image_dimension = max_image_dimension

        # Логируем параметры
        self.logger.info("Инициализация Yandex Vision Processor")
        self.logger.debug(f"Folder ID: {folder_id}")
        if api_key:
            self.logger.debug(f"API Key: {api_key[:5]}...{api_key[-5:]}")
        else:
            self.logger.error("API Key is empty!")

    def compress_image(self, image_bytes: bytes) -> bytes:
        """
        Сжимает изображение, если оно слишком большое.
        Сохраняет формат (PNG, JPEG).

        :param image_bytes: исходное изображение
        :return: сжатое изображение
        """
        try:
            # Определяем формат
            img = Image.open(io.BytesIO(image_bytes))
            format = img.format

            # Если изображение слишком большое по размеру файла или по разрешению
            if (len(image_bytes) > self.max_image_size or
                    max(img.size) > self.max_image_dimension):

                # Вычисляем новый размер
                ratio = min(
                    self.max_image_dimension / max(img.size),
                    0.9 * self.max_image_size / len(image_bytes)
                )
                new_size = (int(img.width * ratio), int(img.height * ratio))

                # Изменяем размер
                img = img.resize(new_size, Image.LANCZOS)

                # Сохраняем в буфер
                buffer = io.BytesIO()
                img.save(buffer, format=format or "PNG", optimize=True)
                compressed_bytes = buffer.getvalue()

                self.logger.info(f"Сжато изображение: {len(image_bytes)} -> {len(compressed_bytes)} байт")
                return compressed_bytes
            else:
                return image_bytes
        except Exception as e:
            self.logger.error(f"Ошибка сжатия изображения: {str(e)}")
            return image_bytes

    def process_image(self, image_bytes: bytes, features: List[str] = ["TEXT_DETECTION", "OBJECT_DETECTION"]) -> \
    Optional[dict]:
        """
        Основной метод обработки изображения

        :param image_bytes: изображение в виде байтов
        :param features: список запрашиваемых функций
        :return: структурированные результаты или None при ошибке
        """
        # Проверка входных данных
        if not image_bytes:
            self.logger.error("Получены пустые байты изображения")
            return None

        # Сжимаем изображение при необходимости
        if len(image_bytes) > self.max_image_size:
            image_bytes = self.compress_image(image_bytes)

        size = len(image_bytes)
        if size > self.max_image_size:
            self.logger.warning(f"Изображение слишком большое после сжатия ({size} байт)")
            # Все равно попробуем обработать

        self.logger.info(f"Обработка изображения размером {size} байт")

        try:
            # Шаг 1: Подготовка изображения
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            self.logger.debug("Изображение закодировано в base64")

            # Шаг 2: Формирование запроса
            analyze_specs = [{
                "content": encoded_image,
                "features": []
            }]

            # Добавляем запрошенные функции анализа
            for feature in features:
                feature_config = {"type": feature}

                # Для текста добавляем языки
                if feature == "TEXT_DETECTION":
                    feature_config["text_detection_config"] = {
                        "language_codes": self.default_languages
                    }

                analyze_specs[0]["features"].append(feature_config)

            request_body = {
                "folderId": self.folder_id,
                "analyzeSpecs": analyze_specs
            }

            self.logger.debug(f"Отправка запроса с функциями: {features}")

            # Шаг 3: Отправка запроса
            response = self._send_request(request_body)

            if not response:
                self.logger.error("Пустой ответ от API")
                return None

            self.logger.info("Успешный ответ от API Vision")

            # Шаг 4: Обработка ответа
            return self._parse_response(response)

        except Exception as e:
            self.logger.exception(f"Критическая ошибка обработки: {str(e)}")
            return None

    def _send_request(self, body: dict) -> Optional[dict]:
        """
        Отправляет запрос к Vision API с обработкой ошибок и повторами

        :param body: тело запроса в формате JSON
        :return: ответ API или None при ошибке
        """
        url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        # Логируем тело запроса (без base64)
        log_body = body.copy()
        if 'analyzeSpecs' in log_body and len(log_body['analyzeSpecs']) > 0:
            log_body['analyzeSpecs'][0]['content'] = f"[image_data:{len(log_body['analyzeSpecs'][0]['content'])}]"
        self.logger.debug(f"Отправка запроса: {json.dumps(log_body, indent=2)}")

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Попытка {attempt + 1}/{self.max_retries}")
                start_time = time.time()

                response = requests.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=self.timeout
                )

                latency = time.time() - start_time
                self.logger.debug(f"Ответ за {latency:.2f} сек. Код: {response.status_code}")

                # Логируем ошибки 4xx/5xx
                if response.status_code >= 400:
                    self.logger.error(f"Ошибка {response.status_code}: {response.reason}")
                    # Логируем тело ответа (первые 1000 символов)
                    self.logger.debug(f"Ответ сервера: {response.text[:1000]}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Ошибка запроса: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Повтор через {wait_time} сек...")
                    time.sleep(wait_time)
                else:
                    self.logger.critical("Превышено количество попыток")
                    return None

    def _parse_response(self, response: dict) -> dict:
        """
        Разбирает ответ Vision API в структурированный формат

        :param response: сырой ответ API
        :return: структурированные результаты
        """
        result = {
            "text": "",
            "objects": [],
            "raw": response
        }

        try:
            # Извлекаем результаты первого анализа
            if "results" not in response or not response["results"]:
                self.logger.error("Некорректный ответ: отсутствует results")
                return result

            first_result = response["results"][0]
            analysis_results = first_result.get("results", [])

            # Обрабатываем каждый тип результата
            for feature in analysis_results:
                # Распознавание текста
                if "textDetection" in feature:
                    text_data = feature["textDetection"]
                    pages = text_data.get("pages", [])

                    for page in pages:
                        for block in page.get("blocks", []):
                            for line in block.get("lines", []):
                                words = [word["text"] for word in line.get("words", [])]
                                result["text"] += " ".join(words) + "\n"

                    word_count = len(result["text"].split())
                    self.logger.info(f"Распознано {word_count} слов")

                # Обнаружение объектов
                elif "objectDetection" in feature:
                    objects = feature["objectDetection"].get("objects", [])

                    for obj in objects:
                        if "name" in obj and "confidence" in obj:
                            result["objects"].append({
                                "name": obj["name"],
                                "confidence": obj["confidence"],
                                "bbox": obj.get("boundingBox", {})
                            })

                    self.logger.info(f"Обнаружено {len(result['objects'])} объектов")

            return result

        except (KeyError, TypeError) as e:
            self.logger.error(f"Ошибка разбора ответа: {str(e)}")
            result["error"] = f"Response parsing error: {str(e)}"
            return result


def load_config(config_path: Path = None) -> dict:
    """Загружает конфигурацию из config.yaml"""
    if not config_path:
        project_root = Path(__file__).resolve().parent.parent
        config_path = project_root / "config.yaml"

    if not config_path.exists():
        print(f"❌ Файл config.yaml не найден: {config_path}")
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения config.yaml: {str(e)}")
        return {}


def test_connection(api_key: str, folder_id: str):
    """
    Тестирует подключение к Yandex Vision API

    :param api_key: API ключ сервисного аккаунта
    :param folder_id: ID каталога в Yandex Cloud
    :return: True если подключение успешно, False в противном случае
    """
    url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }

    # Минимальный валидный запрос
    data = {
        "folderId": folder_id,
        "analyzeSpecs": [{
            "content": base64.b64encode(b"test").decode('utf-8'),
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        print("✅ Успешное подключение к Vision API!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print("Детали ошибки:", e.response.text[:500])
        return False


def test_image_processing(processor: YandexVisionProcessor, image_path: Path):
    """
    Тестирует обработку конкретного изображения

    :param processor: инициализированный процессор
    :param image_path: путь к изображению
    """
    if not image_path.exists():
        print(f"❌ Файл не найден: {image_path}")
        return

    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()

        print(f"✅ Загружен файл: {image_path} ({len(image_data)} байт)")

        # Обработка изображения
        result = processor.process_image(image_data)

        if not result:
            print("❌ Ошибка обработки изображения")
            return

        # Вывод результатов
        print("\n--- Распознанный текст ---")
        print(result["text"][:500] + ("..." if len(result["text"]) > 500 else ""))

        if result["objects"]:
            print("\n--- Обнаруженные объекты ---")
            for obj in result["objects"][:10]:
                print(f"- {obj['name']} (точность: {obj['confidence']:.2f})")
        else:
            print("\n⚠️ Объекты не обнаружены")

        print("\n✅ Обработка завершена успешно")

    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Главная функция для тестирования"""
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)

    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='Yandex Vision Processor')
    parser.add_argument('--test-connection', action='store_true', help='Test API connection only')
    parser.add_argument('--test-image', type=str, help='Path to specific image for testing')
    parser.add_argument('--config', type=str, help='Path to config.yaml')
    args = parser.parse_args()

    # Загрузка конфигурации
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    if not config:
        return

    # Получение параметров
    yandex_config = config.get('yandex_cloud', {})
    api_key = yandex_config.get('api_key') or os.getenv('YANDEX_API_KEY')
    folder_id = yandex_config.get('folder_id') or os.getenv('YANDEX_FOLDER_ID')

    # Проверка параметров
    if not api_key or not folder_id:
        print("❌ Необходимо указать в config.yaml:")
        print("yandex_cloud:")
        print("  api_key: ваш_40_символьный_ключ")
        print("  folder_id: ваш_id_каталога")
        return

    # Тестирование подключения
    if args.test_connection:
        print("\n=== Тестирование подключения к Vision API ===")
        if test_connection(api_key, folder_id):
            print("✅ Подключение успешно!")
        else:
            print("❌ Проблемы с подключением")
        return

    # Создание процессора
    processor = YandexVisionProcessor(
        folder_id=folder_id,
        api_key=api_key
    )

    # Тестирование конкретного изображения
    if args.test_image:
        image_path = Path(args.test_image)
        print(f"\n=== Тестирование изображения: {image_path} ===")
        test_image_processing(processor, image_path)
        return

    # Стандартный режим: обработка последнего скриншота
    print("\n=== Обработка последнего скриншота ===")

    # Путь к скриншотам
    project_root = Path(__file__).resolve().parent.parent
    screenshot_dir = project_root / "screenshots"

    if not screenshot_dir.exists():
        print(f"❌ Папка со скриншотами не найдена: {screenshot_dir}")
        return

    # Поиск последнего скриншота
    screenshots = [f for f in screenshot_dir.iterdir()
                   if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg']]

    if not screenshots:
        print(f"❌ Нет скриншотов в {screenshot_dir}")
        return

    latest_screenshot = max(screenshots, key=lambda f: f.stat().st_mtime)

    # Обработка изображения
    test_image_processing(processor, latest_screenshot)


if __name__ == "__main__":
    main()