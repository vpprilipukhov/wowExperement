import base64
import logging
import time
import json
import os
import glob
from io import BytesIO
from PIL import Image
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate


class LocalVisionProcessor:
    def __init__(self, model_name="llama3:8b-instruct-q5_K_M"):
        """
        Упрощенный анализатор скриншотов для World of Warcraft
        :param model_name: Название модели Ollama
        """
        # Инициализация модели
        self.llm = Ollama(
            model=model_name,
            temperature=0.1,
            num_ctx=4096,
            num_gpu=50
        )

        # Настройка логирования
        self.logger = logging.getLogger("WoWVision")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler('wow_vision.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.info(f"Инициализирован анализатор с моделью: {model_name}")

    def _image_to_base64(self, image: Image.Image) -> str:
        """Конвертирует PIL.Image в base64 строку"""
        try:
            # Уменьшаем размер для производительности
            if image.width > 1024:
                new_height = int(1024 * image.height / image.width)
                image = image.resize((1024, new_height))
                self.logger.debug(f"Изображение уменьшено до 1024x{new_height}")

            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Ошибка конвертации изображения: {e}")
            return ""

    def analyze_image(self, image: Image.Image) -> dict:
        """
        Анализирует скриншот WoW с помощью LLM
        :param image: PIL.Image - скриншот игры
        :return: словарь с анализом
        """
        start_time = time.time()
        result = {
            "status": "error",
            "analysis": "",
            "processing_time": 0,
            "error": ""
        }

        try:
            if not image:
                self.logger.error("Получено пустое изображение")
                result["error"] = "Empty image"
                return result

            # Подготовка изображения
            img_base64 = self._image_to_base64(image)
            if not img_base64:
                result["error"] = "Image conversion failed"
                return result

            # Формирование простого промпта
            prompt = """
            Ты - эксперт по World of Warcraft. Анализируй скриншот и кратко опиши:
            1. Что происходит на экране?
            2. Какие ключевые элементы интерфейса видны?
            3. Что должен сделать игрок?

            Будь лаконичным - не более 3 предложений.
            """

            # Создаем промпт с изображением
            prompt_template = ChatPromptTemplate.from_messages([
                ("human",
                 "{prompt_text}\n"
                 "<image>\n")
            ])

            chain = prompt_template | self.llm

            # Отправка запроса
            self.logger.info("Отправка запроса к модели...")
            response = chain.invoke({
                "prompt_text": prompt,
                "image": img_base64
            })

            # Обработка ответа
            result["status"] = "success"
            result["analysis"] = response.strip()

            # Логирование производительности
            proc_time = time.time() - start_time
            result["processing_time"] = round(proc_time, 2)
            self.logger.info(f"Анализ завершен за {proc_time:.2f} сек")
            self.logger.info(f"Ответ модели: {response[:100]}...")

            return result

        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}", exc_info=True)
            result["error"] = str(e)
            return result

    def save_debug_info(self, image: Image.Image, response: str):
        """Сохраняет скриншот и ответ для отладки"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"debug_{timestamp}.jpg"
            image.save(filename)

            with open(f"debug_{timestamp}.txt", "w") as f:
                f.write(response)

            self.logger.info(f"Сохранен debug-пакет: {filename}")
        except Exception as e:
            self.logger.error(f"Не удалось сохранить debug-информацию: {e}")


def find_project_root(start_path=None):
    """Находит корневую директорию проекта"""
    if start_path is None:
        start_path = os.path.abspath(os.path.dirname(__file__))

    # Поднимаемся вверх по директориям, пока не найдем .git или другие маркеры
    current_path = start_path
    while current_path != os.path.dirname(current_path):  # Пока не достигли корня файловой системы
        # Проверяем маркеры проекта
        markers = ['.git', 'requirements.txt', 'main.py', 'README.md']
        if any(os.path.exists(os.path.join(current_path, marker)) for marker in markers):
            return current_path

        # Поднимаемся на уровень выше
        current_path = os.path.dirname(current_path)

    # Если не нашли, возвращаем текущую директорию скрипта
    return start_path


if __name__ == "__main__":
    print("Тестирование WoW Vision Processor...")
    processor = LocalVisionProcessor()

    # Находим корень проекта
    project_root = find_project_root()
    print(f"Корень проекта: {project_root}")

    # Папка со скриншотами в корне проекта
    screenshots_dir = os.path.join(project_root, "screenshots")
    print(f"Ищем скриншоты в: {screenshots_dir}")

    # Проверяем существование папки
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
        print(f"Создана папка для скриншотов: {screenshots_dir}")
        print("Пожалуйста, добавьте скриншоты в эту папку и запустите снова.")
        exit()

    # Ищем все файлы изображений
    screenshot_files = glob.glob(os.path.join(screenshots_dir, "*.jpg")) + \
                       glob.glob(os.path.join(screenshots_dir, "*.jpeg")) + \
                       glob.glob(os.path.join(screenshots_dir, "*.png"))

    if not screenshot_files:
        print(f"В папке {screenshots_dir} нет скриншотов!")
        print("Добавьте скриншоты для анализа.")
        exit()

    # Сортируем по времени изменения (последний измененный файл будет первым)
    screenshot_files.sort(key=os.path.getmtime, reverse=True)
    latest_screenshot = screenshot_files[0]

    print(f"Анализ последнего скриншота: {latest_screenshot}")

    try:
        # Загружаем изображение
        test_img = Image.open(latest_screenshot)
        print(f"Размер изображения: {test_img.size}")

        # Анализируем
        analysis = processor.analyze_image(test_img)

        print("\nРезультат анализа:")
        print(analysis["analysis"])

        # Сохраняем результаты для отладки
        if analysis["status"] == "success":
            processor.save_debug_info(test_img, analysis["analysis"])

    except Exception as e:
        print(f"Ошибка при обработке скриншота: {str(e)}")
        processor.logger.error(f"Ошибка теста: {str(e)}")