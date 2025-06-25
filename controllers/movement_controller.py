# base/movement_controller.py - Контроллер движения персонажа
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class MovementController:
    def __init__(self):
        """Инициализация контроллера движения"""
        logger.info("MovementController инициализирован")

    def execute(self, action: Dict):
        """
        Выполняет действие движения
        :param action: Словарь с описанием действия
        """
        try:
            logger.debug(f"Выполнение действия: {action}")
            # Здесь будет реальная реализация движения
            # Пока просто логируем действие
            if action.get('action') == 'move':
                logger.info(f"Персонаж двигается к {action.get('target', {}).get('position')}")
            elif action.get('action') == 'turn':
                logger.info(f"Персонаж поворачивается на {action.get('degrees', 0)} градусов")
            else:
                logger.warning(f"Неизвестное действие: {action.get('action')}")

        except Exception as e:
            logger.error(f"Ошибка выполнения движения: {str(e)}", exc_info=True)
            raise