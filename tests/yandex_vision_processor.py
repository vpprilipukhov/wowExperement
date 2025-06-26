import os
import json
import logging
import time
import cv2
import numpy as np
import requests
import base64
from typing import Dict, Optional, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vision_processor.log'),
        logging.StreamHandler()
    ]
)


class YandexVisionProcessor:
    def __init__(self, api_key: str, folder_id: str, results_dir: str = "analysis_results"):
        self.api_url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
        self.api_key = api_key
        self.folder_id = folder_id
        self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.last_analysis = {}

    def _image_to_base64(self, image: np.ndarray) -> str:
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')

    def _call_vision_api(self, image: np.ndarray) -> Optional[Dict]:
        try:
            base64_image = self._image_to_base64(image)

            body = {
                "folderId": self.folder_id,
                "analyze_specs": [{
                    "content": base64_image,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "text_detection_config": {
                            "language_codes": ["*"],
                            "model": "page"
                        }
                    }],
                    "mimeType": "image/jpeg"
                }]
            }

            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=body,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Ошибка Vision API: {str(e)}")
            return None

    def analyze_active_window(self, image: np.ndarray, metadata: Dict) -> Dict:
        """Анализирует только активное окно"""
        try:
            if not image.size:
                return {}

            api_response = self._call_vision_api(image)
            if not api_response:
                return {}

            text_blocks = api_response['results'][0]['textDetection']['pages'][0]['blocks']
            full_text = "\n".join(" ".join(line['text'] for line in block['lines']) for block in text_blocks)

            def extract_value(pattern):
                import re
                match = re.search(pattern, full_text, re.IGNORECASE)
                return int(match.group(1)) if match else None

            result = {
                'hp': extract_value(r'HP[:]?\s*(\d+)%'),
                'resource': {
                    'type': 'mana' if extract_value(r'(?:Мана|Mana)[:]?\s*(\d+)%') else 'energy',
                    'value': extract_value(r'(?:Мана|Mana|Энергия|Energy)[:]?\s*(\d+)%')
                },
                'status_effects': [
                    eff for eff in ['haste', 'food']
                    if eff in full_text.lower()
                ],
                'metadata': metadata,
                'timestamp': time.time()
            }

            filename = f"{self.results_dir}/result_{metadata['timestamp']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.last_analysis = result
            logging.info(f"Анализ сохранён: {filename}")
            return result

        except Exception as e:
            logging.error(f"Ошибка анализа: {str(e)}", exc_info=True)
            return {}

    def run_standalone_test(self, test_image_path: str):
        print(f"Анализ тестового скриншота: {test_image_path}")
        image = cv2.imread(test_image_path)
        if image is None:
            print("Ошибка загрузки изображения")
            return

        metadata = {
            'filename': test_image_path,
            'timestamp': int(time.time())
        }

        result = self.analyze_active_window(image, metadata)
        print("\nРезультаты:")
        print(f"HP: {result.get('hp', 'N/A')}%")
        print(f"{result.get('resource', {}).get('type', 'Resource')}: "
              f"{result.get('resource', {}).get('value', 'N/A')}%")
        print(f"Эффекты: {', '.join(result.get('status_effects', [])) or 'Нет'}")


if __name__ == "__main__":
    processor = YandexVisionProcessor(
        api_key="your_api_key",
        folder_id="your_folder_id"
    )
    processor.run_standalone_test("test_screenshot.jpg")