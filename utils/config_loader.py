import yaml
import os


class ConfigLoader:
    """Загрузчик конфигурации с поддержкой переменных окружения"""

    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        """Загружает конфиг из YAML-файла"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:  # Добавлено encoding='utf-8'
            config = yaml.safe_load(f)

        # Подставляем значения из переменных окружения
        if 'api_key' in config['llm']:
            config['llm']['api_key'] = os.getenv('LLM_API_KEY', config['llm']['api_key'])

        return config

    def get(self, key, default=None):
        """Получает значение из конфига по пути вида 'llm.model'"""
        keys = key.split('.')
        value = self.config

        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default