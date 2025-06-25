# wow_bot.py - Основной класс бота для World of Warcraft с расширенным логированием
import logging
from datetime import datetime
from typing import Dict, List
import time

from agents.action_planner import ActionPlanner
from agents.llm_provider import YandexGPTProvider
from agents.movement_controller import MovementController
from wow_environment import WowEnvironment


class WoWBot:
    def __init__(self):
        """Инициализация бота с расширенным логированием и валидацией"""
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("=== ИНИЦИАЛИЗАЦИЯ НОВОГО ЭКЗЕМПЛЯРА БОТА ===")
        self.logger = logging.getLogger(__name__)
        self.action_history: List[Dict] = []
        self.logger.info("Бот успешно инициализирован")
        self._init_components()
        self._start_time = datetime.now()
        self.logger.info(f"Бот инициализирован (Время запуска: {self._start_time})")

    def _setup_logging(self):
        """Расширенная настройка логирования с ротацией логов"""
        logging.basicConfig(
            level=logging.DEBUG,  # Изменили на DEBUG для более детального лога
            format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(f'bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler(),
                # Можно добавить RotatingFileHandler для ротации логов
            ]
        )
        # Настройка уровня логирования для библиотек
        logging.getLogger('pyautogui').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)

    def _init_components(self):
        """Инициализация всех компонентов системы с обработкой ошибок"""
        self.logger.info("Инициализация компонентов...")

        component_status = {
            'llm_provider': False,
            'planner': False,
            'mover': False,
            'env': False
        }

        try:
            # 1. Инициализация LLM провайдера
            self.logger.debug("Инициализация YandexGPTProvider...")
            self.llm_provider = YandexGPTProvider()
            component_status['llm_provider'] = True
            self.logger.debug("YandexGPTProvider успешно инициализирован")

            # 2. Инициализация планировщика действий
            self.logger.debug("Инициализация ActionPlanner...")
            from agents.action_planner import ActionPlanner
            self.planner = ActionPlanner(self.llm_provider)
            component_status['planner'] = True
            self.logger.debug("ActionPlanner успешно инициализирован")

            # 3. Инициализация контроллера движения
            self.logger.debug("Инициализация MovementController...")
            from base.movement_controller import MovementController
            self.mover = MovementController()
            component_status['mover'] = True
            self.logger.debug("MovementController успешно инициализирован")

            # 4. Инициализация окружения
            self.logger.debug("Инициализация WowEnvironment...")
            from environment.wow_environment import WowEnvironment
            self.env = WowEnvironment()
            component_status['env'] = True
            self.logger.debug("WowEnvironment успешно инициализирован")

            # Проверка работоспособности
            test_state = self.env.get_game_state()
            if test_state.get('status') != 'success':
                raise RuntimeError(f"Ошибка проверки состояния: {test_state.get('reason')}")

            self.logger.info(
                "Статус инициализации компонентов:\n" +
                "\n".join([f"- {comp}: {'OK' if status else 'FAILED'}"
                           for comp, status in component_status.items()])
            )

        except Exception as e:
            self.logger.critical(
                "Ошибка инициализации компонентов:\n" +
                "\n".join([f"- {comp}: {'OK' if status else 'FAILED'}"
                           for comp, status in component_status.items()]) +
                f"\nОшибка: {str(e)}",
                exc_info=True
            )
            raise

    def run(self):
        """Основной цикл работы с расширенным логированием"""
        self.logger.info("=== ЗАПУСК ОСНОВНОГО ЦИКЛА ===")
        self.logger.info(f"Конфигурация: {self._get_config_summary()}")

        loop_counter = 0
        error_count = 0
        last_success_time = datetime.now()

        try:
            while True:
                loop_counter += 1
                loop_start = datetime.now()
                self.logger.debug(f"Начало цикла #{loop_counter}")

                try:
                    self._game_loop()
                    last_success_time = datetime.now()
                    self.logger.debug(f"Цикл #{loop_counter} завершен успешно")
                except Exception as e:
                    error_count += 1
                    self.logger.warning(
                        f"Ошибка в цикле #{loop_counter} (Всего ошибок: {error_count}): {str(e)}",
                        exc_info=True
                    )
                    time.sleep(2)  # Задержка после ошибки

                loop_time = (datetime.now() - loop_start).total_seconds()
                self.logger.debug(f"Время выполнения цикла #{loop_counter}: {loop_time:.2f} сек")

                # Логирование статистики каждые 10 циклов
                if loop_counter % 10 == 0:
                    self._log_statistics(loop_counter, error_count, last_success_time)

                time.sleep(0.1)  # Базовая задержка между циклами

        except KeyboardInterrupt:
            self.logger.info("Остановка по запросу пользователя")
        except Exception as e:
            self.logger.critical(f"Критическая ошибка в основном цикле: {str(e)}", exc_info=True)
        finally:
            self._shutdown(loop_counter, error_count)

    def _game_loop(self):
        """Один цикл обработки игры с детальным логированием"""
        # 1. Сбор данных
        game_state = self._collect_game_data()
        if not game_state:
            self.logger.warning("Пропуск цикла из-за отсутствия данных состояния")
            time.sleep(1)
            return

        # 2. Планирование действия
        action = self._plan_action(game_state)
        if not action:
            self.logger.warning("Пропуск цикла из-за ошибки планирования")
            return

        # 3. Выполнение действия
        self._execute_action(action, game_state)

    def _collect_game_data(self) -> Dict:
        """Собирает данные о текущем состоянии игры с логированием"""
        try:
            collect_start = datetime.now()
            state = self.env.get_game_state()
            collect_time = (datetime.now() - collect_start).total_seconds()

            if state.get("status") != "success":
                self.logger.warning(
                    f"Не удалось получить состояние игры: {state.get('reason', 'неизвестная ошибка')} "
                    f"(Время запроса: {collect_time:.2f} сек)"
                )
                return None

            self.logger.debug(
                f"Получено состояние игры (Время запроса: {collect_time:.2f} сек):\n" +
                "\n".join([f"- {k}: {v}" for k, v in state.items() if k != 'frame'])
            )
            return state

        except Exception as e:
            self.logger.error(
                f"Ошибка сбора данных: {str(e)}",
                exc_info=True
            )
            return None

    def _plan_action(self, game_state: Dict) -> Dict:
        """Генерирует действие через LLM с детальным логированием"""
        try:
            plan_start = datetime.now()

            # Подготовка контекста для планирования
            context = {
                "game_state": game_state,
                "history": self.action_history[-5:] if self.action_history else [],
                "inventory": [],
                "abilities": []
            }

            self.logger.debug(f"Контекст для планирования:\n{context}")

            action = self.planner.plan_action(context)
            plan_time = (datetime.now() - plan_start).total_seconds()

            if action.get("status") != "success":
                self.logger.warning(
                    f"Ошибка планирования: {action.get('reason', 'неизвестная ошибка')} "
                    f"(Время планирования: {plan_time:.2f} сек)"
                )
                return None

            self.logger.info(
                f"Запланировано действие: {action['action']} "
                f"(Время планирования: {plan_time:.2f} сек)"
            )
            return action

        except Exception as e:
            self.logger.error(
                f"Ошибка планирования: {str(e)}",
                exc_info=True
            )
            return None

    def _execute_action(self, action: Dict, game_state: Dict):
        """Выполняет действие с полным логированием"""
        try:
            execute_start = datetime.now()

            # Логирование перед выполнением
            action_log = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "game_state": {k: v for k, v in game_state.items() if k != 'frame'}
            }
            self.action_history.append(action_log)

            self.logger.debug(f"Выполнение действия:\n{action_log}")

            # Выполнение действия
            self.mover.execute(action)

            execute_time = (datetime.now() - execute_start).total_seconds()
            self.logger.info(
                f"Действие выполнено успешно (Время выполнения: {execute_time:.2f} сек)"
            )

        except Exception as e:
            self.logger.error(
                f"Ошибка выполнения действия: {str(e)}\nДействие: {action}",
                exc_info=True
            )

    def _shutdown(self, loop_count: int, error_count: int):
        """Корректное завершение работы с полной статистикой"""
        shutdown_start = datetime.now()
        self.logger.info("Начало процедуры завершения работы...")

        try:
            self.env.cleanup()
            self.logger.debug("Окружение успешно очищено")
        except Exception as e:
            self.logger.error(f"Ошибка очистки окружения: {str(e)}", exc_info=True)

        try:
            # Можно добавить сохранение истории действий в файл
            pass
        except Exception as e:
            self.logger.error(f"Ошибка сохранения истории: {str(e)}", exc_info=True)

        uptime = (datetime.now() - self._start_time).total_seconds()
        success_rate = ((loop_count - error_count) / loop_count * 100) if loop_count > 0 else 0

        self.logger.info(
            "=== СТАТИСТИКА РАБОТЫ ===\n"
            f"- Всего циклов: {loop_count}\n"
            f"- Ошибок: {error_count}\n"
            f"- Успешных циклов: {loop_count - error_count}\n"
            f"- Процент успеха: {success_rate:.2f}%\n"
            f"- Общее время работы: {uptime:.2f} секунд"
        )

        shutdown_time = (datetime.now() - shutdown_start).total_seconds()
        self.logger.info(f"=== БОТ ОСТАНОВЛЕН (Время завершения: {shutdown_time:.2f} сек) ===")

    def _get_config_summary(self) -> Dict:
        """Возвращает основные параметры конфигурации"""
        # Здесь можно добавить сбор важных параметров конфигурации
        return {
            "log_level": logging.getLevelName(logging.getLogger().level),
            "components": ["WowEnvironment", "ActionPlanner", "MovementController"]
        }

    def _log_statistics(self, loop_count: int, error_count: int, last_success_time: datetime):
        """Логирование периодической статистики"""
        uptime = (datetime.now() - self._start_time).total_seconds()
        time_since_last_success = (datetime.now() - last_success_time).total_seconds()
        success_rate = ((loop_count - error_count) / loop_count * 100) if loop_count > 0 else 0

        self.logger.info(
            "=== ПРОМЕЖУТОЧНАЯ СТАТИСТИКА ===\n"
            f"- Всего циклов: {loop_count}\n"
            f"- Ошибок: {error_count}\n"
             "f - Время"
        "работы: {uptime: .2f}"
        "сек\n"
        f"- Время с последнего успеха: {time_since_last_success:.2f} сек\n"
        f"- Процент успеха: {success_rate:.2f}%"
        )


if __name__ == "__main__":
            bot = WoWBot()
            bot.run()