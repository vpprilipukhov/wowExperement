import base64
import os
import glob
import time
import logging
from io import BytesIO
from PIL import Image
import torch
import torchvision.transforms as transforms
from langchain_community.llms import Ollama

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vision_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def setup_device():
    """Определяем доступное устройство для вычислений (GPU/CPU)"""
    try:
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"Используется GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024 ** 3:.2f} GB")
        elif torch.backends.mps.is_available():  # Для Mac M1/M2
            device = torch.device("mps")
            logger.info("Используется Apple M1/M2 GPU (Metal)")
        else:
            device = torch.device("cpu")
            logger.warning("CUDA недоступно! Используется CPU. Производительность будет снижена")
        return device
    except Exception as e:
        logger.error(f"Ошибка инициализации устройства: {e}")
        return torch.device("cpu")


def find_screenshots_dir():
    """Находит папку со скриншотами с валидацией путей"""
    possible_paths = [
        "screenshots",
        "../screenshots",
        os.path.expanduser("~/screenshots"),
        "C:/screenshots",
        "/tmp/screenshots"
    ]

    logger.info("Поиск директории со скриншотами...")
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            logger.info(f"Директория найдена: {abs_path}")
            return abs_path

    # Создаем директорию если не найдена
    new_dir = os.path.abspath("screenshots")
    os.makedirs(new_dir, exist_ok=True)
    logger.warning(f"Директория не найдена. Создана новая: {new_dir}")
    return new_dir


def find_latest_screenshot():
    """Находит последний скриншот с валидацией форматов"""
    directory = find_screenshots_dir()
    logger.info(f"Сканирование директории: {directory}")

    valid_extensions = ['png', 'jpg', 'jpeg']
    screenshots = []
    for ext in valid_extensions:
        screenshots.extend(glob.glob(os.path.join(directory, f'*.{ext}')))

    if not screenshots:
        logger.error("Скриншоты не найдены. Добавьте изображения в директорию.")
        return None

    # Сортировка по времени модификации
    screenshots.sort(key=os.path.getmtime, reverse=True)
    latest = screenshots[0]
    logger.info(f"Выбран последний скриншот: {latest}")
    return latest


def preprocess_image(image_path, device, max_size=1024):
    """
    Обрабатывает изображение с использованием GPU:
    1. Загрузка и конвертация в тензор
    2. Автоматическое изменение размера
    3. Нормализация значений пикселей
    """
    try:
        logger.info(f"Начало обработки изображения: {image_path}")
        start_time = time.time()

        # Загрузка изображения
        with Image.open(image_path) as img:
            original_size = img.size
            logger.info(f"Оригинальный размер: {original_size}")

            # Конвертация в RGB если необходимо
            if img.mode != 'RGB':
                logger.info(f"Конвертация из {img.mode} в RGB")
                img = img.convert('RGB')

            # Автоматическое изменение размера с сохранением пропорций
            if max(original_size) > max_size:
                scale = max_size / max(original_size)
                new_size = tuple(int(dim * scale) for dim in original_size)
                logger.info(f"Изменение размера до: {new_size}")
                img = img.resize(new_size, Image.LANCZOS)

            # Преобразование в тензор PyTorch
            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Lambda(lambda x: x.to(device))
            ])
            img_tensor = transform(img).unsqueeze(0)  # Добавляем batch dimension

            # Нормализация (опционально)
            normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                             std=[0.229, 0.224, 0.225])
            img_tensor = normalize(img_tensor)

            # Конвертация обратно в PIL Image для base64
            to_pil = transforms.ToPILImage()
            processed_img = to_pil(img_tensor.squeeze(0).cpu())

            processing_time = time.time() - start_time
            logger.info(f"Обработка завершена за {processing_time:.2f} сек")
            return processed_img

    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {str(e)}")
        return None


def image_to_base64(pil_image):
    """Конвертирует PIL Image в base64 с оптимизацией"""
    try:
        logger.info("Конвертация в base64...")
        start_time = time.time()

        buffered = BytesIO()
        pil_image.save(buffered, format="JPEG", quality=85, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

        logger.info(f"Размер base64: {len(img_str) / 1024:.2f} KB")
        logger.info(f"Конвертация заняла {time.time() - start_time:.2f} сек")
        return img_str
    except Exception as e:
        logger.error(f"Ошибка конвертации в base64: {str(e)}")
        return None


def initialize_model(model_name="llama3.2-vision"):
    """Инициализация модели с обработкой ошибок"""
    try:
        logger.info(f"Инициализация модели: {model_name}")
        start_time = time.time()

        llm = Ollama(model=model_name)

        logger.info(f"Модель загружена за {time.time() - start_time:.2f} сек")
        return llm
    except Exception as e:
        logger.error(f"Ошибка инициализации модели: {str(e)}")
        logger.error(f"Убедитесь что модель установлена: ollama pull {model_name}")
        return None


def analyze_image(llm, image_base64, prompt):
    """Анализ изображения с помощью LLM"""
    try:
        logger.info("Отправка запроса к модели...")
        start_time = time.time()

        response = llm.invoke(
            input=prompt,
            images=[image_base64]
        )

        processing_time = time.time() - start_time
        logger.info(f"Анализ завершен за {processing_time:.2f} сек")
        return response.strip()
    except Exception as e:
        logger.error(f"Ошибка анализа изображения: {str(e)}")
        return None


def main():
    logger.info("=== GPU Vision Processor для WoW AI ===")

    # Инициализация устройства
    device = setup_device()

    # Поиск скриншота
    screenshot_path = find_latest_screenshot()
    if not screenshot_path:
        return

    # Предобработка изображения на GPU
    processed_image = preprocess_image(screenshot_path, device)
    if not processed_image:
        return

    # Конвертация в base64
    img_base64 = image_to_base64(processed_image)
    if not img_base64:
        return

    # Инициализация модели
    llm = initialize_model("llama3.2-vision")  # Используем работающую модель
    if not llm:
        return

    # Промпт для анализа WoW скриншота
    prompt = (
        "Ты опытный игрок в World of Warcraft. Проанализируй скриншот игрового интерфейса:\n"
        "1. Определи текущее окружение (локация, противники, союзники)\n"
        "2. Опиши состояние интерфейса (здоровье, мана, способности)\n"
        "3. Предложи 3 оптимальных действия для игрока\n"
        "4. Оцени опасность ситуации по шкале от 1 до 10\n\n"
        "Ответ предоставь в формате JSON с полями: location, player_status, actions, danger_level"
    )

    # Анализ изображения
    analysis_result = analyze_image(llm, img_base64, prompt)

    # Сохранение результата
    if analysis_result:
        logger.info("\n=== Результат анализа ===")
        logger.info(analysis_result)

        result_dir = os.path.dirname(screenshot_path)
        result_path = os.path.join(result_dir, "analysis_result.json")

        with open(result_path, "w", encoding="utf-8") as f:
            f.write(analysis_result)
        logger.info(f"Результат сохранен в: {result_path}")
    else:
        logger.error("Анализ не удался")


if __name__ == "__main__":
    main()