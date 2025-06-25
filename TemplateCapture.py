import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
import os


class TemplateCapture:
    def __init__(self):
        self.templates = {'npc': [], 'enemy': []}
        self.capture_size = 160
        self.window_name = "WoW Template Capture"

    def _clean_windows(self):
        """Закрывает все дополнительные окна"""
        try:
            cv2.destroyWindow("Capture Preview")
            cv2.destroyWindow("Last Template")
        except:
            pass

    def _show_image(self, img, title, timeout=300):
        """Безопасный показ изображения"""
        self._clean_windows()
        cv2.namedWindow(title, cv2.WINDOW_NORMAL)
        cv2.imshow(title, img)
        cv2.waitKey(timeout)
        cv2.destroyWindow(title)

    def _capture_template(self, x, y, obj_type):
        try:
            # Захват экрана
            frame = np.array(ImageGrab.grab())
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Выделяем область
            half = self.capture_size // 2
            roi = frame[y - half:y + half, x - half:x + half]

            if roi.size == 0:
                print("⚠️ Объект слишком близко к краю!")
                return

            # Сохраняем и показываем
            self.templates[obj_type].append(roi)
            print(f"✅ Захвачен {obj_type.upper()} (Всего: {len(self.templates[obj_type])})")

            # Показываем превью
            self._show_image(roi, "Capture Preview")

        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")

    def _save_templates(self):
        """Сохраняет все шаблоны в папку"""
        try:
            os.makedirs('base', exist_ok=True)

            for name, images in self.templates.items():
                if not images:
                    continue

                # Сохраняем все образцы
                for i, img in enumerate(images):
                    cv2.imwrite(f'base/{name}_{i}.png', img)

                # Создаем усредненный шаблон
                avg_template = np.mean(images, axis=0).astype(np.uint8)
                cv2.imwrite(f'base/{name}_template.png', avg_template)

            print("💾 Все шаблоны сохранены в папку 'base'")
            print(os.listdir('base'))

        except Exception as e:
            print(f"❌ Ошибка сохранения: {str(e)}")

    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        try:
            while True:
                # Основной фрейм
                frame = np.array(ImageGrab.grab())
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                # Отрисовка зоны захвата
                x, y = pyautogui.position()
                half = self.capture_size // 2
                cv2.rectangle(frame,
                              (x - half, y - half),
                              (x + half, y + half),
                              (0, 255, 0), 2)

                # Инфо-текст
                cv2.putText(frame, "n-NPC | e-Враг | s-Сохранить | q-Выход",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame,
                            f"Размер: {self.capture_size}px | Образцов: {sum(len(v) for v in self.templates.values())}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                cv2.imshow(self.window_name, frame)
                key = cv2.waitKey(50) & 0xFF

                if key == ord('q'):
                    break
                elif key == ord('n'):
                    self._capture_template(x, y, 'npc')
                elif key == ord('e'):
                    self._capture_template(x, y, 'enemy')
                elif key == ord('s'):
                    self._save_templates()

        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    print("=== Утилита захвата шаблонов ===")
    print("Убедитесь, что WoW запущен в оконном режиме!")
    capture = TemplateCapture()
    capture.run()