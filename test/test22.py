import base64
import os
import glob
import time
import logging
from io import BytesIO
from PIL import Image
from langchain_community.llms import Ollama
import torch  # Для проверки доступности GPU

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("WoWVisionGPU")


def check_gpu():
    """Проверяет доступность GPU и возвращает информацию"""
    gpu_info = {"available": False, "type": "None"}

    if torch.cuda.is_available():
        gpu_info["available"] = True
        gpu_info["type"] = torch.cuda.get_device_name(0)
        gpu_info["memory"] = f"{torch.cuda.get_device_properties(0).total_memory / 1024 ** 3:.2f} GB"

    return gpu_info


def find_screenshots_dir():
    """Находит папку со скриншотами"""
    # Проверяем папку в корне проекта
    project_root = os.path.dirname(os.path.abspath(__file__))
    screenshots_path = os.path.join(project_root, "screenshots")

    if os.path.exists(screenshots_path):
        return screenshots_path

    # Проверяем другие возможные расположения
    possible_paths = [
        os.path.expanduser("~/screenshots"),
        "/screenshots",
        "C:/screenshots",
        "/tmp/screenshots"
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Создаем папку
    os.makedirs(screenshots_path, exist_ok=True)
    return screenshots_path


def find_latest_screenshot(directory):
    """Находит последний скриншот в директории"""
    screenshots = glob.glob(os.path.join(directory, "*.png")) + \
                  glob.glob(os.path.join(directory, "*.jpg")) + \
                  glob.glob(os.path.join(directory, "*.jpeg"))

    if not screenshots:
        return None

    screenshots.sort(key=os.path.getmtime, reverse=True)
    return screenshots[0]


def optimize_image(image_path, target_size=1024):
    """Оптимизирует изображение для обработки на GPU"""
    try:
        with Image.open(image_path) as img:
            # Сохраняем соотношение сторон
            if img.width > target_size:
                ratio = target_size / float(img.width)
                new_height = int(float(img.height) * float(ratio))
                img = img.resize((target_size, new_height))
                logger.info(f"Изображение уменьшено до {target_size}x{new_height}")

            # Конвертация в RGB (если нужно)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=90)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка оптимизации изображения: {e}")
        return None


def main():
    logger.info("=== Оптимизированный анализатор WoW для GPU ===")

    # Проверка GPU
    gpu_info = check_gpu()
    logger.info(
        f"Информация о GPU: Доступен: {gpu_info['available']}, Тип: {gpu_info['type']}, Память: {gpu_info.get('memory', 'N/A')}")

    # Настройки для мощной видеокарты
    gpu_layers = 100  # Максимальное использование GPU
    model_name = "llama3.2-vision"

    # Находим скриншоты
    screenshots_dir = find_screenshots_dir()
    logger.info(f"Папка со скриншотами: {screenshots_dir}")

    screenshot_path = find_latest_screenshot(screenshots_dir)
    if not screenshot_path:
        logger.error("Скриншоты не найдены! Добавьте файлы в папку.")
        return

    logger.info(f"Анализируем скриншот: {screenshot_path}")

    # Оптимизируем изображение
    img_base64 = optimize_image(screenshot_path)
    if not img_base64:
        logger.error("Не удалось подготовить изображение")
        return

    # Инициализация модели с оптимизацией для GPU
    try:
        logger.info(f"Инициализация модели {model_name} с GPU-оптимизацией...")
        llm = Ollama(
            model=model_name,
            num_gpu=gpu_layers,  # 100% использование GPU
            num_thread=16,  # Максимальное количество потоков
            num_ctx=4096,  # Размер контекста
            temperature=0.1  # Для более детерминированных ответов
        )
    except Exception as e:
        logger.error(f"Ошибка инициализации модели: {e}")
        logger.error("Убедитесь, что модель установлена: ollama pull llama3.2-vision")
        return

    # Промпт для детального анализа
    prompt = """
    Ты профессиональный игрок в World of Warcraft. Детально опиши, что ты видишь на этом скриншоте:
    1. Точное название локации
    2. Состояние персонажа (здоровье, мана, уровень, активные эффекты)
    3. Основные цели и их состояние
    4. Видимые элементы интерфейса
    5. Что происходит в данный момент
    6. Что ты планируешь делать дальше

    Будь максимально точным и используй игровую терминологию.
    """

    # Анализ с замером времени
    start_time = time.time()
    logger.info("Начинаем анализ...")

    try:
        response = llm.invoke(
            input=prompt,
            images=[img_base64]
        )
    except Exception as e:
        logger.error(f"Ошибка при анализе: {e}")
        return

    # Результаты
    processing_time = time.time() - start_time
    logger.info("\n=== Результат анализа ===")
    print(response.strip())
    logger.info(f"\nВремя обработки: {processing_time:.2f} секунд")

    # Дополнительная информация
    logger.info(f"Размер входных данных: {len(img_base64) / 1024:.2f} KB")
    logger.info(f"Длина ответа: {len(response)} символов")


if __name__ == "__main__":
    main()