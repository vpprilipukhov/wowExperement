import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
import os
import logging

class WowEnvironment:
    def __init__(self):
        self.region = (0, 0, 1920, 1080)  # Фиксированный размер
        self.logger = logging.getLogger(self.__class__.__name__)
        self.templates = {
            'npc': [self._create_template('npc')],
            'enemy': [self._create_template('enemy')]
        }
        self.logger.info("Инициализирован с дефолтными шаблонами")

    def _create_template(self, obj_type):
        """Создает простые шаблоны без загрузки файлов"""
        size = 50
        template = np.zeros((size, size, 3), dtype=np.uint8)
        if obj_type == 'npc':
            cv2.circle(template, (size//2, size//2), size//3, (0, 255, 255), -1)
        else:  # enemy
            cv2.rectangle(template, (size//4, size//4), (3*size//4, 3*size//4), (0, 0, 255), -1)
        return template

    def get_game_state(self):
        """Гарантированно возвращает dict с frame"""
        try:
            frame = self._capture_frame()
            return {
                'frame': frame,
                'npcs': self._find_objects(frame, 'npc'),
                'enemies': self._find_objects(frame, 'enemy'),
                'status': 'success'
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения состояния: {str(e)}")
            return {
                'frame': np.zeros((1080, 1920, 3), dtype=np.uint8),
                'status': 'error',
                'error': str(e)
            }

    def _capture_frame(self):
        """Захватывает кадр с обработкой ошибок"""
        screen = ImageGrab.grab(bbox=self.region)
        return cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

    def _find_objects(self, frame, obj_type):
        """Упрощенный поиск объектов"""
        try:
            results = []
            for template in self.templates.get(obj_type, []):
                res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= 0.7)
                results.extend(zip(*loc[::-1]))
            return results
        except Exception as e:
            self.logger.error(f"Ошибка поиска {obj_type}: {str(e)}")
            return []