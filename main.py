# main.py - Основной модуль WoW бота
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time
import sys
from pathlib import Path

# Настройка системы путей
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.append(str(PROJECT_ROOT))


class WoWBot:
    def __init__(self):
        """Инициализация бота с защищенным логированием"""
        self._setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.action_history: List[Dict] = []
        self._start_time = datetime.now()

        try:
            self.logger.info("=== ИНИЦИАЛИЗАЦИЯ БОТА ===")
            self._init_components()
            self.logger.info("Бот успешно инициализирован")
        except Exception as e:
            self.logger.critical(f"Ошибка инициализации бота: {str(e)}", exc_info=True)
            raise

    def _setup_logging(self):
        """Настройка системы логирования"""
        logs_dir = PROJECT_ROOT / 'logs'
        logs_dir.mkdir(exist_ok=True)

        handlers = [
            logging.FileHandler(
                filename=logs_dir / f'bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=handlers
        )
        logging.getLogger('pyautogui').setLevel(logging.WARNING)

    def _init_components(self):
        """Инициализация всех компонентов системы"""
        from agents.llm_provider import YandexGPTProvider
        from agents.action_planner import ActionPlanner
        from controllers.movement_controller import MovementController
        from environment.wow_environment import WowEnvironment

        self.logger.info("Инициализация компонентов:")

        self.llm_provider = YandexGPTProvider()
        self.planner = ActionPlanner(self.llm_provider)
        self.mover = MovementController()
        self.env = WowEnvironment()

        # Проверка работоспособности окружения
        test_state = self.env.get_game_state()
        if test_state.get('status') != 'success':
            raise RuntimeError(f"Ошибка проверки окружения: {test_state.get('reason')}")

    def run(self):
        """Основной рабочий цикл бота"""
        self.logger.info("=== ЗАПУСК ОСНОВНОГО ЦИКЛА ===")
        loop_counter = 0

        try:
            while True:
                loop_counter += 1
                self.logger.debug(f"Начало цикла #{loop_counter}")

                try:
                    self._game_loop()
                except Exception as e:
                    self.logger.error(f"Ошибка в цикле #{loop_counter}: {str(e)}", exc_info=True)
                    time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Остановка по запросу пользователя")
        except Exception as e:
            self.logger.critical(f"Фатальная ошибка: {str(e)}", exc_info=True)
        finally:
            self._shutdown()

    def _game_loop(self):
        """Одна итерация игрового цикла"""
        # 1. Сбор данных
        game_state = self._collect_game_data()
        if not game_state:
            raise ValueError("Не удалось получить состояние игры")

        # 2. Планирование действия
        action = self._plan_action(game_state)
        if not action:
            raise ValueError("Не удалось запланировать действие")

        # 3. Выполнение действия
        self._execute_action(action, game_state)

    def _collect_game_data(self) -> Optional[Dict]:
        """Сбор данных о состоянии игры"""
        try:
            state = self.env.get_game_state()
            if state.get("status") != "success":
                self.logger.warning(f"Ошибка состояния: {state.get('reason')}")
                return None

            self.logger.debug(f"Состояние игры: {state}")
            return state
        except Exception as e:
            self.logger.error(f"Ошибка сбора данных: {str(e)}", exc_info=True)
            return None

    def _plan_action(self, game_state: Dict) -> Optional[Dict]:
        """Планирование следующего действия"""
        try:
            action = self.planner.plan_action({
                "game_state": game_state,
                "history": self.action_history[-5:] if self.action_history else [],
                "inventory": [],
                "abilities": []
            })

            if action.get("status") != "success":
                self.logger.warning(f"Ошибка планирования: {action.get('reason')}")
                return None

            self.logger.info(f"Запланировано действие: {action['action']}")
            return action
        except Exception as e:
            self.logger.error(f"Ошибка планирования: {str(e)}", exc_info=True)
            return None

    def _execute_action(self, action: Dict, game_state: Dict):
        """Выполнение запланированного действия"""
        try:
            self.action_history.append({
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "game_state": game_state
            })

            self.mover.execute(action)
            self.logger.info(f"Выполнено действие: {action['action']}")
        except Exception as e:
            self.logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
            raise

    def _shutdown(self):
        """Корректное завершение работы"""
        self.logger.info("Завершение работы...")
        try:
            self.env.cleanup()
        except Exception as e:
            self.logger.error(f"Ошибка при завершении: {str(e)}")
        finally:
            self.logger.info("=== РАБОТА БОТА ЗАВЕРШЕНА ===")


if __name__ == "__main__":
    try:
        bot = WoWBot()
        bot.run()
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске: {str(e)}", exc_info=True)
        raise