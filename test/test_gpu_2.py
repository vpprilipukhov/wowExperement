import torch
from langchain_community.llms import Ollama
import time
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_gpu():
    """Проверяет доступность GPU и его использование"""
    # Проверка PyTorch
    logger.info("=== Проверка GPU через PyTorch ===")
    logger.info(f"Доступно GPU: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"Количество GPU: {torch.cuda.device_count()}")
        logger.info(f"Имя GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024 ** 3:.2f} GB")

    # Проверка Ollama
    logger.info("\n=== Проверка GPU через Ollama ===")
    os.environ["OLLAMA_NUM_GPU"] = "1"  # Форсируем использование GPU

    try:
        llm = Ollama(model="llama3.2-vision", num_gpu=1)
        logger.info("Модель инициализирована с параметром num_gpu=1")

        # Тестовый запрос
        start_time = time.time()
        response = llm.invoke("Ответь только 'OK'")
        logger.info(f"Тестовый ответ: {response}")
        logger.info(f"Время выполнения: {time.time() - start_time:.2f} сек")
    except Exception as e:
        logger.error(f"Ошибка: {e}")


def monitor_gpu_usage():
    """Мониторинг использования GPU во время выполнения"""
    logger.info("\n=== Мониторинг использования GPU ===")

    # Проверка через nvidia-smi (для Windows)
    try:
        import subprocess

        # Запускаем nvidia-smi в фоновом режиме
        process = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv", "-l", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Даем время на запуск мониторинга
        time.sleep(2)

        # Запускаем тестовый запрос
        llm = Ollama(model="llama3.2-vision")
        start_time = time.time()
        response = llm.invoke("Ответь только 'GPU TEST'")
        logger.info(f"Ответ модели: {response}")
        logger.info(f"Время выполнения: {time.time() - start_time:.2f} сек")

        # Останавливаем мониторинг
        process.terminate()

        # Выводим результаты мониторинга
        stdout, stderr = process.communicate()
        logger.info("\nРезультаты nvidia-smi:")
        logger.info(stdout)

    except Exception as e:
        logger.error(f"Ошибка мониторинга GPU: {e}")
        logger.info("Убедитесь, что nvidia-smi установлен и доступен в PATH")


if __name__ == "__main__":
    check_gpu()
    monitor_gpu_usage()