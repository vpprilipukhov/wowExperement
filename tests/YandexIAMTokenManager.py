import yaml
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
import base64

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("YandexIAMTokenManager")


class YandexIAMTokenManager:
    def __init__(self):
        """
        Инициализация менеджера токенов с загрузкой конфигурации
        из config.yaml в корне проекта
        """
        self.oauth_token = None
        self.iam_token = None
        self.expires_at = None
        self.folder_id = None
        self._load_config()

    def _load_config(self):
        """Загружает конфигурацию из config.yaml в корне проекта"""
        try:
            # Определяем корень проекта
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'config.yaml'

            logger.info(f"Загрузка конфигурации из: {config_path}")

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Получаем токен из конфига
            yandex_config = config.get('yandex_cloud', {})
            self.oauth_token = yandex_config.get('oauth_token')
            self.folder_id = yandex_config.get('folder_id')

            # Если не нашли по ключу 'oauth_token', попробуем 'api_key'
            if not self.oauth_token:
                self.oauth_token = yandex_config.get('api_key')

            if not self.oauth_token:
                raise ValueError("OAuth токен не найден в конфиге. Используйте ключ 'oauth_token' или 'api_key'")

            if not self.folder_id:
                raise ValueError("Folder ID не найден в конфиге")

            logger.info(f"OAuth токен загружен (первые 10 символов): {self.oauth_token[:10]}...")
            logger.info(f"Folder ID: {self.folder_id}")

        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {str(e)}")
            raise

    def get_iam_token(self) -> str:
        """
        Получает действительный IAM-токен
        - Использует существующий токен, если он еще действителен
        - Запрашивает новый при необходимости
        """
        # Проверка действительности существующего токена
        if self.iam_token and self.expires_at and datetime.utcnow() < self.expires_at:
            logger.debug("Используется существующий IAM-токен")
            return self.iam_token

        logger.info("Запрос нового IAM-токена...")
        url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
        payload = {"yandexPassportOauthToken": self.oauth_token}

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self.iam_token = token_data["iamToken"]

            # Определяем срок действия
            if "expiresAt" in token_data:
                # Преобразуем строку времени в объект datetime
                expires_at_str = token_data["expiresAt"]
                self.expires_at = datetime.fromisoformat(expires_at_str.rstrip('Z'))
            else:
                # Стандартное значение: 12 часов
                self.expires_at = datetime.utcnow() + timedelta(hours=11, minutes=55)

            logger.info(f"IAM-токен успешно получен, действителен до: {self.expires_at}")
            return self.iam_token

        except requests.exceptions.HTTPError as e:
            logger.error(f"Ошибка HTTP {e.response.status_code}: {e.response.text}")
            if e.response.status_code == 401:
                logger.error("❌ Недействительный OAuth-токен")
            raise
        except Exception as e:
            logger.exception("Непредвиденная ошибка при получении токена")
            raise

    def test_connection(self) -> bool:
        """Проверяет работоспособность токена с помощью тестового запроса к Vision API"""
        try:
            token = self.get_iam_token()
            if not token:
                logger.error("Не удалось получить IAM-токен")
                return False

            logger.info("Проверка токена через Vision API...")

            # URL для Vision API
            vision_url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Создаем минимальное PNG изображение (1x1 пиксель, прозрачное)
            test_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f\x04\x00\x09\xfb\x03\xfd\x00\x00\x00\x00IEND\xaeB`\x82"
            content = base64.b64encode(test_image).decode('utf-8')

            # Формируем тело запроса
            request_body = {
                "folderId": self.folder_id,
                "analyzeSpecs": [{
                    "content": content,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "textDetectionConfig": {"languageCodes": ["*"]}
                    }],
                    "mimeType": "image/png"
                }]
            }

            # Отправляем запрос
            response = requests.post(vision_url, headers=headers, json=request_body, timeout=10)

            # Анализируем ответ
            if response.status_code == 200:
                logger.info("✅ Токен успешно прошел проверку! Vision API доступен.")
                return True
            elif response.status_code == 400:
                # Bad Request - возможно из-за пустого изображения, но токен то работает!
                logger.info("✅ Токен работает! Vision API ответил ошибкой 400 (ожидаемо для тестового изображения)")
                return True
            else:
                logger.error(f"❌ Ошибка проверки токена. Код: {response.status_code}")
                logger.error(f"Ответ сервера: {response.text[:500]}")
                return False

        except Exception as e:
            logger.error(f"❌ Тест подключения провален: {str(e)}")
            return False


def main():
    """Точка входа для тестирования токена"""
    print("=== Тестирование Yandex IAM Token Manager ===")

    try:
        manager = YandexIAMTokenManager()

        # Проверяем подключение
        success = manager.test_connection()

        if success:
            print("\n✅ Тест пройден успешно! Токен работает корректно.")
            print(f"IAM-токен: {manager.iam_token[:15]}...")
        else:
            print("\n❌ Тест не пройден. Проверьте конфигурацию.")

    except Exception as e:
        print(f"\n🔥 Критическая ошибка: {str(e)}")
        print("Проверьте наличие и содержание config.yaml в корне проекта")


if __name__ == "__main__":
    main()