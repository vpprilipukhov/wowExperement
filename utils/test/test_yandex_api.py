import requests
import yaml
from pathlib import Path
import os
from dotenv import load_dotenv


def load_config():
    """Загружает конфигурацию из config.yaml"""
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки config.yaml: {str(e)}")
        return None


def test_yandex_api_rest(api_key: str, folder_id: str):
    """
    Тестирует подключение к YandexGPT через REST API

    :param api_key: 58-символьный API ключ сервисного аккаунта
    :param folder_id: ID каталога в Yandex Cloud
    :return: True если подключение успешно, False в противном случае
    """
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
        "messages": [
            {
                "role": "user",
                "text": "Привет! Это тестовое сообщение."
            }
        ],
        "completionOptions": {
            "stream": False,
            "temperature": 0.1,
            "maxTokens": "100"
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        print("✅ Успешное подключение! Ответ сервера:")
        print(response.json())
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка REST запроса: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print("Детали ошибки:", e.response.text)
        return False


if __name__ == "__main__":
    # Пробуем загрузить из .env (для обратной совместимости)
    load_dotenv()

    # Загружаем конфиг из config.yaml
    config = load_config()
    if not config:
        exit(1)

    # Получаем параметры (приоритет у config.yaml)
    api_key = config.get('yandex_cloud', {}).get('api_key') or os.getenv('YANDEX_API_KEY')
    folder_id = config.get('yandex_cloud', {}).get('folder_id') or os.getenv('YANDEX_FOLDER_ID')

    if not api_key or not folder_id:
        print("Необходимо указать в config.yaml или .env файле:")
        print("yandex_cloud:")
        print("  api_key: ваш_58_символьный_ключ")
        print("  folder_id: ваш_id_каталога")
        exit(1)

    print(f"Используем API ключ длиной {len(api_key)} символов и folder_id: {folder_id}")

    if test_yandex_api_rest(api_key, folder_id):
        print("✅ Тест пройден успешно!")
    else:
        print("❌ Тест не пройден")