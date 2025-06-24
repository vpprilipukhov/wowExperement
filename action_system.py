from typing import Dict

import pyautogui
import time
import random


class ActionSystem:
    def __init__(self, env):
        self.env = env

    def execute(self, action: Dict):
        """Выполняет одно действие"""
        try:
            if action['type'] == 'move_to':
                return self._move_to(action['target'])
            elif action['type'] == 'attack':
                return self._attack(action['target'])
            # ... другие типы действий ...
        except Exception as e:
            print(f"Ошибка выполнения {action}: {e}")

    def _move_to(self, target):
        """Движение к цели с человеческой случайностью"""
        x, y = target
        x += random.randint(-5, 5)
        y += random.randint(-5, 5)

        pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.3))
        pyautogui.click()

    def _attack(self, target):
        x, y = target
        pyautogui.rightClick(x, y)
        time.sleep(random.uniform(0.2, 0.5))