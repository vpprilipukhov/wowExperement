import pyautogui
import random
import time
import logging
import math
from typing import Dict, Tuple, Optional, List  # Добавлен импорт List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MovementConfig:
    min_delay: float = 0.1
    max_delay: float = 0.3
    human_like: bool = True
    precision: int = 5  # pixels randomness
    pathfinding_step: int = 50  # pixels per move


class MovementController:
    """Контроллер движения с поддержкой human-like поведения и pathfinding"""

    def __init__(self, config: Optional[MovementConfig] = None):
        self.config = config or MovementConfig()
        self._setup_pyautogui()
        logger.info("MovementController инициализирован")

    def _setup_pyautogui(self):
        """Настройка параметров pyautogui"""
        pyautogui.MINIMUM_DURATION = self.config.min_delay
        pyautogui.PAUSE = random.uniform(0.05, 0.2)

        if self.config.human_like:
            pyautogui.easeInOutQuad  # Используем плавные кривые движения

    def execute(self, action: Dict):
        """Выполняет действие на основе команды"""
        try:
            action_type = action.get('action')
            target = action.get('target', {})

            if action_type == 'move':
                self.move_to(target['position'])
            elif action_type == 'attack':
                self.attack(target['position'], target.get('type'))
            elif action_type == 'interact':
                self.interact(target['position'])
            else:
                logger.warning(f"Неизвестный тип действия: {action_type}")

        except Exception as e:
            logger.error(f"Ошибка выполнения движения: {str(e)}")

    def move_to(self, position: Tuple[int, int]):
        """Плавное движение к указанной позиции"""
        try:
            x, y = self._apply_randomness(position)
            current_pos = pyautogui.position()

            if self._should_use_pathfinding(current_pos, (x, y)):
                self._move_with_pathfinding(current_pos, (x, y))
            else:
                self._direct_move(current_pos, (x, y))

            self._human_delay()

        except Exception as e:
            logger.error(f"Ошибка движения: {str(e)}")
            raise

    def attack(self, position: Tuple[int, int], enemy_type: Optional[str] = None):
        """Атака цели с human-like поведением"""
        try:
            x, y = self._apply_randomness(position)

            # Подход к цели
            self.move_to((x + random.randint(-30, 30), y + random.randint(-30, 30)))

            # Имитация выбора цели
            pyautogui.rightClick(x, y, duration=random.uniform(0.1, 0.3))
            time.sleep(random.uniform(0.2, 0.5))

            # Использование способностей
            self._use_combat_abilities(enemy_type)

            self._human_delay()

        except Exception as e:
            logger.error(f"Ошибка атаки: {str(e)}")
            raise

    def interact(self, position: Tuple[int, int]):
        """Взаимодействие с NPC/объектом"""
        try:
            x, y = self._apply_randomness(position)
            self.move_to((x, y))

            # Имитация взаимодействия
            pyautogui.click(button='right', duration=random.uniform(0.1, 0.3))
            time.sleep(random.uniform(0.5, 1.5))  # Ожидание диалога

        except Exception as e:
            logger.error(f"Ошибка взаимодействия: {str(e)}")
            raise

    def _apply_randomness(self, position: Tuple[int, int]) -> Tuple[int, int]:
        """Добавляет случайность к координатам"""
        if not self.config.human_like:
            return position

        x, y = position
        return (
            x + random.randint(-self.config.precision, self.config.precision),
            y + random.randint(-self.config.precision, self.config.precision)
        )

    def _should_use_pathfinding(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Определяет нужно ли использовать pathfinding"""
        distance = math.dist(start, end)
        return distance > 100  # Используем pathfinding для дистанций > 100px

    def _move_with_pathfinding(self, start: Tuple[int, int], end: Tuple[int, int]):
        """Имитация pathfinding с промежуточными точками"""
        steps = self._calculate_path(start, end)
        for point in steps:
            self._direct_move(pyautogui.position(), point)
            time.sleep(random.uniform(0.1, 0.3))

    def _direct_move(self, start: Tuple[int, int], end: Tuple[int, int]):
        """Прямое движение между точками"""
        if self.config.human_like:
            duration = random.uniform(self.config.min_delay, self.config.max_delay)
            pyautogui.moveTo(end[0], end[1], duration=duration, tween=pyautogui.easeInOutQuad)
        else:
            pyautogui.moveTo(end[0], end[1])

    def _calculate_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Генерирует промежуточные точки пути"""
        steps = []
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.dist(start, end)
        steps_count = int(distance / self.config.pathfinding_step)

        if steps_count > 1:
            for i in range(1, steps_count):
                steps.append((
                    int(start[0] + dx * i / steps_count),
                    int(start[1] + dy * i / steps_count)
                ))

        steps.append(end)
        return steps

    def _use_combat_abilities(self, enemy_type: Optional[str] = None):
        """Имитация использования способностей"""
        abilities = {
            'melee': ['1', '2', '3'],
            'ranged': ['4', '5'],
            'spell': ['q', 'e']
        }

        # Выбор способностей в зависимости от типа врага
        if enemy_type in ['dragon', 'boss']:
            keys = abilities['spell'] + abilities['ranged']
        else:
            keys = abilities['melee']

        # Human-like последовательность нажатий
        for key in random.sample(keys, min(3, len(keys))):
            pyautogui.press(key)
            time.sleep(random.uniform(0.2, 0.4))

    def _human_delay(self):
        """Случайная задержка между действиями"""
        if self.config.human_like:
            time.sleep(random.uniform(0.1, 0.7))