import pyautogui
import time
import random
import numpy as np


class ActionExecutor:
    """Выполняет действия в игре с человекообразным поведением"""

    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.mouse_speed = 0.3

    def execute_code(self, code):
        """Выполняет сгенерированный код"""
        try:
            # Создаем безопасный контекст выполнения
            context = {
                'move_to': self.move_to,
                'click': self.click,
                'cast_spell': self.cast_spell,
                'loot': self.loot
            }

            exec(code, context)
            return True
        except Exception as e:
            print(f"Ошибка выполнения кода: {e}")
            return False

    def move_to(self, x, y):
        """Плавное движение к координатам (0-1)"""
        abs_x = int(x * self.screen_width) + random.randint(-5, 5)
        abs_y = int(y * self.screen_height) + random.randint(-5, 5)
        self._human_like_move(abs_x, abs_y)

    def _human_like_move(self, target_x, target_y):
        """Движение по кривой Безье"""
        start_x, start_y = pyautogui.position()
        cp_x = start_x + (target_x - start_x) * random.uniform(0.3, 0.7)
        cp_y = start_y + (target_y - start_y) * random.uniform(0.3, 0.7)
        steps = max(10, int(np.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2) / 10))

        for t in np.linspace(0, 1, steps):
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * cp_x + t ** 2 * target_x
        y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * cp_y + t ** 2 * target_y
        pyautogui.moveTo(x, y)
        time.sleep(self.mouse_speed / steps)

    def click(self, element_type="left"):
        """Естественный клик мышью"""
        time.sleep(random.uniform(0.1, 0.3))
        pyautogui.mouseDown(button=element_type)
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.mouseUp(button=element_type)
        time.sleep(random.uniform(0.1, 0.4))

    def cast_spell(self, spell_name):
        """Применение заклинания (заглушка)"""
        print(f"Применение заклинания: {spell_name}")
        time.sleep(1.0)

    def loot(self):
        """Подбор предметов"""
        print("Подбор предметов...")
        time.sleep(0.5)