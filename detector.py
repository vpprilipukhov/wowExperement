import cv2
import numpy as np


class EnemyDetector:
    def __init__(self):
        # Создаем простой шаблон врага (красный квадрат)
        self.template = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.rectangle(self.template, (10, 10), (40, 40), (0, 0, 255), -1)

    def find_enemies(self, frame):
        """Возвращает список координат врагов"""
        result = cv2.matchTemplate(frame, self.template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= 0.7)
        return list(zip(*locations[::-1]))