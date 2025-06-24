import logging
from datetime import datetime
from typing import Dict, List
from wow_environment import WowEnvironment
from agents.action_planner import ActionPlanner
from agents.movement_controller import MovementController


class WoWBot:
    def __init__(self):
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self._init_components()
        self.action_history: List[Dict] = []

    def _setup_logging(self):
        """Настройка расширенного логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )

    def _init_components(self):
        """Инициализация всех компонентов системы"""
        self.logger.info("Инициализация компонентов...")

        try:
            self.env = WowEnvironment()
            self.planner = ActionPlanner()
            self.mover = MovementController()

            # Тестовая проверка работы окружения
            test_state = self.env.get_game_state()
            if test_state.get('status') != 'success':
                raise RuntimeError(f"Не удалось получить начальное состояние: {test_state.get('reason')}")

            self.logger.info("Все компоненты успешно инициализированы")
        except Exception as e:
            self.logger.critical(f"Ошибка инициализации: {str(e)}", exc_info=True)
            raise

    def run(self):
        """Основной цикл работы бота"""
        self.logger.info("=== ЗАПУСК БОТА ===")

        try:
            while True:
                self._game_loop()

        except KeyboardInterrupt:
            self.logger.info("Остановка по запросу пользователя")
        except Exception as e:
            self.logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        finally:
            self._shutdown()

    def _game_loop(self):
        """Один цикл обработки игры"""
        # 1. Сбор данных
        game_state = self._collect_game_data()
        if not game_state:
            time.sleep(1)  # Задержка при ошибке
            return

        # 2. Планирование действия
        action = self._plan_action(game_state)
        if not action:
            return

        # 3. Выполнение действия
        self._execute_action(action, game_state)

    def _collect_game_data(self) -> Dict:
        """Собирает данные о текущем состоянии игры"""
        try:
            state = self.env.get_game_state()

            if state.get("status") != "success":
                self.logger.warning(f"Не удалось получить состояние игры: {state.get('reason')}")
                return None

            self.logger.debug(f"Состояние игры: { {k: v for k, v in state.items() if k != 'frame'} }")
            return state

        except Exception as e:
            self.logger.error(f"Ошибка сбора данных: {str(e)}")
            return None

    def _plan_action(self, game_state: Dict) -> Dict:
        """Генерирует действие через LLM"""
        try:
            start_time = datetime.now()
            action = self.planner.plan_action({
                "game_state": game_state,
                "history": self.action_history[-5:] if self.action_history else [],
                "inventory": [],
                "abilities": []
            })
            latency = (datetime.now() - start_time).total_seconds()

            if action.get("status") != "success":
                self.logger.warning(f"Ошибка планирования: {action.get('reason')}")
                return None

            self.logger.info(f"Запланировано действие: {action['action']} (за {latency:.2f}с)")
            return action

        except Exception as e:
            self.logger.error(f"Ошибка планирования: {str(e)}")
            return None

    def _execute_action(self, action: Dict, game_state: Dict):
        """Выполняет запланированное действие"""
        try:
            # Логирование перед выполнением
            self.action_history.append({
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "game_state": {k: v for k, v in game_state.items() if k != 'frame'}
            })

            # Выполнение действия
            self.mover.execute(action)

        except Exception as e:
            self.logger.error(f"Ошибка выполнения: {str(e)}")

    def _shutdown(self):
        """Корректное завершение работы"""
        self.logger.info("Завершение работы...")
        self.env.cleanup()  # Теперь метод существует
        self.logger.info("=== БОТ ОСТАНОВЛЕН ===")


if __name__ == "__main__":
    import time

    bot = WoWBot()
    bot.run()