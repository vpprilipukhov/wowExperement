import dxcam
import time
import numpy as np
import cv2
from utils.config_loader import ConfigLoader


class ScreenCapturer:
    def __init__(self):
        self.config = ConfigLoader()
        self.camera = None
        self.last_frame = None
        self.frame_count = 0
        self.start_time = time.time()
        self.initialize_camera()

    def initialize_camera(self):
        region = self.config.get('app.screen_region')
        self.camera = dxcam.create(region=region, output_color="RGB")
        self.camera.start(
            target_fps=self.config.get('app.target_fps', 15),
            video_mode=True
        )

    def get_frame(self):
        raw_frame = self.camera.get_latest_frame()
        if raw_frame is None:
            return self.last_frame
        rgb_frame = raw_frame[:, :, [2, 1, 0]]
        self.last_frame = rgb_frame
        self.update_stats()
        return rgb_frame

    def update_stats(self):
        self.frame_count += 1
        if self.frame_count % 100 == 0:
            elapsed = time.time() - self.start_time
            fps = self.frame_count / elapsed
            print(f"[ScreenCapturer] FPS: {fps:.2f}")


if __name__ == "__main__":
    # Тест модуля захвата
    capturer = ScreenCapturer()
    for _ in range(10):
        frame = capturer.get_frame()
        if frame is not None:
            print(f"Frame shape: {frame.shape}")
        time.sleep(0.1)