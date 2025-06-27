import base64
import os
import glob
import time
import logging
import re
from io import BytesIO
from PIL import Image
from langchain_community.llms import Ollama

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def find_latest_screenshot(directory="screenshots"):
    """Быстрый поиск последнего скриншота"""
    files = glob.glob(os.path.join(directory, "*.png"))
    files += glob.glob(os.path.join(directory, "*.jpg"))
    files += glob.glob(os.path.join(directory, "*.jpeg"))

    if not files:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        logger.error("Скриншоты не найдены!")
        return None

    return max(files, key=os.path.getmtime)


def crop_health_bar(image_path, crop_height=100):
    """Обрезает область с полосой здоровья"""
    try:
        with Image.open(image_path) as img:
            # Обрезаем верхнюю часть изображения (где обычно здоровье)
            width, height = img.size
            crop_box = (0, 0, width, crop_height)
            cropped = img.crop(crop_box)

            # Уменьшаем размер
            cropped = cropped.resize((width // 2, crop_height // 2), Image.NEAREST)

            buffered = BytesIO()
            cropped.save(buffered, format="JPEG", quality=85)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {str(e)}")
        return None


def main():
    logger.info("=== Быстрый анализатор здоровья в WoW ===")

    # Форсируем использование GPU
    os.environ["OLLAMA_NUM_GPU"] = "1"

    # Поиск скриншота
    screenshot_path = find_latest_screenshot()
    if not screenshot_path:
        return

    logger.info(f"Анализируем: {screenshot_path}")

    # Подготовка изображения: обрезаем только область здоровья
    start_time = time.time()
    img_base64 = crop_health_bar(screenshot_path, crop_height=150)
    if not img_base64:
        return

    prep_time = time.time() - start_time
    logger.info(f"Изображение подготовлено за {prep_time:.3f} сек")

    # Инициализация модели
    try:
        llm = Ollama(model="llama3.2-vision", num_gpu=1, temperature=0.0)
    except Exception as e:
        logger.error(f"Ошибка загрузки модели: {e}")
        return

    # Оптимизированный промпт
    prompt = "Только число здоровья (HP) персонажа:"

    # Анализ
    logger.info("Определяем здоровье...")
    start_analysis = time.time()

    try:
        response = llm.invoke(input=prompt, images=[img_base64])
        analysis_time = time.time() - start_analysis

        # Ищем число в ответе
        match = re.search(r'\d+', response)
        hp_value = match.group(0) if match else None

        logger.info("\n=== Результат ===")
        logger.info(f"Здоровье: {hp_value or 'N/A'} HP")
        logger.info(f"Время анализа: {analysis_time:.2f} сек")
        logger.info(f"Общее время: {time.time() - start_time:.2f} сек")

        # Сохраняем результат
        result_path = os.path.join(os.path.dirname(screenshot_path), "hp_result.txt")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write(f"Здоровье: {hp_value or 'N/A'}")
        logger.info(f"Результат сохранен в: {result_path}")

    except Exception as e:
        logger.error(f"Ошибка анализа: {str(e)}")


if __name__ == "__main__":
    main()