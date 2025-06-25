# controllers/movement_controller.py - Контроллер движения с полной обработкой действий
import logging
from typing import Dict, Any
import pyautogui
import time

logger = logging.getLogger(__name__)


class MovementController:
    def __init__(self):
        """Инициализация контроллера движения с безопасными настройками"""
        logger.info("Инициализация MovementController")
        self.action_handlers = {
            "explore": self._handle_explore,
            "gather_resources": self._handle_gather,
            "move": self._handle_move,
            "attack": self._handle_attack
        }
        pyautogui.FAILSAFE = False
        self.move_duration = 0.7
        self.action_delay = 1.0
        logger.info(f"Доступные обработчики действий: {list(self.action_handlers.keys())}")

    def execute(self, action_data: Dict[str, Any]):
        """
        Основной метод выполнения действия
        :param action_data: Данные действия в формате:
            {
                "action": "тип_действия",
                "target": {"type": "...", "position": [x,y]},
                "reason": "..."
            }
            или вложенная структура с полем 'action'
        """
        try:
            logger.debug(f"Получено действие для выполнения: {action_data}")

            # Извлекаем основное действие из возможной обертки
            if 'action' in action_data and isinstance(action_data['action'], dict):
                action = action_data['action']
            else:
                action = action_data

            # Проверяем структуру действия
            if not isinstance(action, dict):
                raise ValueError("Действие должно быть словарем")

            action_type = action.get('action')
            if not action_type:
                raise ValueError("Действие не содержит типа")

            logger.info(f"Выполнение действия типа: {action_type}")

            # Получаем обработчик
            handler = self.action_handlers.get(str(action_type))
            if not handler:
                raise ValueError(f"Неизвестный тип действия: {action_type}")

            # Выполняем действие
            handler(action)
            time.sleep(self.action_delay)

        except Exception as e:
            logger.error(f"Ошибка выполнения действия: {str(e)}", exc_info=True)
            raise

    def _handle_explore(self, action: Dict[str, Any]):
        """Обработка исследования территории"""
        logger.info("Начало исследования территории")

        # Простейший паттерн движения по квадрату
        movements = [
            (100, 0),  # Вправо
            (0, 100),  # Вниз
            (-100, 0),  # Влево
            (0, -100)  # Вверх
        ]

        for dx, dy in movements:
            self._safe_move((dx, dy), relative=True)
            time.sleep(0.5)

        logger.info("Исследование территории завершено")

    def _handle_gather(self, action: Dict[str, Any]):
        """Обработка сбора ресурсов"""
        target = action.get('target', {})
        position = target.get('position', [0, 0])

        logger.info(f"Сбор ресурсов в позиции {position}")

        # Движение к цели
        self._safe_move(position)

        # Имитация сбора
        pyautogui.press('f')
        time.sleep(1.5)

        logger.info("Сбор ресурсов завершен")

    def _handle_move(self, action: Dict[str, Any]):
        """Обработка движения к цели"""
        target = action.get('target', {})
        position = target.get('position', [0, 0])

        logger.info(f"Движение к позиции {position}")
        self._safe_move(position)

    def _handle_attack(self, action: Dict[str, Any]):
        """Обработка атаки цели"""
        target = action.get('target', {})
        logger.info(f"Атака цели: {target.get('type', 'unknown')}")

        # Имитация атаки
        pyautogui.click(button='right')
        time.sleep(1.0)

    def _safe_move(self, position, relative=False):
        """
        Безопасное перемещение с обработкой ошибок
        :param position: Кортеж/список (x, y)
        :param relative: Относительное перемещение
        """
        try:
            if not isinstance(position, (tuple, list)) or len(position) != 2:
                raise ValueError("Некорректный формат позиции")

            x, y = map(int, position)  # Преобразуем в целые числа

            if relative:
                pyautogui.move(x, y, duration=self.move_duration)
                logger.debug(f"Относительное перемещение: ({x}, {y})")
            else:
                pyautogui.moveTo(x, y, duration=self.move_duration)
                logger.debug(f"Абсолютное перемещение: ({x}, {y})")

        except Exception as e:
            logger.error(f"Ошибка перемещения: {str(e)}")
            raise

    def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Очистка MovementController")