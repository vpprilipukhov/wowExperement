from datetime import time

from WowMovement import WowMovement
from detector import EnemyDetector
from PIL import ImageGrab
import numpy as np
import cv2
import time


def main():
    detector = EnemyDetector()
    mover = WowMovement()

    print("Бот запущен. Для выхода нажмите Ctrl+C")

    try:
        while True:
            # 1. Захват экрана
            screen = np.array(ImageGrab.grab())
            frame = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)

            # 2. Поиск врагов
            enemies = detector.find_enemies(frame)

            if not enemies:
                print("Врагов не найдено")
                time.sleep(1)
                continue

            # 3. Движение к первому врагу
            target = enemies[0]
            print(f"Найден враг на позиции: {target}")
            mover.move_to(*target)

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nБот остановлен")


if __name__ == "__main__":
    main()