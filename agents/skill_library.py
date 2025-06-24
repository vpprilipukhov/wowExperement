import json
import os


class SkillLibrary:
    """Библиотека для хранения и поиска навыков агента"""

    def __init__(self, file_path):
        self.file_path = file_path
        self.skills = self._load_skills()

    def _load_skills(self):
        """Загружает навыки из файла"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return json.load(f)
        return {}

    def save_skills(self):
        """Сохраняет навыки в файл"""
        with open(self.file_path, 'w') as f:
            json.dump(self.skills, f, indent=2)

    def add_skill(self, task_description, code):
        """Добавляет новый навык в библиотеку"""
        self.skills[task_description] = code
        self.save_skills()

    def find_skill(self, task_description):
        """Ищет подходящий навык для задачи"""
        # Простой поиск по ключевым словам
        for skill_desc, code in self.skills.items():
            if all(keyword in task_description for keyword in skill_desc.split()[:3]):
                return code
        return None