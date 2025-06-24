import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
import os
import logging
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class WowEnvironment:
    def __init__(self):
        self.region = self._get_game_window_region()
        self.templates = self._load_templates()
        logger.info(f"Инициализирован WowEnvironment с регионом: {self.region}")

    def _get_game_window_region(self) -> Tuple[int, int, int, int]:
        """Автоматически определяет окно игры или использует fallback"""
        try:
            wow_window = pyautogui.getWindowsWithTitle("World of Warcraft")[0]
            if wow_window.width < 100 or wow_window.height < 100:
                raise ValueError("Слишком маленькое окно игры")
            return (wow_window.left, wow_window.top, wow_window.right, wow_window.bottom)
        except Exception as e:
            logger.warning(f"Не удалось определить окно игры: {str(e)}, использую fallback 1920x1080")
            return (0, 0, 1920, 1080)

    def _load_templates(self) -> Dict[str, List[np.ndarray]]:
        """Загружает шаблоны для поиска объектов"""
        # Простые шаблоны по умолчанию
        enemy_template = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.rectangle(enemy_template, (10, 10), (40, 40), (0, 0, 255), -1)

        return {
            'enemy': [enemy_template],
            'npc': []
        }

    def get_game_state(self) -> Dict:
        """Основной метод получения состояния игры"""
        try:
            frame = self._capture_frame()
            if frame is None:
                return {"status": "error", "reason": "Не удалось захватить кадр"}

            return {
                "status": "success",
                "frame": frame,
                "enemies": self._find_objects(frame, 'enemy'),
                "npcs": [],
                "position": self._get_player_position(frame)
            }
        except Exception as e:
            logger.error(f"Ошибка получения состояния: {str(e)}", exc_info=True)
            return {"status": "error", "reason": str(e)}

    def _capture_frame(self) -> Optional[np.ndarray]:
        """Захватывает кадр игры"""
        try:
            screen = ImageGrab.grab(bbox=self.region)
            frame = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

            # Простая проверка что игра видна
            if np.mean(frame) < 10:  # Черный экран
                logger.warning("Возможно игра не видна (черный экран)")
                return None

            return frame
        except Exception as e:
            logger.error(f"Ошибка захвата кадра: {str(e)}")
            return None

    def _find_objects(self, frame: np.ndarray, obj_type: str) -> List[Tuple[int, int]]:
        """Находит объекты на кадре"""
        objects = []
        for template in self.templates.get(obj_type, []):
            res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= 0.7)
            objects.extend(zip(*loc[::-1]))
        return objects

    def _get_player_position(self, frame: np.ndarray) -> Tuple[int, int]:
        """Определяет позицию игрока (упрощенно - центр экрана)"""
        return (
            self.region[0] + (self.region[2] - self.region[0]) // 2,
            self.region[1] + (self.region[3] - self.region[1]) // 2
        )

    def cleanup(self):
        """Метод для очистки ресурсов"""
        logger.info("Очистка ресурсов WowEnvironment")
        # Можно добавить закрытие файлов/соединений при необходимости