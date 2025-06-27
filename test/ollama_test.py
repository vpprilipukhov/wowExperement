# ollama_test.py
import logging
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("OllamaTest")


def test_ollama_connection():
    """Тестирует базовое подключение к локальной модели Llama"""
    try:
        logger.info("Инициализация модели Llama 3.2...")

        # Инициализируем модель с оптимизированными параметрами
        llm = Ollama(
            model="llama3:8b-instruct-q5_K_M",
            temperature=0.3,
            num_predict=128,
            num_ctx=2048
        )

        logger.info("Создание тестового промпта...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Ты - помощник для тестирования подключения и работоспособности."),
            ("human", "Привет! Назови 3 главных особенности модели llama3:8b-instruct-q5_K_M "),
            ("human", " какая  сейчас погода в москве ?")

        ])

        logger.info("Отправка запроса модели...")
        chain = prompt | llm
        response = chain.invoke({"model_name": "Llama 3.2"})

        logger.info("Тест пройден успешно!")
        logger.info(f"Ответ модели:\n{response}")

        return True

    except Exception as e:
        logger.error(f"Ошибка подключения: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("=== Начало теста Ollama ===")
    success = test_ollama_connection()

    if success:
        logger.info("✅ Тест пройден успешно! Модель работает корректно.")
    else:
        logger.error("❌ Тест не пройден. Проверьте настройки Ollama.")