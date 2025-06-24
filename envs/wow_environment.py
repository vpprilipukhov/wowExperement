import logging
import time
import win32gui
import win32con
import ctypes
import cv2
import numpy as np
from typing import Optional, Dict, Any
from mss import mss


class Config:
    WOW_WINDOW_TITLE = "World of Warcraft"
    YANDEX_GPT_API_KEY = "your_api_key_here"  # Замените на реальный ключ
    CAPTURE_FPS = 15
    MAX_CACHE_SIZE = 30

logger = logging.getLogger(__name__)

class WoWEnvironment:
    def __init__(self):
        self.window_handle = None
        self.sct = None
        self.capture_region = None
        self.last_frame_time = 0
        
    def initialize(self) -> bool:
        try:
            self._set_dpi_awareness()
            self._find_window()
            self._setup_capture_region()
            self._init_capture()
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации: {str(e)}")
            self.cleanup()
            return False

    def _set_dpi_awareness(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()

    def _find_window(self):
        def callback(hwnd, _):
            if (win32gui.IsWindowVisible(hwnd) and 
                Config.WOW_WINDOW_TITLE.lower() in win32gui.GetWindowText(hwnd).lower()):
                rect = win32gui.GetWindowRect(hwnd)
                if rect[2] - rect[0] > 100 and rect[3] - rect[1] > 100:
                    self.window_handle = hwnd
        
        win32gui.EnumWindows(callback, None)
        if not self.window_handle:
            raise ValueError(f"Окно '{Config.WOW_WINDOW_TITLE}' не найдено")

    def _setup_capture_region(self):
        left, top, right, bottom = win32gui.GetWindowRect(self.window_handle)
        if win32gui.IsIconic(self.window_handle):
            win32gui.ShowWindow(self.window_handle, win32con.SW_RESTORE)
            time.sleep(0.5)
            left, top, right, bottom = win32gui.GetWindowRect(self.window_handle)
        
        self.capture_region = {
            'left': left,
            'top': top,
            'width': right - left,
            'height': bottom - top
        }

    def _init_capture(self):
        self.sct = mss()
        logger.info(f"Инициализирован захват для региона: {self.capture_region}")

    def get_game_state(self) -> Dict[str, Any]:
        frame = self.capture_frame()
        return {
            'resolution': f"{self.capture_region['width']}x{self.capture_region['height']}",
            'frame': frame,
            'timestamp': time.time()
        }

    def capture_frame(self) -> Optional[np.ndarray]:
        if time.time() - self.last_frame_time < 1 / Config.CAPTURE_FPS:
            return None
            
        try:
            frame = np.array(self.sct.grab(self.capture_region))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
            self.last_frame_time = time.time()
            return frame
        except Exception as e:
            logger.error(f"Ошибка захвата: {str(e)}")
            return None

    def cleanup(self):
        if hasattr(self, 'sct') and self.sct:
            self.sct.close()