import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
import os
import logging


class WowEnvironmentTEEEEST:
    def __init__(self, region=None):
        self.region = region or (0, 0, 1920, 1080)
        self.logger = logging.getLogger(__name__)
        self.templates = self._load_templates()

    def _load_templates(self):
        """Загрузка шаблонов с проверкой пути"""
        template_dir = os.path.join(os.path.dirname(__file__), 'envs', 'base')
        self.logger.info(f"Ищу шаблоны в: {template_dir}")

        if not os.path.exists(template_dir):
            self.logger.warning(f"Папка не найдена: {template_dir}")
            os.makedirs(template_dir, exist_ok=True)

        templates = {'npc': [], 'enemy': []}

        # Проверяем существование файлов
        for name in templates.keys():
            template_path = os.path.join(template_dir, f'{name}_0.png')
            if os.path.exists(template_path):
                img = cv2.imread(template_path, cv2.IMREAD_COLOR)
                if img is not None:
                    templates[name].append(img)
                    self.logger.info(f"Загружен шаблон: {template_path}")

            # Создаем дефолтные если не найдены
            if not templates[name]:
                templates[name].append(self._create_default_template(name))
                self.logger.warning(f"Создан дефолтный шаблон для {name}")

        return templates

    def capture_screen(self):
        """Захват экрана с обработкой ошибок"""
        try:
            screen = ImageGrab.grab(bbox=self.region)
            return cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.logger.error(f"Ошибка захвата: {str(e)}")
            return np.zeros((1080, 1920, 3), dtype=np.uint8)  # Черный экран при ошибке

    def get_game_state(self):
        """Возвращает состояние игры и кадр"""
        frame = self.capture_screen()
        state = {
            'npcs': self._find_objects(frame, 'npc'),
            'enemies': self._find_objects(frame, 'enemy'),
            'frame': frame  # Добавляем кадр в возвращаемый словарь
        }
        self.logger.debug(f"Обнаружено NPC: {len(state['npcs'])}, Врагов: {len(state['enemies'])}")
        return state

    def _find_objects(self, frame, obj_type, threshold=0.7):
        """Поиск объектов на кадре"""
        results = []
        for template in self.templates.get(obj_type, []):
            try:
                res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= threshold)
                results.extend(zip(*loc[::-1]))
            except Exception as e:
                self.logger.error(f"Ошибка поиска {obj_type}: {str(e)}")
        return results

    def _create_default_template(self, name):
        """Создает простые тестовые шаблоны"""
        size = 50
        template = np.zeros((size, size, 3), dtype=np.uint8)

        if name == 'npc':
            cv2.circle(template, (size // 2, size // 2), size // 3, (0, 255, 255), -1)
        elif name == 'enemy':
            cv2.rectangle(template, (size // 4, size // 4), (3 * size // 4, 3 * size // 4), (0, 0, 255), -1)

        return template