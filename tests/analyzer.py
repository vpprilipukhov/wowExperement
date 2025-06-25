import sys
from pathlib import Path
import logging
import time
import pyautogui

# Настройка путей
project_root = Path(__file__).parent.parent.resolve()
sys.path.append(str(project_root))

from environment.wow_environment import WowEnvironment


def setup_logging():
    """Настройка логирования с сохранением в /logs"""
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)  # Создаём папку, если её нет

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / "analyzer.log"),
            logging.StreamHandler()
        ]
    )


def is_wow_active(window_title="World of Warcraft"):
    """Проверяет, активно ли окно WoW"""
    try:
        window = pyautogui.getWindowsWithTitle(window_title)
        return len(window) > 0 and window[0].isActive
    except Exception:
        return False


def analyze_game_state():
    """Анализирует состояние игры с проверками"""
    logger = logging.getLogger("ANALYZER")
    env = WowEnvironment()

    logger.info("=== ЗАПУСК АНАЛИЗАТОРА ===")

    try:
        while True:
            # 1. Проверяем, что WoW открыт и активен
            if not is_wow_active():
                logger.error("ОШИБКА: WoW не запущен или окно не активно!")
                time.sleep(3)
                continue

            # 2. Получаем состояние игры
            state = env.get_game_state()

            if state.get("status") != "success":
                logger.error(f"ОШИБКА: {state.get('reason', 'Неизвестная ошибка')}")
                time.sleep(2)
                continue

            # 3. Выводим ТОЛЬКО реальные данные
            logger.info("\n=== АНАЛИЗ ===")

            # Позиция (x, y) — координаты персонажа на экране в пикселях
            pos = state.get("position")
            if pos:
                logger.info(f"ПОЗИЦИЯ: [X: {pos[0]}, Y: {pos[1]}] (пиксели от левого верхнего угла экрана)")
            else:
                logger.warning("Позиция не определена!")

            # Здоровье (если есть)
            health = state.get("health")
            if health is not None:
                logger.info(f"ЗДОРОВЬЕ: {health}%")
            else:
                logger.warning("Здоровье не определено!")

            # Другие параметры
            logger.info(f"ВРАГИ: {len(state.get('enemies', []))}")
            logger.info(f"NPC: {len(state.get('npcs', []))}")

            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Анализатор остановлен")
    finally:
        env.cleanup()


if __name__ == "__main__":
    setup_logging()
    analyze_game_state()