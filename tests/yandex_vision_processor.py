import logging
import time
import requests
import base64
import re
from PIL import Image, ImageEnhance
import io
import numpy as np
import cv2
from pathlib import Path
import yaml
import json

from yandex_iam import YandexIAMTokenManager


class YandexVisionProcessor:
    def __init__(self, iam_token_manager, folder_id):
        """
        Инициализация процессора для работы с Yandex Vision API

        :param iam_token_manager: экземпляр YandexIAMTokenManager
        :param folder_id: ID каталога в Yandex Cloud
        """
        self.iam_token_manager = iam_token_manager
        self.folder_id = folder_id
        self.logger = logging.getLogger("YandexVisionProcessor")
        self.logger.setLevel(logging.INFO)

        # Настройка обработчика логов
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.info("Инициализация Yandex Vision Processor")

    def enhance_image_for_ocr(self, image_data: bytes) -> bytes:
        """
        Улучшает изображение для лучшего распознавания текста
        - Увеличивает контраст и резкость
        - Удаляет шумы
        - Оптимизирует цвета
        """
        try:
            # Открываем изображение
            img = Image.open(io.BytesIO(image_data))

            # Увеличиваем контраст
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)

            # Увеличиваем резкость
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)

            # Конвертируем в OpenCV формат для дополнительной обработки
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # Уменьшаем шум
            img_cv = cv2.fastNlMeansDenoisingColored(img_cv, None, 10, 10, 7, 21)

            # Преобразуем обратно в PIL
            img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))

            # Сохраняем в буфер
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=95)
            return buffer.getvalue()

        except Exception as e:
            self.logger.error(f"Ошибка улучшения изображения: {str(e)}")
            return image_data

    def compress_image(self, image_data: bytes, max_size_mb: float = 0.9) -> bytes:
        """
        Сжимает изображение до приемлемого размера для Vision API
        """
        try:
            # Рассчитываем максимальный размер в байтах
            max_size_bytes = int(max_size_mb * 1024 * 1024 * 0.75)

            if len(image_data) <= max_size_bytes:
                return image_data

            img = Image.open(io.BytesIO(image_data))

            # Конвертируем RGBA в RGB
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            # Параметры сжатия
            quality = 90
            while quality >= 50:
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=quality, optimize=True)
                compressed_data = buffer.getvalue()

                if len(compressed_data) <= max_size_bytes:
                    self.logger.info(f"Изображение сжато до {len(compressed_data)} байт (quality: {quality}%)")
                    return compressed_data

                quality -= 10

            return compressed_data

        except Exception as e:
            self.logger.error(f"Ошибка сжатия изображения: {str(e)}")
            return image_data

    def extract_game_state(self, response: dict) -> dict:
        """
        Анализирует полный ответ Vision API и извлекает состояние игры

        :param response: полный JSON-ответ от Vision API
        :return: словарь с состоянием игры (hp, resource)
        """
        game_state = {"hp": None, "resource": None}

        # Сохраняем полный ответ для анализа
        with open("vision_response.json", "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=2)

        # Извлекаем все текстовые блоки с координатами
        text_blocks = []
        try:
            if "results" in response and response["results"]:
                for page in response["results"][0]["results"][0]["textDetection"]["pages"]:
                    for block in page["blocks"]:
                        for line in block["lines"]:
                            for word in line["words"]:
                                text_blocks.append({
                                    "text": word["text"],
                                    "confidence": word["confidence"],
                                    "bounding_box": word["boundingBox"]["vertices"]
                                })
        except (KeyError, TypeError) as e:
            self.logger.error(f"Ошибка разбора ответа API: {str(e)}")
            return game_state

        if not text_blocks:
            self.logger.error("Не найдено текстовых блоков для анализа")
            return game_state

        # Анализируем текст с помощью эвристик
        game_state = self.analyze_text_blocks(text_blocks)

        return game_state

    def analyze_text_blocks(self, text_blocks: list) -> dict:
        """
        Применяет интеллектуальные эвристики для определения HP и ресурса
        """
        game_state = {"hp": None, "resource": None}

        # Эвристика 1: Ищем значения в формате "число/число"
        fraction_values = []
        for block in text_blocks:
            if re.match(r'^\d+\s*/\s*\d+$', block["text"]):
                fraction_values.append(block)

        # Если найдено несколько значений, выбираем самые надежные
        if fraction_values:
            # Сортируем по достоверности и позиции на экране
            fraction_values.sort(
                key=lambda x: (
                    -x["confidence"],
                    self.calculate_screen_position_score(x["bounding_box"])
                )
            )

            # Первое значение - вероятно HP
            game_state["hp"] = fraction_values[0]["text"]

            # Второе значение - вероятно ресурс
            if len(fraction_values) > 1:
                game_state["resource"] = fraction_values[1]["text"]

        # Эвристика 2: Ищем ключевые слова (health, mana и т.д.)
        if not game_state["hp"]:
            for block in text_blocks:
                text = block["text"].lower()
                if "health" in text or "hp" in text:
                    # Ищем числовое значение рядом
                    nearby_value = self.find_nearby_value(block, text_blocks)
                    if nearby_value:
                        game_state["hp"] = nearby_value

        if not game_state["resource"]:
            for block in text_blocks:
                text = block["text"].lower()
                if "mana" in text or "energy" in text or "resource" in text:
                    # Ищем числовое значение рядом
                    nearby_value = self.find_nearby_value(block, text_blocks)
                    if nearby_value:
                        game_state["resource"] = nearby_value

        # Эвристика 3: Ищем числовые значения в нижней части экрана
        if not game_state["hp"]:
            bottom_values = [
                block for block in text_blocks
                if block["text"].isdigit() and self.is_in_bottom_area(block["bounding_box"])
            ]
            if bottom_values:
                # Берем самое большое число (вероятно, это HP)
                bottom_values.sort(key=lambda x: int(x["text"]), reverse=True)
                game_state["hp"] = bottom_values[0]["text"]

        # Логируем результаты
        if game_state["hp"]:
            self.logger.info(f"Определено здоровье: {game_state['hp']}")
        else:
            self.logger.warning("Не удалось определить здоровье")

        if game_state["resource"]:
            self.logger.info(f"Определен ресурс: {game_state['resource']}")
        else:
            self.logger.warning("Не удалось определить ресурс")

        return game_state

    def calculate_screen_position_score(self, vertices: list) -> float:
        """
        Вычисляет оценку позиции на экране (нижняя часть экрана получает более высокий балл)
        """
        # Вычисляем среднюю Y-координату
        y_coords = [v.get("y", 0) for v in vertices]
        avg_y = sum(y_coords) / len(y_coords)

        # Чем ниже на экране, тем выше оценка (от 0 до 1)
        return avg_y / 1000  # Нормализуем предполагаемую высоту экрана

    def is_in_bottom_area(self, vertices: list) -> bool:
        """
        Проверяет, находится ли текст в нижней трети экрана
        """
        y_coords = [v.get("y", 0) for v in vertices]
        avg_y = sum(y_coords) / len(y_coords)
        return avg_y > 600  # Предполагаем, что экран высотой около 900px

    def find_nearby_value(self, keyword_block: dict, all_blocks: list, max_distance: float = 100.0) -> str:
        """
        Ищет числовое значение рядом с ключевым словом
        """
        # Вычисляем центр ключевого слова
        k_vertices = keyword_block["bounding_box"]
        k_x = sum(v.get("x", 0) for v in k_vertices) / len(k_vertices)
        k_y = sum(v.get("y", 0) for v in k_vertices) / len(k_vertices)

        # Ищем ближайшее числовое значение
        closest_value = None
        min_distance = float('inf')

        for block in all_blocks:
            if block == keyword_block:
                continue

            if re.match(r'^\d+$', block["text"]) or re.match(r'^\d+\s*/\s*\d+$', block["text"]):
                # Вычисляем центр блока
                b_vertices = block["bounding_box"]
                b_x = sum(v.get("x", 0) for v in b_vertices) / len(b_vertices)
                b_y = sum(v.get("y", 0) for v in b_vertices) / len(b_vertices)

                # Вычисляем расстояние
                distance = ((b_x - k_x) ** 2 + (b_y - k_y) ** 2) ** 0.5

                if distance < min_distance and distance < max_distance:
                    min_distance = distance
                    closest_value = block["text"]

        return closest_value

    def process_image(self, image_data: bytes) -> dict:
        """
        Обрабатывает изображение с помощью Yandex Vision API

        :param image_data: бинарные данные изображения
        :return: словарь с результатами распознавания
        """
        self.logger.info(f"Обработка изображения размером {len(image_data)} байт")

        # Улучшаем изображение для распознавания
        enhanced_image = self.enhance_image_for_ocr(image_data)

        # Сжимаем изображение при необходимости
        compressed_image = self.compress_image(enhanced_image)
        content = base64.b64encode(compressed_image).decode('utf-8')

        # Формируем тело запроса
        request_body = {
            "folderId": self.folder_id,
            "analyzeSpecs": [{
                "content": content,
                "features": [{
                    "type": "TEXT_DETECTION",
                    "textDetectionConfig": {
                        "languageCodes": ["*"],
                        "model": "page"  # Используем точную модель для документов
                    }
                }],
                "mimeType": "image/jpeg"
            }]
        }

        # Получаем IAM-токен
        iam_token = self.iam_token_manager.get_iam_token()

        # Отправляем запрос
        response = self._send_request(iam_token, request_body)

        # Анализируем полный ответ
        game_state = self.extract_game_state(response)

        return game_state

    def _send_request(self, iam_token: str, request_body: dict, max_retries: int = 3) -> dict:
        """
        Отправляет запрос к Vision API с обработкой ошибок и повторами
        """
        url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
        headers = {
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json"
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=request_body, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Слишком много запросов. Повтор через {wait_time} сек...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Ошибка {e.response.status_code}: {e.response.text}")
                    raise

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                wait_time = 2 ** attempt
                self.logger.warning(f"Сетевая ошибка: {str(e)}. Повтор через {wait_time} сек...")
                time.sleep(wait_time)

            except Exception as e:
                self.logger.exception("Непредвиденная ошибка при отправке запроса")
                raise

        raise RuntimeError(f"Не удалось выполнить запрос после {max_retries} попыток")


# Пример использования
if __name__ == "__main__":
    # Создаем менеджер токенов
    token_manager = YandexIAMTokenManager()

    try:
        # Получаем folder_id из конфига
        config_path = Path(__file__).parent.parent / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            folder_id = config['yandex_cloud']['folder_id']

        # Инициализируем процессор
        processor = YandexVisionProcessor(
            iam_token_manager=token_manager,
            folder_id=folder_id
        )

        # Загружаем тестовое изображение
        screenshot_path = "screenshots/game_state_12345.png"
        with open(screenshot_path, "rb") as f:
            image_data = f.read()

        # Обрабатываем изображение
        result = processor.process_image(image_data)

        print("\nРезультаты распознавания:")
        print(f"HP: {result.get('hp', 'N/A')}")
        print(f"Ресурс: {result.get('resource', 'N/A')}")

        # Сохраняем улучшенное изображение для отладки
        enhanced = processor.enhance_image_for_ocr(image_data)
        with open("enhanced_image.jpg", "wb") as f:
            f.write(enhanced)
        print("Улучшенное изображение сохранено как 'enhanced_image.jpg'")

    except Exception as e:
        print(f"\n🔥 Критическая ошибка: {str(e)}")
        import traceback

        traceback.print_exc()