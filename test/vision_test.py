import base64
import os
import glob
import time
from io import BytesIO
from PIL import Image
from langchain_community.llms import Ollama


def find_screenshots_dir():
    """Находит папку со скриншотами в нескольких возможных местах"""
    possible_paths = [
        "screenshots",  # Текущая директория
        "../screenshots",  # Директория уровнем выше
        os.path.expanduser("~/screenshots"),  # Домашняя директория
        "C:/screenshots",  # Для Windows
        "/tmp/screenshots"  # Для Linux/Mac
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Если ни одна папка не найдена, создаем screenshots в текущей директории
    os.makedirs("screenshots", exist_ok=True)
    return "screenshots"


def find_latest_screenshot():
    """Находит последний скриншот в директории"""
    directory = find_screenshots_dir()
    print(f"Ищем скриншоты в: {os.path.abspath(directory)}")

    screenshots = glob.glob(os.path.join(directory, "*.png")) + \
                  glob.glob(os.path.join(directory, "*.jpg")) + \
                  glob.glob(os.path.join(directory, "*.jpeg"))

    if not screenshots:
        print("Скриншоты не найдены. Пожалуйста, добавьте скриншоты в папку.")
        return None

    # Сортировка по времени изменения
    screenshots.sort(key=os.path.getmtime, reverse=True)
    return screenshots[0]


def image_to_base64(image_path):
    """Конвертирует изображение в base64"""
    try:
        with Image.open(image_path) as img:
            # Автоматическое уменьшение размера
            if img.width > 1024:
                new_height = int(1024 * img.height / img.width)
                img = img.resize((1024, new_height))
                print(f"Изображение уменьшено до 1024x{new_height}")

            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Ошибка конвертации изображения: {e}")
        return None


def main():
    print("=== Простой тест анализатора WoW скриншотов ===")

    # 1. Находим последний скриншот
    screenshot_path = find_latest_screenshot()
    if not screenshot_path:
        return

    print(f"Анализируем скриншот: {screenshot_path}")

    # 2. Конвертируем изображение
    img_base64 = image_to_base64(screenshot_path)
    if not img_base64:
        print("Не удалось конвертировать изображение")
        return

    # 3. Инициализируем модель
    print("Инициализация модели...")
    try:
        llm = Ollama(model="llama3.2-vision")
    except Exception as e:
        print(f"Ошибка инициализации модели: {e}")
        print("Убедитесь, что модель установлена: ollama pull llama3.2-vision")
        return

    # 4. Простейший промпт
    prompt = "Ты игрок в World of Warcraft. Расскажи, что ты видишь на этом скриншоте?"

    # 5. Засекаем время и отправляем запрос
    start_time = time.time()
    print("\nОтправка запроса к модели...")

    try:
        response = llm.invoke(
            input=prompt,
            images=[img_base64]
        )
    except Exception as e:
        print(f"Ошибка при анализе изображения: {e}")
        return

    # 6. Выводим результат
    processing_time = time.time() - start_time
    print("\n=== Результат анализа ===")
    print(response.strip())
    print(f"\nВремя обработки: {processing_time:.2f} секунд")

    # 7. Сохраняем результат для сравнения
    result_path = os.path.join(os.path.dirname(screenshot_path), "last_analysis.txt")
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(response.strip())
    print(f"Результат сохранен в: {result_path}")


if __name__ == "__main__":
    main()