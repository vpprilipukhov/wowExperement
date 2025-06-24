import pyautogui
import random
import time


class WowMovement:
    def __init__(self):
        self.click_delay = 0.3

    def move_to(self, x, y):
        """Плавное движение к цели"""
        # Добавляем случайность для "человечности"
        x += random.randint(-5, 5)
        y += random.randint(-5, 5)

        pyautogui.moveTo(x, y, duration=random.uniform(0.2, 0.5))
        pyautogui.click(duration=random.uniform(0.1, 0.3))
        time.sleep(self.click_delay)