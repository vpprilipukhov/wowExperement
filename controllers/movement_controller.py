# controllers/movement_controller.py
import logging
from typing import Dict, Any
import pyautogui
import time

logger = logging.getLogger(__name__)


class MovementController:
    def __init__(self):
        """Инициализация контроллера движения"""
        logger.info("MovementController инициализирован")
        self.action_handlers = {
            "explore": self._handle_explore,
            "gather_resources": self._handle_gather,
            "move": self._handle_move,
            "attack": self._handle_attack
        }
        pyautogui.FAILSAFE = False
        logger.debug(f"Доступные обработчики: {list(self.action_handlers.keys())}")

    def execute(self, action_data: Dict[str, Any]):
        """
        Выполняет действие
        :param action_data: Данные действия в формате:
            {
                "action": "тип_действия",  # обязательное поле
                "target": {...},  # опционально
                "reason": "..."   # опционально
            }
            ИЛИ вложенная структура с полем 'action'
        """
        try:
            logger.debug(f"Получены данные действия: {action_data}")

            # Извлекаем само действие из возможной обертки
            if isinstance(action_data.get('action'), dict):
                action = action_data['action']
            else:
                action = action_data

            # Получаем тип действия как строку
            action_type = str(action.get('action')) if action.get('action') else None
            if not action_type:
                raise ValueError("Действие не содержит типа")

            logger.info(f"Начало выполнения действия: {action_type}")

            # Получаем обработчик
            handler = self.action_handlers.get(action_type)
            if not handler:
                raise ValueError(f"Нет обработчика для действия: {action_type}")

            # Выполняем действие
            handler(action)

        except Exception as e:
            logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
            raise

    def _handle_explore(self, action: Dict):
        """Обработка исследования территории"""
        logger.info("Исследование территории начато")

        # Движение по квадрату 100x100 пикселей
        movements = [(100, 0), (0, 100), (-100, 0), (0, -100)]
        for dx, dy in movements:
            self._move_relative(dx, dy)
            time.sleep(0.5)

        logger.info("Исследование территории завершено")

    def _handle_gather(self, action: Dict):
        """Обработка сбора ресурсов"""
        target = action.get('target', {})
        x, y = target.get('position', [0, 0])

        logger.info(f"Сбор ресурсов в позиции ({x}, {y})")
        self._move_to(x, y)
        pyautogui.press('f')  # Клавиша сбора
        time.sleep(1)

    def _handle_move(self, action: Dict):
        """Обработка движения к цели"""
        target = action.get('target', {})
        x, y = target.get('position', [0, 0])

        logger.info(f"Движение к позиции ({x}, {y})")
        self._move_to(x, y)

    def _handle_attack(self, action: Dict):
        """Обработка атаки"""
        logger.info("Атака цели")
        pyautogui.click(button='right')
        time.sleep(0.5)

    def _move_to(self, x: int, y: int):
        """Абсолютное перемещение"""
        pyautogui.moveTo(x, y, duration=0.5)
        logger.debug(f"Перемещение в ({x}, {y})")

    def _move_relative(self, dx: int, dy: int):
        """Относительное перемещение"""
        pyautogui.move(dx, dy, duration=0.3)
        logger.debug(f"Относительное перемещение на ({dx}, {dy})")

    def cleanup(self):
        """Очистка ресурсов"""
        logger.info("MovementController: очистка ресурсов")