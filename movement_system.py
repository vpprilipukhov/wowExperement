import pyautogui
import random
import time


class MovementSystem:
    def __init__(self):
        self.click_delay = 0.3

    def move_to_target(self, x, y):
        """Плавное движение к цели с человеческой случайностью"""
        # Добавляем небольшую случайность к координатам
        x += random.randint(-10, 10)
        y += random.randint(-10, 10)

        # Плавное движение мыши
        pyautogui.moveTo(
            x, y,
            duration=random.uniform(0.2, 0.5),
            tween=pyautogui.easeInOutQuad
        )

        # Имитация нажатия WASD
        self._press_movement_keys(x, y)

    def _press_movement_keys(self, x, y):
        """Имитация нажатия клавиш движения"""
        current_x, current_y = pyautogui.position()
        dx, dy = x - current_x, y - current_y

        # Определяем направление
        if abs(dx) > abs(dy):
            key = 'd' if dx > 0 else 'a'
        else:
            key = 'w' if dy < 0 else 's'

        # Нажимаем с человеческой вариативностью
        press_time = min(0.5, max(0.1, (abs(dx) + abs(dy)) / 1000))
        pyautogui.keyDown(key)
        time.sleep(press_time)
        pyautogui.keyUp(key)