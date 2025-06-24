from agents.llm_provider import LLMProvider
from agents.action_planner import ActionPlanner
from agents.code_generator import CodeGenerator
from envs.wow_environment import WoWEnvironment
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    try:
        logger.info("Инициализация компонентов...")

        # Инициализация LLMProvider
        llm_provider = LLMProvider()

        # Тестовый запрос для проверки подключения
        try:
            test_response = llm_provider.get_completion([
                {"role": "user", "text": "Тестовое сообщение"}
            ])
            logger.info("Подключение к Yandex GPT успешно")
        except Exception as e:
            logger.error(f"Ошибка подключения: {str(e)}")
            return

        # Инициализация остальных компонентов
        env = WoWEnvironment()
        planner = ActionPlanner()
        code_generator = CodeGenerator(llm_provider)

        logger.info("Запуск основного цикла...")
        for i in range(3):  # Ограничим цикл для теста
            try:
                game_state = env.get_game_state()
                logger.info(f"Состояние игры: {game_state}")

                task_result = planner.plan_action(
                    game_state=game_state,
                    history=[],
                    inventory=[],
                    abilities=[]
                )

                if task_result["status"] == "success":
                    logger.info(f"Сгенерировано действие: {task_result['action']}")
                else:
                    logger.warning(f"Ошибка планирования: {task_result['reason']}")

            except Exception as e:
                logger.error(f"Ошибка в цикле: {str(e)}")

            time.sleep(1)

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")


if __name__ == "__main__":
    main()