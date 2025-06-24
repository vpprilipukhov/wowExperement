import cv2
import numpy as np
from ultralytics import YOLO
from utils.config_loader import ConfigLoader


class VisionModule:
    def __init__(self):
        self.config = ConfigLoader()
        self.ui_model = None
        self.load_model()
        self.last_detection = {}

    def load_model(self):
        model_path = self.config.get('vision.ui_model')
        if not model_path:
            raise ValueError("UI model path not configured")
        self.ui_model = YOLO(model_path)
        self.ui_model.conf = self.config.get('vision.confidence_threshold', 0.7)

    def analyze_frame(self, frame):
        if frame is None:
            return self.last_detection

        # Для теста: сохраняем первый кадр
        if not hasattr(self, 'first_frame_saved'):
            cv2.imwrite("test_frame.jpg", frame)
            self.first_frame_saved = True

        # Заглушка для теста
        state = {
            'health': 100,
            'mana': 100,
            'target': "Test Target",
            'ui_elements': [
                {'class': 'health_bar', 'coords': [100, 100, 200, 50], 'confidence': 0.9}
            ]
        }
        self.last_detection = state
        return state


if __name__ == "__main__":
    # Тест модуля зрения
    vision = VisionModule()
    test_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    state = vision.analyze_frame(test_frame)
    print(f"Test state: {state}")